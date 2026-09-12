from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, TypeVar, Literal, Self
import ee
import FeatureManipulation.FeatureCollectionUtils as FeatureCollectionUtils
from EeImageCollections.ImageCollection import ImageCollection
from ReducedCollections.ImmutableReducedBatchCollection import ImmutableReducedBatchCollection
from ReducedCollections.ImmutableReducedOrbitCollection import ImmutableReducedOrbitCollection


if TYPE_CHECKING:
        from EeImageCollections.MultiOrbitCollection import MultiOrbitCollection

TSingleOrbit = TypeVar("TSingleOrbit", bound="SingleOrbitCollection")
"""
Any subclasses of SingleOrbitCollection
"""
TMultiOrbit = TypeVar("TMultiOrbit", bound="MultiOrbitCollection")
"""
Any subclasses of MultiOrbitCollection
"""

class SingleOrbitCollection(ImageCollection, ABC):
    """
    Abstract class
    """

    _reducer_groups : dict[str, tuple[set[str], ee.Reducer]]
    """
    Guides which reducers should be applied to different variables.
    Is a dictionary of
        (1) the reducer name
        (2) a list of
            (1) the set of band_names that should be reduced using this reducer
            (2) the reducer instance that should be used.
    """

    _batch_size : int = 500
    """
    The batch size into which features will be split for processing. Default batch size is 500.
    """

    _mother_collection_id : str
    """
    The collection id of the mother (multi-orbit) image collection.
    """


    def __init__(self,
                start_date: str,
                end_date: str,
                relative_orbit_dict: dict[int, Literal["ASCENDING", "DESCENDING"]],
                collection: ee.ImageCollection,
                collection_name: str,
                footprint_size: int,
                mother_collection_id: str
                ):
        """ PRIVATE CONSTRUCTOR """
    
        super().__init__(
            start_date,
            end_date,
            relative_orbit_dict,   # only this orbit
            collection,
            collection_name,
            footprint_size,
        )
        self._mother_collection_id = mother_collection_id
        self._reducer_groups = {
            "mean_count_stdev": (
                set(), 
                ee.Reducer.mean()
                .combine(ee.Reducer.stdDev(), sharedInputs=True)
                .combine(ee.Reducer.count(), sharedInputs=True)),
            "mean_stdev": (
                set(), 
                ee.Reducer.mean()
                .combine(ee.Reducer.stdDev(), sharedInputs=True) ),
            "mean": (
                set(),
                ee.Reducer.mean() ),
        }

    @classmethod
    @abstractmethod
    def of(cls, multi_orbit_collection: "MultiOrbitCollection[Self]", relative_orbit: int) -> Self:
        """
        Creates a single orbit collection instance of all images of the given multiorbit collection
        instance that are all from the given relative orbit.
        """
        pass

    def get_relative_orbit(self) -> int:
        """
        Returns the relative orbits all of the image in this collection are part of. 
        """
        return list(self.get_relative_orbits())[0]
    
    def get_pass_type(self) -> Literal["ASCENDING", "DESCENDING"]:
        """
        Returns the pass type by which all of these images were taken.
        """
        return self.get_relative_orbit_info()[self.get_relative_orbit()]

    def get_size(self) -> int:
        """
        Returns the number of images in this image collection.
        """
        size_info = self._collection.size().getInfo()
        if size_info is None:
            raise ValueError("The returned size is None.")
        return int(size_info)
    
    def get_bands_per_reducer(self) -> dict[str, set[str]]:
        """
        For each reducer (represented as its reducer name as key) it returns the bands
        allocated to it.
        """
        result = {}
        for name, values in self._reducer_groups.items():
            result[name] = values[0]
        return result    
    
    def get_reducers(self) -> dict[str, ee.Reducer]:
        """
        Returns all reducer instances currently associated with this collection as a dictionary of
            (1) the name (str) of the reducers as keys
            (2) the reducer instances as values

        NOTE: the pressence of a reducer does not indicate that bands are effectively attributed to it.
        """
        result = {}
        for name, values in self._reducer_groups.items():
            result[name] = values[1]
        return result
    
    def get_batch_size(self) -> int:
        """
        Returns the batch size currently associated with this collection.
        """
        return self._batch_size

    def get_mother_collection_id(self) -> str:
        return self._mother_collection_id
    
    def set_batch_size(self, batch_size: int) -> None:
        if not isinstance(batch_size, int):
            raise ValueError(f"'batch_size' should be of type int but is '{type(batch_size)}'")
        if batch_size <= 0:
            raise ValueError(f"'batch_size' should be strickly positive but is {batch_size}.")
        self._batch_size = batch_size
    
    #@abstractmethod
    #def remove_band(self, band_name: str) -> None:
    #    """
    #    Removes the given band from the image collection if present.
    #    Does nothing if the band is not present.
    #    """
    #    pass

    #def reproject_to_common_crs(self) -> None:
    #    """
    #    reprojects all images in the collection to the crs of the
    #    first image.
    #    """
    #    if self._reprojected:
    #        return

    #    first_image = self._collection.first()
    #    target_proj = first_image.projection()

    #    self._collection = self._collection.map(
    #        lambda image: image.reproject(target_proj)
    #    )

    #    self._reprojected = True

    def add_reducer(self, reducer_name: str, reducer: ee.Reducer) -> None:
        """
        Adds a new type of reducer to the MutableCollection.
        Note: default reducers already present are: 'mean_count_stdev', 'mean_stdev' and 'mean'
        No bands are allocated to the newly created reducer yet.
        """
        if not isinstance(reducer, ee.Reducer):
            raise TypeError(f"reducer must be of type ee.Reducer but is {type(reducer)}")
        
        self._reducer_groups[reducer_name] = (set(), reducer)

    def _get_bands_allocated_to_some_reducer(self) -> set[str]:
        """ returns all bands that are already allocated to a reducer. """
        result = set()
        for values in self._reducer_groups.values():
            result.update(values[0])
        return result

    def _get_bands_allocated_to_reducer(self, reducer_name: str) -> set[str]:
        """ returns all band names allocated to the given reducer_name. """
        if not reducer_name in self._reducer_groups.keys():
            raise ValueError(f"The given 'reducer_name': '{reducer_name}' is not one of the available reducers {set(self._reducer_groups.keys())}")
        return self._reducer_groups[reducer_name][0].copy()

    def _allocate_band_to_reducer(self, reducer_name: str, band_name: str) -> None:
        self._reducer_groups[reducer_name][0].add(band_name)

    def allocate_band_to_reducer(self, reducer_name: str, band_name: str) -> None:
        if band_name in self._get_bands_allocated_to_some_reducer():
            raise ValueError(f"band {band_name} is already allocated to a reducer.")
        if not band_name in self.get_bands():
            raise ValueError(f"band {band_name} is not present in the bands of this collection ({self.get_bands()}).")
        if not reducer_name in self._reducer_groups.keys():
            raise ValueError(f"'reducer_name' must be one of {self._reducer_groups.keys()} but is {reducer_name}.")
        self._allocate_band_to_reducer(reducer_name, band_name)

    def allocate_bands_to_reducer(self, reducer_name: str, bands: set[str]) -> None:
        """
        Allocated the given bands to the given reducer_name. Keeps previously
        allocated bands if present.
        """
        for band_name in bands:
            if band_name in self._get_bands_allocated_to_some_reducer():
                raise ValueError(f"band {band_name} is already allocated to a reducer.")
            if not band_name in self.get_bands():
                raise ValueError(f"band {band_name} is not present in the bands of this collection ({self.get_bands()}).")
            if not reducer_name in self._reducer_groups.keys():
                raise ValueError(f"'reducer_name' must be one of {self._reducer_groups.keys()} but is {reducer_name}.")
        for band_name in bands:
            self._allocate_band_to_reducer(reducer_name, band_name)

    #def remove_reducer_band(self, reducer_name: str, band_name: str) -> None:
    #    if not reducer_name in self._reducer_groups.keys():
    #        raise ValueError(f"'reducer_name' must be one of {self._reducer_groups.keys()} but is {reducer_name}.")
    #    self._reducer_groups[reducer_name][0].discard(band_name)

    def get_variables_after_reduction(self) -> set[str]:
        """
        Returns the names of the variables that will be obtained after reducing this
        instance using this.reduce(). Variables have the form of {band_name}_{reducer_name}
        e.g. angle_mean.
        """
        result = []
        for bands, reducer in self._reducer_groups.values():
            for band_name in bands:
                info = reducer.getOutputs().getInfo()
                if info is None:
                    continue
                for reducer_name in list(info):
                    result.append(f"{band_name}_{reducer_name}")
        return set(result)

    def get_variables_per_reducer(self) -> dict[str, set[str]]:
        """
        Returns a dictionary with
            (1) the names of the reducers as keys.
            (2) the associated band_names as values.
        """
        result = {}
        for reducer_name, values in self._reducer_groups.items():
            result[reducer_name] = values[0].copy()
        return result

    @abstractmethod
    def get_name(self) ->str:
        """
        Returns the name of this SingleOrbitCollection.
        This name will be used for downstream file-naming.
        """
        pass
    
    def _create_batch_name(self, batch_id: str) -> str:
        return self.get_name() + '_' + batch_id

    def _reduce_batch(self, field_assets: ee.FeatureCollection, properties: set[str], batch_id: str, object_id_name: str) -> ImmutableReducedBatchCollection:
        """
        Reduces the image collection for one batch of field assets to a ReducedBatchCollection.
        """

        # Use the caller-provided object id property if given, otherwise fall back to
        # deriving one from 'system:index' under an internal '_uid' property.

        reduced_collections : list[ee.FeatureCollection] = []

        for bands, reducer in self._reducer_groups.values():
            if not bands:
                continue
            filtered_collection : ee.ImageCollection = self._collection.select(ee.List(list(bands)))
            stacked_collection : ee.Image = filtered_collection.toBands()
            reduced_collections.append(
                stacked_collection.reduceRegions(
                    collection=field_assets,
                    reducer=reducer,
                    crs=self._get_crs(),
                    scale=self._get_scale(),
                    tileScale=8,
                )
            )

        resulting_variables = self.get_variables_after_reduction()

        merged = self._merge_feature_collections(reduced_collections, join_field=object_id_name)

        #TODO finnish property logic
        return ImmutableReducedBatchCollection.of(merged,
                                                  resulting_variables,
                                                  self._create_batch_name(batch_id),
                                                  self.get_relative_orbit(),
                                                  object_id_name, properties,
                                                  self.get_mother_collection_id())

    def reduce(self, field_assets: ee.FeatureCollection, object_id_name : str) -> ImmutableReducedOrbitCollection:
        """
        Reduces this orbit  relative to the set reducers over the given field_assets, and downloads it to a 
        ReducedOrbitCollection instance.
        object_id_name specifies the name of the object_id collumn. If None it creates an index itself called OID.
        Batching happens internally and can be influenced by using the 'set_batch_size' method.
        
        """
        if not isinstance(field_assets, ee.FeatureCollection):
            raise TypeError(f"'field_assets' must be of type ee.FeatureCollection but are of type {type(field_assets)}.")

        asset_size_info = field_assets.bounds().area(100).getInfo()
        if asset_size_info is None:
            raise ValueError("The return value of field_assets.bound().area().getInfo() cannot be None.")
        if int(asset_size_info) > self._footprint_size:
            raise Warning(f"The bounding box of the field asset is very large ({int(asset_size_info)} m²)." \
                          "This can result in an eventual datasets that are inflated by NaN values (as different fields are observed by totally different relative orbits.) ")

        properties = FeatureCollectionUtils.get_feature_properties(field_assets)
        if not object_id_name in set(properties):
            raise ValueError("The given object_id_name is not present in the field_assets.")
        properties.remove(object_id_name)

        batches = FeatureCollectionUtils.split_features_into_batches(field_assets, self._batch_size)
        batch_collections : set[ImmutableReducedBatchCollection] = set()

        for batch_id, assets in batches.items():
            reduced_batch = self._reduce_batch(assets, properties, batch_id, object_id_name)
            batch_collections.add(reduced_batch)


        return ImmutableReducedOrbitCollection(batch_collections,
                                      self.get_relative_orbit(),
                                      self.get_variables_after_reduction(),
                                      self.get_name(),
                                      object_id_name,
                                      properties,
                                      self.get_mother_collection_id())


    @staticmethod
    def _merge_feature_collections(
        collections: list[ee.FeatureCollection],
        join_field: str,
    ) -> ee.FeatureCollection:

        merged = collections[0]
        join = ee.Join.inner()
        condition = ee.Filter.equals(
            leftField=join_field,
            rightField=join_field,
        )

        for fc in collections[1:]:
            merged = ee.FeatureCollection(
                join.apply(merged, fc, condition).map(
                    lambda pair: ee.Feature(pair.get("primary")).copyProperties(
                        ee.Feature(pair.get("secondary"))
                    )
                )
            )

        return merged

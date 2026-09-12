from __future__ import annotations
from typing import TYPE_CHECKING, Self
from EeImageCollections.MultiOrbitCollection import MultiOrbitCollection
import ee
from . import S1GRD_ImageUtils as ImageUtils
import pandas as pd
import FeatureManipulation.FeatureCollectionUtils as FeatureCollectionUtils
from typing import Literal
from utils.Batch import BatchID
from EeImageCollections.SingleOrbitCollection import SingleOrbitCollection


if TYPE_CHECKING:
        from .S1GRD_MultiOrbitCollection import S1GRD_MultiOrbitCollection

class S1GRD_SingleOrbitCollection(SingleOrbitCollection):
    """
    A mutable collection containing S1 GRD images all of the same relative orbit.
    """

    _reprojected : bool = False
    """
    Expresses whether all images in this collection are already reprojected to a common crs or not.
    """

    _reducer_groups : dict[str, tuple[set[str], ee.Reducer]] = {
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

    _units : Literal["db", "linear"]
    """
    The  units in which the 'VV' and 'VH' bands are expressed.
    """

    def __init__(self,
                start_date: str,
                end_date: str,
                relative_orbit_dict: dict[int, Literal["ASCENDING", "DESCENDING"]],
                collection: ee.ImageCollection,
                collection_name: Literal["COPERNICUS/S1_GRD", "COPERNICUS/S1_GRD_FLOAT"],
                footprint_size: int,
                mother_collection_id: str
                ):
        """ PRIVATE CONSTRUCTOR """
        super().__init__(
            start_date,
            end_date,
            relative_orbit_dict,
            collection,
            collection_name,
            footprint_size,
            mother_collection_id
        )

        self._units = 'db' if collection_name == "COPERNICUS/S1_GRD" else 'linear'

    @classmethod
    def of(cls, multi_orbit_collection: "MultiOrbitCollection[Self]", relative_orbit: int) -> Self:
        filtered = (
            multi_orbit_collection._collection
            .filter(ee.Filter.eq("relativeOrbitNumber_start", relative_orbit))
        )
        name = multi_orbit_collection.get_collection_name()
        assert name in ("COPERNICUS/S1_GRD", "COPERNICUS/S1_GRD_FLOAT")

        return cls(
            multi_orbit_collection.get_time_period()[0],
            multi_orbit_collection.get_time_period()[1],
            {relative_orbit: multi_orbit_collection.get_relative_orbit_info()[relative_orbit]},   # only this orbit
            filtered,
            name,
            multi_orbit_collection.get_footprint_size(),
            multi_orbit_collection.get_collection_id()
        )
    
    def get_units(self) -> Literal["db", "linear"]:
        """
        Returns the units in which the 'VV' and 'VH' band are expressed.
        """
        return self._units

    def add_db_cross_polarization(self) -> None:
        """
        Adds the cross polarization in dB units. The resulting band will be called 'CP'.
        Note: you cannot add both linear and dB cross polarisation bands.
        """
        if 'CP' in self.get_bands():
            return
        if self._units == 'db':
            self._collection = self._collection.map(ImageUtils.add_db_cross_polarization_from_db)
        else:
            self._collection = self._collection.map(ImageUtils.add_db_cross_polarization_from_linear)

    def add_linear_cross_polarization(self) -> None:
        """
        Adds the cross polarization in linear units. The resulting band will be called 'CP'.
        Note: you cannot add both linear and dB cross polarisation bands.
        """
        if 'CP' in self.get_bands():
            return
        if self._units == 'db':
            self._collection = self._collection.map(ImageUtils.add_linear_cross_polarization_from_db)
        else:
            self._collection = self._collection.map(ImageUtils.add_linear_cross_polarization_from_linear)

    def filter_border_noise(self) -> None:
        """
        Masks Sentinel‑1 border noise.
        All pixels with 'VV' value <= -30 [dB] or 0.001 [-] are masked.
        All pixels with angle values >= 47° or <= 28° are masked.
        """
        if self._units == 'linear':
            self._collection = self._collection.map(lambda image: ImageUtils.filter_border_noise_linear(image))
        else:
            self._collection = self._collection.map(lambda image: ImageUtils.filter_border_noise_db(image))

    def add_azimuth_and_local_incidence_angle(self) -> None:
        """
        Adds two bands:
            (1) the 'AZI' or azimuth angle band containing the azimuth angle (in ° off North)
            (2) the 'LIA' or projected local incidence angle band, containting the local incidence
                angle relative to the azimuth angle and ground terrain.
        """
        pass_type = self.get_pass_type()
        self._collection = self._collection.map(lambda image: ImageUtils.add_lia_and_azimuth(image, pass_type))

    #def remove_band(self, band_name: str) -> None:
    #    if band_name == "VV" or band_name == "VH":
    #        raise ValueError("Cannot remove base bands VV and VH.")
    #    self._collection.map(lambda image: ImageUtils.remove_band(image))
    #    for reducer_name, values in self._reducer_groups.items():
    #        if band_name in values[0]:
    #            self.remove_reducer_band(reducer_name, band_name)


    def get_name(self) -> str:
        """
        Returns the name of this single orbit collection. This name is unique for each collection of
        a certain satellite mission, relative orbit, pass type and year.
        """
        return f"S1_RO_{self.get_relative_orbit()}_Pass_{self.get_pass_type()[:3]}_Year_{self.get_start_year()}"

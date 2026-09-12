from ee import batch
from matplotlib.pylab import isinteractive

from .ImmutableReducedBatchCollection import ImmutableReducedBatchCollection
from .ImmutableReducedCollection import ImmutableReducedCollection
from utils.Batch import BatchID
import pandas as pd
import numpy as np
import xarray as xr

class ImmutableReducedOrbitCollection(ImmutableReducedCollection):
    """
    Represents a reduced orbit collection with data stored locally.
    """

    _batch_collections : set[ImmutableReducedBatchCollection]
    """
    A set of batch collection of 
        (1) that all have the same orbit as this collection,
        (2) that all have the same variables as this collection,
        (3) that all have the same object id name.
    This set should be complete, i.e. contain all batches from this orbit.
    """

    def __init__(self, batch_collections: set[ImmutableReducedBatchCollection], relative_orbit: int, variables: set[str], name: str, object_id_name: str, asset_properties: set[str], mother_collection_id: str):
        """
        PRIVATE COONSTRUCTOR
        """
        super().__init__(variables, name, relative_orbit, object_id_name, asset_properties, mother_collection_id)
        self._batch_collections = batch_collections.copy()

    @staticmethod
    def of(batch_collections: set[ImmutableReducedBatchCollection]) -> "ImmutableReducedOrbitCollection":
        """
        Creates a 'ReducedOrbitCollection' instance from a set of ReducedBatchCollections
        Raises values errors
        """
        if not isinstance(batch_collections, set):
            raise TypeError("batch_collections should be of type set.")
        if not all(isinstance(element, ImmutableReducedBatchCollection) for element in batch_collections):
            raise TypeError("all elements of batch_collections should be of type ImmutableReducedBatchCollection.")
        if not batch_collections:
            raise ValueError("Cannot create an ImmutableReducedOrbitCollection from an empty set of batch collections.")


        remaining = iter(batch_collections)
        first = next(remaining)

        variables = first.get_variables()
        asset_properties = first.get_asset_properties()
        relative_orbit = first.get_relative_orbit()
        name = first.get_orbit_collection_name()
        object_id_name = first.get_object_id_name()
        mother_collection_id = first.get_mother_collection_id()
        batch_ids = {first.get_batch_id()}

        for batch_collection in remaining:
            batch_ids.add(batch_collection.get_batch_id())

            if variables != batch_collection.get_variables():
                raise ValueError
            if asset_properties != batch_collection.get_asset_properties():
                raise ValueError
            if relative_orbit != batch_collection.get_relative_orbit():
                raise ValueError
            if name != batch_collection.get_orbit_collection_name():
                raise ValueError
            if object_id_name != batch_collection.get_object_id_name():
                raise ValueError
            if mother_collection_id != batch_collection.get_mother_collection_id():
                raise ValueError("The mother collection identifiers are not the same for all batch collections.")

        BatchID.validate_set(batch_ids)

        return ImmutableReducedOrbitCollection(
            batch_collections.copy(), relative_orbit, variables, name, object_id_name, asset_properties, mother_collection_id
        )
    @staticmethod
    def _get_prefix_and_suffix(collection: ImmutableReducedBatchCollection) -> tuple[str, str]:
        """Splits a name into (prefix, suffix) at the last underscore, e.g. ('foo_bar', '01of20')."""
        prefix, _, suffix = collection.get_name().rpartition('_')
        return prefix, suffix


    @staticmethod
    def _has_valid_name(batch_collection: ImmutableReducedBatchCollection, orbit_collection_name: str) -> bool:
        prefix, _ = ImmutableReducedOrbitCollection._get_prefix_and_suffix(batch_collection)
        return prefix == orbit_collection_name

    @staticmethod
    def _validate_names(batch_collections: set[ImmutableReducedBatchCollection], orbit_collection_name: str) -> None:
        """
        Validates that batch_collections all share the given orbit_collection_name
        prefix, and together form a complete batch, e.g. '01of20', ..., '20of20'.
        TODO: move batch id logic into a seperate class.
        """
        if not isinstance(batch_collections, set):
            raise TypeError(f"batch_collections should be of type set but is of type {type(batch_collections)}")
        if not all(isinstance(element, ImmutableReducedBatchCollection) for element in batch_collections):
            raise TypeError("All elements of batch_collections should be of type ImmutableReducedBatchCollection")
        if not batch_collections:
            raise ValueError("batch_collection cannot be empty.")

        batch_ids: set[str] = set()
        for collection in batch_collections:
            prefix, batch_id = ImmutableReducedOrbitCollection._get_prefix_and_suffix(collection)
            if prefix != orbit_collection_name:
                raise ValueError(f"batch collection '{collection}' has a different name that than expected ({orbit_collection_name}_" + f"{batch_id}).")
            batch_ids.add(batch_id)

        try:
            BatchID.validate_set(batch_ids)
        except ValueError:
            raise  # re-raises the original exception, unchanged

    def get_reduced_batch_collections(self) -> set[ImmutableReducedBatchCollection]:
        return self._batch_collections.copy()

    def create_long_variable_dfs(self) -> dict[str, pd.DataFrame]:
        """
        Returns a dictionary with the varibale names as keys and the
        variable dataframes as values (long type). Each dataframe has
        the following columns:
            (1) OID
            (2) timestamp
            (3) {variable}
        """

        df_lists : dict[str, list] = {}
        for variable in self._variables:
            df_lists[variable] = []

        for reduced_batch in self._batch_collections:
            variable_dfs = reduced_batch.create_long_variable_dfs()
            for variable, df in variable_dfs.items():
                df_lists[variable].append(df)

        result = {}
        for variable in self._variables:
            result[variable] = pd.concat(df_lists[variable])
        return result
    
    def create_wide_variable_dfs(self) -> dict[str, pd.DataFrame]:
        """
        Returns a dictionarye with variable names as keys and the
        variable dataframes as values (wide type). Each dataframe
        has the following columns:
            (1) OID
            (2) one column per timestamp
        The values are the values of the given variable.
        """
        result = {}
        long_df_dict = self.create_long_variable_dfs()
        for variable in self._variables:
            result[variable] = long_df_dict[variable].pivot(index = self._object_id_name,
                                                            columns = 'timestamp',
                                                            values = variable)
        return result
    
    def create_properties_df(self, centroid_property_name: str | None) -> pd.DataFrame:
        """
        Creates a dataframe containing all properties of this ReducedOrbitCollection instance.
        """
        frames = [
            reduced_batch.create_properties_df(centroid_property_name)
            for reduced_batch in self._batch_collections
        ]
        if not frames:
            return pd.DataFrame(columns=[self._object_id_name, *self._asset_properties])

        return pd.concat(frames, ignore_index=True)


    def create_dataset(self, controid_property_name: str | None = 'polygon_centroid') -> xr.Dataset:
        """
        Builds an xarray Dataset from the long-format variable dataframes.

        Dimensions/coordinates:
            - OID
            - timestamp

        Data variables:
            - one per entry in get_variables(), each with dims (OID, timestamp)
            - 'RO': relative orbit, with dim (timestamp,) only
            - one entry per property in get_properties(), all 1-D (OID)
        NOTE: The polygon centroid property is split into an x and y variable (that vary with OID)
        """
        variable_dfs = self.create_wide_variable_dfs()

        # for one orbit all oid's and timestamps should be identical for each variable
        first_df : pd.DataFrame = variable_dfs[next(iter(variable_dfs))]
        all_timestamps: list[pd.Timestamp] = sorted(pd.to_datetime(first_df.columns))
        all_oids: list[int | str] = sorted(first_df.index)


        # Align every variable onto the same (OID, timestamp) grid so
        # missing combinations become NaN instead of raising/misaligning.
        data_vars: dict[str, tuple] = {}
        for variable, df in variable_dfs.items():
            if df.empty:
                arr = np.full((len(all_oids), len(all_timestamps)), np.nan)
            else:
                df = df.reindex(index=all_oids, columns=all_timestamps)
                arr = df.to_numpy()
            data_vars[variable] = (("OID", "timestamp"), arr)

        # RO only depends on timestamp, not OID.
        ro_values = np.full(len(all_timestamps), self.get_relative_orbit(), dtype=int)
        data_vars["RO"] = (("timestamp",), np.asarray(ro_values, dtype=int))
    
        # Properties are 1-D per OID; align them onto the same OID grid.
        properties_df = self.create_properties_df(controid_property_name)
        if properties_df.duplicated(subset=self._object_id_name).any():
            raise ValueError(
                f"Duplicate {self._object_id_name!r} values in properties_df; "
                "cannot align to OID dimension unambiguously."
            )
        properties_df = properties_df.set_index(self._object_id_name).reindex(all_oids)
        for property_ in properties_df.columns:
            data_vars[property_] = (("OID",), properties_df[property_].to_numpy())

        return xr.Dataset(
            data_vars=data_vars,
            coords={
                "OID": all_oids,
                "timestamp": all_timestamps,
            },
        )

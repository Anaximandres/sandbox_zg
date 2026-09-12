from .ImmutableReducedCollection import ImmutableReducedCollection
from .ImmutableReducedOrbitCollection import ImmutableReducedOrbitCollection
from typing import Generic
import pandas as pd
import xarray as xr

class ImmutableReducedMultiOrbitCollection(ImmutableReducedCollection):
    """
    Not included yet in the current version.
    Is a class that would be created from reducing a MultiOrbitCollection or
    reading in a full csv output directory.
    """
    #TODO check if this class is a true added value or if merging logic should not just be included in the MutableReducedCollection logic

    _orbit_collections : set[ImmutableReducedOrbitCollection]
    """
    The set of OrbitCollections this instance represents.
    """

    def __init__(self, orbit_collections : set[ImmutableReducedOrbitCollection], variables: set[str], name: str, relative_orbit: int, object_id_name: str, asset_properties: set[str], mother_collection_id: str):
        raise RuntimeError('Not yet implemented')

        super().__init__(variables, name, relative_orbit, object_id_name, asset_properties, mother_collection_id)
        self._orbit_collections = orbit_collections

    @staticmethod
    def of(orbit_collections: set[ImmutableReducedOrbitCollection]) -> "ImmutableReducedMultiOrbitCollection":
        raise RuntimeError('Not yet implemented')

        variables : set[str] = set()
        asset_properties : set[str] = set()
        relative_orbit : int | None = None
        name : str | None = None
        object_id_name : str | None = None
        mother_collection_id : str | None = None
        for orbit_collection in orbit_collections:
            if not variables:
                variables = orbit_collection.get_variables()
            elif variables != orbit_collection.get_variables():
                raise ValueError
            if not asset_properties:
                asset_properties = orbit_collection.get_asset_properties()
            elif asset_properties != orbit_collection.get_asset_properties():
                raise ValueError
            if not relative_orbit:
                relative_orbit = orbit_collection.get_relative_orbit()
            elif relative_orbit != orbit_collection.get_relative_orbit():
                raise ValueError
            if not object_id_name:
                object_id_name = orbit_collection.get_object_id_name()
            elif object_id_name != orbit_collection.get_object_id_name():
                raise ValueError
            if not mother_collection_id:
                mother_collection_id = orbit_collection.get_mother_collection_id()
            elif mother_collection_id != orbit_collection.get_mother_collection_id():
                raise ValueError("The mother collection identifiers are not the same for all batch collections.")
    
        return ImmutableReducedMultiOrbitCollection(orbit_collections.copy(), variables, name, relative_orbit, object_id_name, asset_properties, mother_collection_id)
    
    def create_long_variable_dfs(self) -> dict[str, pd.DataFrame]:
        raise RuntimeError('Not yet implemented')

    def create_wide_variable_dfs(self) ->dict[str, pd.DataFrame]:
        raise RuntimeError('Not yet implemented')

    def create_properties_df(self) -> pd.DataFrame:
        raise RuntimeError('Not yet implemented')

    def create_dataset(self) -> xr.Dataset:
        raise RuntimeError('Not yet implemented')

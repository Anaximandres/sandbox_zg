import xarray as xr
from abc import ABC
from ImmutableReducedOrbitCollection import ImmutableReducedOrbitCollection

class MutableReducedCollection(ABC):
    """
    Abstract class
    """

    _collection : xr.Dataset
    """
    An xarray Dataset with
    Dimensions/coordinates:
        - OID
        - timestamp

    Data variables:
        - one per entry in get_variables(), each with dims (OID, timestamp)
        - 'RO': relative orbit, with dim (timestamp,) only
        - one entry per property in get_properties(), all 1-D (OID)
    """

    def __init__(self, collection: xr.Dataset):
        """ PRIVATE CONSTRUCTOR """
        self._collection = collection

    def of(orbit_collections: set[ImmutableReducedOrbitCollection]) -> "MutableReducedCollection":
        #TODO check how to incorporate the right subclass logic into this.
        variables : set[str] = set()
        asset_properties : set[str] = set()
        relative_orbit : int | None = None
        name : str | None = None
        object_id_name : str | None = None
        mother_collection_id : str | None = None
        datasets : set[xr.Dataset] = set()
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
            datasets.add(orbit_collection.create_dataset())
    
        try:
            combined = xr.merge(
                datasets,
                join="outer",       # union of OID and timestamp coords
                compat="no_conflicts",  # allow NaN-vs-value, error on value-vs-different-value
                fill_value=np.nan,
            )
        except xr.MergeError as exc:
            raise ValueError(
                "Failed to merge orbit datasets — likely a property that "
                "differs for the same OID across orbits (should be constant "
                "per object)."
            ) from exc

        # Optional: deterministic ordering of coords
        combined = combined.sortby(["timestamp", object_id_name])

        return MutableReducedCollection(combined)
    
    def get_collection(self) -> xr.Dataset:
        """ Returns a deep copy of the dataset represented by this instance"""
        return self._collection.copy(deep=True)


from MutableReducedCollection import MutableReducedCollection
from ImmutableReducedOrbitCollection import ImmutableReducedOrbitCollection
from GriddedReducedCollection import GriddedReducedCollection
import xarray as xr

class S1GRD_MutableReducedCollection(MutableReducedCollection):

    def __init__(self, collection: xr.Dataset):
        """ PRIVATE CONSTRUCTOR """
        super().__init__(collection)

    def of(reduced_collections: set[ImmutableReducedOrbitCollection]) -> "S1GRD_MutableReducedCollection":
        pass

    def perform_orbit_correction(self) -> None:
        pass

    def map_to_grid(self) -> GriddedReducedCollection:
        pass
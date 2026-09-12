import xarray as xr
from MutableReducedCollection import MutableReducedCollection

class GriddedReducedCollection():

    _collection : xr.Dataset

    def __init__(self, collection: xr.Dataset):
        self._collection = collection

    @staticmethod
    def of(reduced_collection: MutableReducedCollection) -> "GriddedReducedCollection":
        pass

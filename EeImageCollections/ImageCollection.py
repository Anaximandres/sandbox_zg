from abc import ABC, abstractmethod
import ee
from typing import Literal
from datetime import datetime
import hashlib

class ImageCollection(ABC):

    _collection : ee.ImageCollection
    """
    The server side gee image collection represented by this class instance.
    """
    _start_date : str
    """
    Start date as a string of type 'YYYY-MM-DD'
    """
    _end_date : str
    """
    End date as a string of type 'YYYY-MM-DD'
    """
    _relative_orbit_info : dict[int, Literal["ASCENDING", "DESCENDING"]]
    """
    Dictionary with relative orbit numbers (as int) as keys and the pass type ('ASCENDING' or 'DESCENDING')
    as values.
    """
    _collection_name : str
    """
    The name of GEE collection this ImageCollection is based of.
    """

    _collection_id : str
    """
    A unique identifier for this collection.
    """

    _footprint_size : int
    """
    An approximation of the footprint size in m²
    """

    def __init__(self, start_date: str, end_date: str, relative_orbit_info: dict[int,Literal["ASCENDING", "DESCENDING"]], collection: ee.ImageCollection, collection_name: str, footprint_size: int):
        """ PRIVATE abstract class constructor. See S1Mutable and S1Immutable classes for an implementation"""
        self._collection = collection
        self._start_date = start_date
        self._end_date = end_date
        self._relative_orbit_info = relative_orbit_info
        self._collection_name = collection_name
        self._footprint_size = footprint_size
        self._collection_id = self._generate_collection_id(collection)

    def get_bands(self) -> set[str]:
        """
        Returns a set of the band names each image in this collection has.
        """
        band_names = self._collection.first().bandNames().getInfo()
        assert band_names is not None
        return set(band_names)
    
    def get_relative_orbits(self) -> set[int]:
        """
        Returns a set containing all relative orbit numbers of which
        images are present in this collection.
        """
        return set(self._relative_orbit_info.keys())
    
    def get_time_period(self) -> tuple[str, str]:
        """
        Returns the time period as a tuple of str objects.
        The strings have the following pattern: 'YYYY-MM-DD'.
        """
        return (self._start_date, self._end_date)
    
    def get_start_year(self) -> int:
        """
        Returns the year the first image in this image collection was taken.
        """
        return int(self._start_date[:4])
    
    def get_relative_orbit_info(self) -> dict[int, Literal["ASCENDING", "DESCENDING"]]:
        """
        Return a dictionary with
            (1) relative orbit numbers as keys
            (2) their associated pass type as values
        """
        return self._relative_orbit_info.copy()

    def get_collection_name(self) -> str:
        """
        Returns the name of the GEE collection this ImageCollection was based on.
        """
        return self._collection_name
    
    def get_collection_id(self) -> str:
        """
        Returns a unique identifier of this instance.
        """
        return self._collection_id
    
    def _get_scale(self) -> ee.Number:
        """
        Returns the scale of the images in this ImageCollection (as an ee.Number!)
        """
        return self._collection.first().select([0]).projection().nominalScale()

    def _get_crs(self) -> ee.String:
        """
        Returns the crs of the images in this ImageCollection (as an ee.String!)
        """
        return self._collection.first().select([0]).projection().crs()
    
    def get_footprint_size(self) -> int:
        """
        Returns an approximation of the footprint size of the satellite images.
        """
        return self._footprint_size

    def get_collection(self) -> ee.ImageCollection:
        """
        Returns the image collection represented by this instance as an ee.ImageCollection.
        """
        return self._collection

    @staticmethod
    def _generate_collection_id(collection: ee.ImageCollection) -> str:
        """
        Deterministically derive a stable identifier from an ee.ImageCollection's
        full computation graph (filters, sorting, mosaicking, etc).

        Two independently-built ee.ImageCollection objects that represent the
        same underlying computation will always produce the same id; anything
        different in their construction (different filters, dates, etc.) will
        produce a different id.
        """
        serialized = collection.serialize()  # deterministic JSON of the expression graph
        digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
        return digest

    def __str__(self):
        return str(self._collection)

    def __eq__(self, value):
        if not isinstance(value, ImageCollection):
            return False
        return self._collection_id == value.get_collection_id()

    def __hash__(self):
        return hash(self._collection_id)

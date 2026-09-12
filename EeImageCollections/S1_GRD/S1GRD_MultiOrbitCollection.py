from __future__ import annotations
from typing import TYPE_CHECKING, Literal
import ee
from EeImageCollections.MultiOrbitCollection import MultiOrbitCollection

if TYPE_CHECKING:
    from EeImageCollections.S1_GRD.S1GRD_SingleOrbitCollection import S1GRD_SingleOrbitCollection

class S1GRD_MultiOrbitCollection(MultiOrbitCollection):

    _units : Literal["db", "linear"]
    """
    Expressing the units in which bands 'VV' and 'VH' are expressed
    """

    FOOTPRINT_SIZE: int = 45000000
    """
    The approximate footprint size of a S1 GRD image in IW mode.
    """


    def __init__(self,
                 start_date: str,
                 end_date: str,
                 relative_orbit_info: dict[int, Literal["ASCENDING", "DESCENDING"]],
                 collection: ee.ImageCollection,
                 collection_id: str,
                 units: Literal["db", "linear"], 
                 ):
        """ PRIVATE CONSTRUCTOR """

        super().__init__(start_date, end_date, relative_orbit_info, collection, collection_id, self.FOOTPRINT_SIZE)
        self._units = units

    @staticmethod
    def of(roi: ee.Geometry, start_date: str, end_date: str, units: str = "db") -> S1GRD_MultiOrbitCollection:
        """
        Creates an S1GRD_MultiOrbitCollection instance representing images from Sentinel-1 (GRD) over
        the given region of interest ('roi') from 'start_date' to 'end_date'.
        The images are restricted to 'IW' mode images of dual polarisation with 'VV' and 'VH'
        """
        roi = MultiOrbitCollection.validate_roi(roi)
        start_date, end_date = MultiOrbitCollection.validate_dates(start_date, end_date)

        if units == 'db':
            collection_id = 'COPERNICUS/S1_GRD'
        elif units == 'linear':
            collection_id = 'COPERNICUS/S1_GRD_FLOAT'
        else:
            raise ValueError("`units` should be either 'db' or 'linear'.")

        collection = (
            ee.ImageCollection(collection_id)
            .filterBounds(roi)
            .filterDate(start_date, end_date)
            .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VV"))
            .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VH"))
            .filter(ee.Filter.eq("instrumentMode", "IW"))
            .sort("system:time_start")
        )

        return S1GRD_MultiOrbitCollection(start_date,
                                          end_date,
                                          S1GRD_MultiOrbitCollection._retrieve_relative_orbit_info(collection),
                                          collection,
                                          collection_id,
                                          units)

    def get_units(self) -> Literal["db", "linear"]:
        """
        Retruns the units in which the 'VV' and 'VH' band in this collection are represented.
        """
        return self._units
    
    @staticmethod
    def _retrieve_relative_orbit_info(collection: ee.ImageCollection) -> dict[int, Literal["ASCENDING", "DESCENDING"]]:
        """Fetches all relative orbit numbers (keys) and their pass directions (values)."""
        distinct = collection.distinct("relativeOrbitNumber_start")
        numbers = distinct.aggregate_array("relativeOrbitNumber_start").getInfo()
        passes  = distinct.aggregate_array("orbitProperties_pass").getInfo()
        assert numbers is not None
        assert passes is not None
        return dict(zip(numbers, passes))

    def split_into_relative_orbit_collections(self) -> dict[int, S1GRD_SingleOrbitCollection]:
        """
        Returns a dictionary with the relative orbit numbers as keys and the associated
        image collections as values.
        """
        from EeImageCollections.S1_GRD.S1GRD_SingleOrbitCollection import S1GRD_SingleOrbitCollection
        return {
            ro: S1GRD_SingleOrbitCollection.of(self, ro)
            for ro in self.get_relative_orbits()
        }

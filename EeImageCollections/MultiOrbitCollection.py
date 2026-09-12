from __future__ import annotations
from typing import TYPE_CHECKING,Generic, TypeVar, Iterator, Literal

from abc import ABC, abstractmethod
from EeImageCollections.ImageCollection import ImageCollection
import ee
from datetime import datetime

if TYPE_CHECKING:
    from EeImageCollections.SingleOrbitCollection import SingleOrbitCollection

TSingleOrbit = TypeVar("TSingleOrbit", bound="SingleOrbitCollection")


class MultiOrbitCollection(ImageCollection, Generic[TSingleOrbit], ABC):

    def __init__(self, 
                 start_date: str,
                 end_date: str,
                 relative_orbit_info: dict[int, Literal["ASCENDING", "DESCENDING"]],
                 collection: ee.ImageCollection,
                 collection_id: str,
                 footprint_size: int):
        """ PRIVATE CONSTRUCTOR """
        super().__init__(start_date, end_date, relative_orbit_info, collection, collection_id, footprint_size)

    @staticmethod
    @abstractmethod
    def _retrieve_relative_orbit_info(collection: ee.ImageCollection) -> dict[int, str]:
        """Fetches all relative orbit numbers and their pass directions."""
        pass

    @staticmethod
    def validate_date(date: str) -> str:
        """ checks if date has format YYYY-MM-DD, returns the date if true, raises a valueerror if not"""
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except (ValueError, TypeError):
            raise ValueError(f"Invalid date format: {date!r}. Expected YYYY-MM-DD.")

        return date

    @staticmethod
    def validate_dates(start_date: str, end_date: str) -> list[str]:
        for date in [start_date, end_date]:
            MultiOrbitCollection.validate_date(date)
        if start_date > end_date:
            raise ValueError("start_date must be earlier than end_date.")
        return [start_date, end_date]

    @staticmethod
    def validate_roi(roi: ee.Geometry) -> ee.Geometry:
        if not isinstance(roi, ee.Geometry):
            raise TypeError(f"'roi' must be of type 'ee.Geometry' but is of '{type(roi)}'")
        return roi
    
    @abstractmethod
    def split_into_relative_orbit_collections(self) -> dict[int, TSingleOrbit]:
        """
        Split this collection into single-orbit collections.

        Returns
        -------
        dict[int, TSingleOrbit]
            Mapping from relative orbit number to the mission-specific
            SingleOrbitCollection subclass associated with this
            MultiOrbitCollection subclass (e.g. S1GRD_MultiOrbitCollection
            returns S1GRD_SingleOrbitCollection instances).
        """
        pass

    def __iter__(self) -> Iterator[TSingleOrbit]:
        orbits = self.split_into_relative_orbit_collections()
        return iter(orbits[k] for k in sorted(orbits))

    def __len__(self) -> int:
        """Number of relative orbit collections."""
        return len(self.split_into_relative_orbit_collections())

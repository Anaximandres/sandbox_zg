from abc import ABC, abstractmethod

class ImmutableReducedCollection(ABC):
    """
    Represents a reduced sentinel 1 Image Collection.
    Stores the data locally.
    Immutable.
    """

    _variables : set[str]
    """
    The set of variables represented by
    """

    _asset_properties : set[str]
    """
    The set of properties from the assets that should be kept downstream.
    """

    _name : str
    """
    The name of this reduced collection.
    """

    _relative_orbit : int
    """
    The relative orbit which the data of this collection represent.
    """

    _object_id_name  : str
    """
    The name of the column to use as object id.
    """

    _mother_collection_id : str
    """
    The identifier of the mother (multi-orbit) collection.
    """

    def __init__(self, variables: set[str], name: str, relative_orbit: int, object_id_name: str, asset_properties: set[str], mother_collection_id: str):
        """ 
        ABSTRACT SUPERCLASS CONSTRUCTOR 
        """
        self._variables = variables.copy()
        self._name = name
        self._relative_orbit = relative_orbit
        self._object_id_name = object_id_name
        self._asset_properties = asset_properties.copy()
        self._mother_collection_id = mother_collection_id

    def get_variables(self) -> set[str]:
        return self._variables.copy()
    
    def get_name(self) -> str:
        return self._name
    
    def get_relative_orbit(self) -> int:
        return self._relative_orbit
    
    def get_object_id_name(self) -> str:
        """
        returns the name of the field used as the parcel identifier in the assets.
        """
        return self._object_id_name
    
    def get_asset_properties(self) -> set[str]:
        return self._asset_properties.copy()

    def get_mother_collection_id(self) -> str:
        return self._mother_collection_id
    
    def __str__(self) -> str:
        return f"Reduced Collection of '{self.get_name()}'"
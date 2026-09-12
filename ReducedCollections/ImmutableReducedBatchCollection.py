import ee
import pandas as pd
from FeatureManipulation import FeatureCollectionUtils
from .ImmutableReducedCollection import ImmutableReducedCollection

class ImmutableReducedBatchCollection(ImmutableReducedCollection):
    """
    Represents a reduced sentinel 1 Image Collection.
    Stores the data locally.
    Immutable.
    """

    _collection : pd.DataFrame
    """
    A pandas dataframe representing the reduced ImageCollection data. Its rows contains the
    different field asset ids and its columns represent observations of different reduced
    variables. The last columns are the inherited field properties (eg centroid).
    """


    def __init__(self, dataframe:pd.DataFrame , variables: set[str], name: str, relative_orbit: int, object_id_name: str, asset_properties: set[str], mother_collection_id: str):
        """ 
        PRIVATE CONSTRUCTOR 
        """
        super().__init__(variables, name, relative_orbit, object_id_name, asset_properties, mother_collection_id)
        self._collection = dataframe

    
    @staticmethod
    def of(collection: ee.FeatureCollection,
           variables: set[str],
           name: str,
           relative_orbit: int,
           object_id_name: str,
           asset_properties: set[str],
           mother_collection_id: str) -> "ImmutableReducedBatchCollection":
        """
        Creates an S1ReducedCollection instance from a feature collection.
        """
        #TODO
        #check if moving reduction logic here does not make more sense
        dataframe = FeatureCollectionUtils.feature_collection_to_df(collection)
        return ImmutableReducedBatchCollection(dataframe, variables, name, relative_orbit, object_id_name, asset_properties, mother_collection_id)

    def get_size(self) -> int:
        return self._collection.size
    
    def get_orbit_collection_name(self) -> str:
        """
        Returns the name of the orbit collection this batch is a part of.
        """
        return self._name.rsplit('_', 1)[0]
    
    def get_batch_id(self) -> str:
        """
        Returns the batch id
        """
        #TODO change the batch id logic to be more intuitive and embedded in the class.
        return self._name.rsplit('_', 1)[1]

    def get_collection(self) -> pd.DataFrame:
        """
        Returns a copy the reduced data stored in
        """
        return self._collection.copy(deep = True)
    
    @staticmethod
    def disentangle_column_name(name: str) -> dict[str, str | pd.Timestamp]:
        """
        Disentagles the information in the column name of a collection.
        The resulting keys are:
            'mission_identifier'
            'acquisition_mode'
            'product_type'
            'resolution_class'
            'processing_level'
            'product_class'
            'polarisation'
            'start_datetime'
            'end_datetime'
            'absolute_orbit_number'
            'mission_data_take_id'
            'product_unique_identifier'
            'variable'
        """
        splitted = name.split('_')
        return {
            'mission_identifier'    : splitted[0],
            'acquisition_mode'      : splitted[1],
            'product_type'          : splitted[2][:3],
            'resolution_class'      : splitted[2][-1],
            'processing_level'      : splitted[3][0],
            'product_class'         : splitted[3][1],
            'polarisation'          : splitted[3][2:],
            'start_datetime'        : pd.to_datetime(splitted[4], format="%Y%m%dT%H%M%S").round("h"),
            'end_datetime'          : pd.to_datetime(splitted[5], format="%Y%m%dT%H%M%S").round("h"),
            'absolute_orbit_number' : splitted[6],
            'mission_data_take_id'  : splitted[7],
            'product_unique_identifier' : splitted[8],
            'variable'              : splitted[-2] + '_' + splitted[-1]
        }

    def create_long_variable_dfs(self) -> dict[str, pd.DataFrame]:
        """
        Returns a dictionary with the varibale names as keys and the
        varibale dataframes as values (long type). Each dataframe has
        the following columns:
            (1) OID
            (2) timestamp
            (3) {variable}
        """
        object_ids = self._collection[self._object_id_name]

        result = {}
        for variable in self._variables:
            result[variable] = pd.DataFrame()

        for column_name, values in self._collection.items():
            if str(column_name)[:2] != 'S1':
                continue
            disenagled_name = ImmutableReducedBatchCollection.disentangle_column_name(str(column_name))
            variable_df = pd.DataFrame({
                self._object_id_name        : object_ids,
                "timestamp"                 : disenagled_name['start_datetime'],
                disenagled_name['variable'] : values
            })
            result[disenagled_name['variable']] = pd.concat([result[disenagled_name['variable']], variable_df])

        return result
    
    def create_properties_df(self) -> pd.DataFrame:
        """
        Returns a dataframe containing all properties of this ReducedBatchCollection instance.
        """
        #NOTE possible improvement to allow for using only a subset of the asset properties
        columns = [self._object_id_name, *self._asset_properties]
        return self._collection[columns].copy()

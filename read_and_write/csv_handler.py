import os
from ReducedCollections.ImmutableReducedBatchCollection import ImmutableReducedBatchCollection
from ReducedCollections.ImmutableReducedOrbitCollection import ImmutableReducedOrbitCollection
from pathlib import Path
import pandas as pd
import json

class CSVHandler():
    """
    This class handles writing and reading reduced Sentinel-1 images.
    """

    _root_dir : Path
    """ 
    Base folder in which a Header folder and several Orbit folders will be created.
    Please keep this folder empty and do not manually add / remove items in this folder
    to preserve consistency.
    """

    _relative_orbits : set[int]
    """ 
    Relative orbits accounted for. Each relative orbit has a corresponding non-empty 'Header' 
    file in the Headers folder and an own non-empty 'Orbit' folder with one or more csv describing
    observations of the given relative orbit.
    """

    _meta : dict
    """
    dictionary containing metadata. Always the same as the meta/csv_meta_data.json file
    that is stored in the root directory.
    """

    META_FILENAME : str = "csv_meta_data.json"
    """
    File name used for the meta data file.
    """

    def __init__(self, root_dir: Path):
        """
        Initiates a CSVHandler instance that facilitates writing and reading files to and from
        a the csv folder structure for handling reduced sentinel 1 data. If the given 'root_dir'
        already contains files associated with this data, it will check for consistency and
        incorporate these files.
        :param root_dir: the root directory in which the csv folder structure should be housed.
        It creates folders like 'Headers' and 'Orbit_XX' make sure no folders accidentilly named
        this way are present in the root directory.
        """
        root_dir = Path(root_dir)  # ensure it's a Path even if a str was passed
        try:
            root_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            raise ValueError(
                f"The given directory '{root_dir}' does not exist and trying "
                f"to create it yielded the following exception: {e}"
            ) from e

        headers_dir = root_dir / 'Headers'
        self._root_dir = root_dir
        self._relative_orbits = set()
        self._meta = {}
        headers_dir.mkdir(exist_ok=True)
        if any(headers_dir.iterdir()):  # if not empty
            self._read_in_existing_folder_and_files()

        meta_path = root_dir / CSVHandler.META_FILENAME
        if meta_path.exists():
            with open(meta_path, 'r') as json_file:
                meta = json.load(json_file)
            self._meta = self._valdate_meta(meta)

    @staticmethod
    def _get_csv_file_name(reduced_batch : ImmutableReducedBatchCollection) -> str:
        return f"{reduced_batch.get_name()}.csv"

    @staticmethod
    def _get_orbit_folder_name(relative_orbit: int) -> str:
        """
        Returns the orbit folder of a relative orbit.
        NOTE: it does not verify whether the folder exists or not
        """
        return f"Orbit_{relative_orbit}"

    @staticmethod
    def _get_header_file_name(relative_orbit: int) -> str:
        """
        Returns the file a header of the given relative orbit should have.
        NOTE: does not verify whether the file exists.
        """
        return f"Headers_{CSVHandler._get_orbit_folder_name(relative_orbit)}.txt"

    def _get_orbit_folder_path(self, relative_orbit: int) -> Path:
        return self._root_dir / self._get_orbit_folder_name(relative_orbit)

    def _get_json_file_path(self) -> Path:
        """ Returns the path of the meta data json file. """
        return self._root_dir / self.META_FILENAME
    
    @staticmethod
    def _get_relative_orbit_from_header_name(header_name: str) -> int:
        split_header_name = header_name.split('.')[0].split('_')
        if not len(split_header_name) == 2 and split_header_name[0] == 'Header' and split_header_name[-1].isnumeric():
            raise ValueError("Header name must be of format 'Header_Orbit_{relative_orbit}'" + f" but is {header_name}.")
        return int(split_header_name[-1])
    
    @staticmethod
    def _get_relative_orbit_from_file_name(file_name: str) -> int:
        """ Returns the relative orbit number given a correct file name."""
        splitted = file_name.split('_')
        if not (splitted[0] == "S1" and 
                splitted[1] == "RO" and
                splitted[2].isnumeric()):
            raise ValueError("File name is not of the recognized format 'S1_RO_{relative_orbit}_(...).csv'")
        return int(splitted[2])
    
    @staticmethod
    def _get_all_file_names_from_header_file(header_file_path: str) -> set[str]:
        if not os.path.exists(header_file_path):
            return set()
        with open(header_file_path) as header_file:
            rows = header_file.readlines()
        rows = [row.strip().rstrip(',') for row in rows]
        return set(rows)

    def _read_in_existing_folder_and_files(self) -> None:
        headers_dir = os.path.join(self._root_dir, 'Headers')
        for file_name in os.listdir(headers_dir):
            try:
                ro = CSVHandler._get_relative_orbit_from_header_name(file_name)
            except ValueError:
                continue
            orbit_files = CSVHandler._get_all_file_names_from_header_file(os.path.join(headers_dir, file_name))

            orbit_folder_path = os.path.join(self._root_dir, f"Orbit_{ro}")
            if (not os.path.exists(orbit_folder_path)) and orbit_files:
                raise ValueError(f"Relative orbit {ro} is accounted for in the Header files"
                f"by file {file_name} but does not have a corresponding orbit folder called"
                f"'Orbit_{ro} in the root directory ({self._root_dir}).")

            for orbit_file_name in orbit_files:
                path = os.path.join(orbit_folder_path, orbit_file_name)
                if not os.path.exists(path):
                    raise ValueError(f"File {orbit_file_name} is accounted for in the Headers file but "    \
                                     f"the file itself is not present in its corresponding orbit folder 'Orbit_{ro}'.")
            self._relative_orbits.add(ro)


    def create_output_path_name(self, folder_name: str, file_name: str) -> str:
        """ 
        Creates a path as 'self.get_root_dir()/folder_name/file_name'.
        Creates the folder if it does not exist yet.
        """
        folder_path = os.path.join(self._root_dir, folder_name)
        print(type(folder_path))
        os.makedirs(folder_path, exist_ok = True)
        print(type(file_name))
        return os.path.join(folder_path, file_name)

    def _write_header(self, file_name: str, relative_orbit: int) -> None:
        """
        Append `file_name` to the header file for the given orbit.
        Creates the file if it does not yet exist.
        """
        headers_dir = self.get_headers_dir()

        header_path = os.path.join(
            headers_dir,
            CSVHandler._get_header_file_name(relative_orbit)
        )

        # Create file if missing
        if not os.path.exists(header_path):
            with open(header_path, "w", encoding="utf-8") as f:
                pass  # empty file created

        # Append new entry
        with open(header_path, "a", encoding="utf-8") as f:
            f.write(f"{file_name},\n")

    def _push_meta_to_json(self) -> None:
        with open(self._root_dir / self.META_FILENAME, 'w') as json_file:
            json.dump(self._meta, json_file, indent=4)  # indent for pretty-printing

    def _valdate_meta(self, meta: dict) -> dict:
        """
        validates wether the giiven meta dictionary is a valid one.
        Raises a ValueError if not, returns the dictionary if true
        """
        required_meta_keys = {"object_id_name",
                              "mother_collection_id",
                              "variables",
                              "properties",
                              "orbits"}
        for required_key in required_meta_keys:
            if not required_key in meta.keys():
                raise ValueError(f"The meta data is missing the required value {required_key}.")
        for orbit in meta["orbits"]:
            if not self._get_orbit_folder_name(orbit) in meta.keys():
                raise ValueError(f"The meta data indicates files from orbit {orbit} are present, but specifies none.")
            if not meta[self._get_orbit_folder_name(orbit)]:
                raise ValueError(f"The meta data indicates files from orbit {orbit} are present, but specifies none.")
            for file_name in meta[self._get_orbit_folder_name(orbit)]:
                file_path : Path = self._get_orbit_folder_path(orbit) / file_name
                if not file_path.exists():
                    raise ValueError(f"One of the specified files ({file_name}) in the meta data are not present in the orbit folders.")
        return meta

    def _initialize_meta_json(self, content: ImmutableReducedBatchCollection) -> None:
        """
        Initializes the meta json file with the general content from an ImmutableReducedBatchCollection instance.
        """
        self._meta = {
            #"name"  : NOTE: currently no meaningful implementation of name, but likely in future versions
            "object_id_name"    : content.get_object_id_name(),
            "mother_collection_id"  : content.get_mother_collection_id(),
            "variables"         : list(content.get_variables()),
            "properties"        : list(content.get_asset_properties()),
            "orbits"            : [],
            "orbit_collection_names"    : {},            
        }
        self._push_meta_to_json()

    def _write_meta_json(self, content: ImmutableReducedBatchCollection) -> None:
        if not self._meta["object_id_name"] == content.get_object_id_name():
            raise ValueError(f"The object ID name of the reduced batch collection ({content.get_object_id_name()}) "\
                             f"is not the same as that of previous files {self._meta["object_id_name"]}.")
        if not self._meta["mother_collection_id"] == content.get_mother_collection_id():
            raise ValueError("The given content is from a different mother collection than previously written content.")
        if not set(self._meta["variables"]) == content.get_variables():
            raise ValueError(f"The variables of the reduced batch collection ({list(content.get_variables())}) " \
                             f"are not the same as those of previous files {self._meta["variables"]}.")
        if not set(self._meta["properties"]) == content.get_asset_properties():
            raise ValueError(f"The properties of the reduced batch collection ({list(content.get_asset_properties())}) "\
                             f"are not the same as those of previous files {self._meta["properties"]}.")

        #TODO add orbit collection name logic here.
        ro = content.get_relative_orbit()
        if not ro in self._meta["orbits"]:
            self._meta["orbits"].append(ro)
            self._meta["orbit_collection_names"][str(ro)] = content.get_orbit_collection_name()
        elif not self._meta["orbit_collection_names"][str(ro)] == content.get_orbit_collection_name():
            raise ValueError("The instance of the given reduced batch collection does not share " \
            "the same orbit collection name as previous files.")

        key = self._get_orbit_folder_name(ro)
        if key not in self._meta:
            self._meta[key] = []
        if not self._get_csv_file_name(content) in self._meta[key]:
            self._meta[key].append(self._get_csv_file_name(content))

        self._push_meta_to_json()


    def _write_csv(self, content: ImmutableReducedBatchCollection, output_path: str) -> None:
        dataframe = content.get_collection()
        dataframe.to_csv(output_path)
    
    def _create_orbit_folder(self, relative_orbit: int) -> Path:
        """
        Creates an orbit folder for the given relative orbit.
        Does nothing of the folder already exists.
        """
        result = self._root_dir / CSVHandler._get_orbit_folder_name(relative_orbit)
        os.makedirs(result, exist_ok=True)
        return result

    def _write_reduced_batch_collection(self, reduced_collection: ImmutableReducedBatchCollection) -> None:
        relative_orbit = reduced_collection.get_relative_orbit()
        file_name = f"{reduced_collection.get_name()}.csv"
        folder_path = self._create_orbit_folder(relative_orbit)
        output_path = os.path.join(folder_path, file_name)

        self._write_csv(reduced_collection, output_path)
        self._write_header(file_name, relative_orbit)
        if not self._meta:
            self._initialize_meta_json(reduced_collection)
        self._write_meta_json(reduced_collection)
        self._relative_orbits.add(relative_orbit)
    
    def write(self, reduced_collection: ImmutableReducedOrbitCollection) -> None:
        """
        Writes a reduced collection to csv files. Considers the internal batching structure when doing so.
        """
        if not isinstance(reduced_collection, ImmutableReducedOrbitCollection):
            raise TypeError(f"'reduced_collection' must be of type ReducedOrbitCollection but is of type {type(reduced_vollection)}.")
        for batch_collection in reduced_collection.get_reduced_batch_collections():
            self._write_reduced_batch_collection(batch_collection)


    @staticmethod
    def _read_csv(path) -> pd.DataFrame:
        """ Bundles all csv reading. """
        df = pd.read_csv(path)
        if 'Unnamed: 0' in df.columns:
            df = df.rename(columns = {'Unnamed: 0': 'system:index'})
        return df
    
    @staticmethod
    def _derive_variable_set_from_df(dataframe: pd.DataFrame) -> set[str]:
        """ Derives the variable set from the column names of the given dataframe. """
        variables = set()
        for column_name in dataframe.columns:
            splitted = column_name.split('_')
            if not splitted[0] == 'S1A':
                continue
            variable = f"{splitted[-2]}_{splitted[-1]}"
            if variable in variables:
                break
            variables.add(variable)
        return variables

    def _derive_object_id_name(self, dataframe: pd.DataFrame) -> str:
        name = str(self._meta["object_id_name"])
        if name in dataframe.columns:
            return name
        raise ValueError(f"the object id name '{self._meta["object_id_name"]}' associated to files related to this folder is not found in the given dataframe {dataframe.columns}")

    @staticmethod
    def _derive_property_names(dataframe: pd.DataFrame, object_id_name: str) -> set[str]:
        """
        Derives the asset properties stored this dataframe.
        NOTE: it assumes properties are stored in the last collumns of the dataframe.
        """
        result = set()
        for column_name in reversed(dataframe.columns):
            if not column_name.startswith("S1"):
                result.add(column_name)
            else:
                break
        for column_name in dataframe.columns:
            if not column_name.startswith("S1"):
                result.add(column_name)
            else:
                break
        result.remove(object_id_name)
        return result
            
    def _read_to_a_reduced_batch_collection(self, file_name: str, relative_orbit: int|None = None) -> ImmutableReducedBatchCollection:
        """ 
        Creates an S1ReducedCollection from the given file. 
        Derives the relative orbit and variables from the given file.
        """
        #TODO update: work with json file to retreive all needed information
        #TODO remove system:index from this the properties.
        if not relative_orbit:
            relative_orbit = CSVHandler._get_relative_orbit_from_file_name(file_name)

        folder_path = self._create_orbit_folder(relative_orbit)
        file_path = os.path.join(folder_path, file_name)
        df = CSVHandler._read_csv(file_path)
        variables = CSVHandler._derive_variable_set_from_df(df)
        object_id_name = self._derive_object_id_name(df)
        properties = CSVHandler._derive_property_names(df, object_id_name)
        return ImmutableReducedBatchCollection(df, variables, file_name.rsplit('_', 1)[0], relative_orbit, object_id_name, properties, self._meta["mother_collection_id"])

    def read_to_reduced_orbit(self, relative_orbit: int) -> ImmutableReducedOrbitCollection:
        #TODO include json info
        # Convert to dictionary
        file_names = self.get_file_names_of_relative_orbit(relative_orbit)
        batch_collections = set()
        variables : set[str] = set(self._meta["variables"])
        properties : set[str] = set(self._meta["properties"])
        object_id_name : str =  self._meta["object_id_name"]
        relative_orbit_name : str = self._meta["orbit_collection_names"][str(relative_orbit)]
        for file_name in file_names:
            batch_collection = self._read_to_a_reduced_batch_collection(file_name)
            if variables != batch_collection.get_variables():
                raise ValueError("The variables of all files from the same orbit should be the same but are different.\n" \
                                 f"One batch contains variables {variables} while another contains {batch_collection.get_variables()}.")
            if self._meta["object_id_name"] != batch_collection.get_object_id_name():
                raise ValueError("The object id names of all batch collections should be the samet.\n" \
                                 f"One batch has name {object_id_name} while another has {batch_collection.get_object_id_name()}.")
            if properties != batch_collection.get_asset_properties():
                raise ValueError("The properties of all files from the same orbit should be the same but are different.\n" \
                    f"One batch contains properties {properties} while another contains {batch_collection.get_asset_properties()}.")
            if relative_orbit_name != batch_collection.get_name():
                raise ValueError("All collection from the relative orbit should have the same root in their name." \
                                 f"(These collection contain both {relative_orbit_name} and {batch_collection.get_name()})")
            batch_collections.add(batch_collection)

        assert relative_orbit_name is not None
        #variables = next(iter(batch_collections)) #first element
        return ImmutableReducedOrbitCollection(batch_collections,
                                               relative_orbit,
                                               variables,
                                               relative_orbit_name,
                                               object_id_name, properties,
                                               self._meta["mother_collection_id"])


    def get_root_dir(self) -> Path:
        """
        Returns the root directory.
        """
        return self._root_dir

    def get_headers_dir(self) -> Path:
        """
        Returns the path to the 'Headers' directory.
        """
        return self._root_dir / 'Headers'

    def get_file_names_of_relative_orbit(self, relative_orbit: int) -> set[str]:
        """
        Returns a set of all file names currently written for a relative orbit.
        """
        return set(self._meta[f"Orbit_{relative_orbit}"])

    def get_file_paths_of_relative_orbit(self, relative_orbit: int) -> set[Path]:
        """
        Returns a set of all file paths currently written for a relative orbit.
        """
        all_file_paths : set[Path] = set()
        for file_name in self.get_file_names_of_relative_orbit(relative_orbit):
            all_file_paths.add(self._get_orbit_folder_path(relative_orbit) / file_name)
        return all_file_paths
    
    def get_relative_orbits(self) -> set[int]:
        """
        Returns all relative orbits of which data is stored in this folder structure.
        """
        return self._relative_orbits.copy()
    
    def get_all_file_paths_per_orbit(self) -> dict[int, set[Path]]:
        """ 
        Returns a dictionary with the relative orbit numbers as keys
        and a set containing the file paths of each orbit.
        """
        result : dict[int, set[Path]] = {}
        for ro in self.get_relative_orbits():
            result[ro] = self.get_file_paths_of_relative_orbit(ro)
        return result

    

    

from pathlib import Path
import os
import json
from datetime import date


class S1MiningConfig:

    requiered_config_fields = {"years", 
                               "field_asset_paths", 
                                "variables", "units", 
                                "output_dir", 
                                "batch_size"}
    possible_variables = {"VV", "VH", "CP", "azimuth", "lia"}
    possible_units = {"dB", "linear"}

    def __init__(self, config_json_path: str):
        if config_json_path is None:
            raise ValueError("`config_json_path` cannot be None")
        
        config_path = Path(config_json_path)
        raw_config = self._open_json(config_path)
        self._check_config(raw_config)
        self.path = config_json_path
        self.config = raw_config  # store validated config

    # -------------------------
    # JSON loading
    # -------------------------
    @staticmethod
    def _open_json(config_path) -> dict:
        if not os.path.isfile(config_path):
            raise FileNotFoundError(f"Config file not found: {config_path}")

        try:
            with open(config_path, "r") as f:
                config = json.load(f)

        except json.JSONDecodeError as e:
            raise ValueError(f"Config file is not valid JSON: {config_path}\n{e}")

        except PermissionError:
            raise PermissionError(f"Insufficient permissions to read: {config_path}")

        return config

    # -------------------------
    # Validation
    # -------------------------    
    @staticmethod
    def _check_config_keys(my_dict: dict) -> None:
        missing = [k for k in S1MiningConfig.requiered_config_fields if str(k) not in my_dict]
        if missing:
            raise KeyError(f"Missing {missing} in config fields.")

    @staticmethod
    def _check_years(years: list) -> None:
        if not isinstance(years, list):
            raise TypeError(f"'years' values must be a list but is {type(years)}.")
        if not all(isinstance(year, int) for year in years):
            raise TypeError("'years' values must be a list of int values.")
        if any(2014 >= y > date.today().year for y in years):
            raise ValueError(f"`year` values must be between 2014 and {date.today().year}")
    
    @staticmethod
    def _check_field_assets(field_asset_dict: dict, required_years: list) -> None:
        if not isinstance(field_asset_dict, dict):
            raise TypeError("`field_asset_paths` must contain field - value pairs of the form '" + '{"YYYY": "asset_path"}' + "'.")
        available_years_list = list(field_asset_dict.keys())
        missing = [k for k in required_years if str(k) not in available_years_list]
        if not missing:
            raise ValueError(f"Not all requested years have a corresponding field_asset given.\n\
                             The following years are missing: {missing}.")
    
    @staticmethod
    def _check_requested_variables(variables: list) -> None:
        if not isinstance(variables, list):
            raise ValueError("'variables' values must be a list.")
        variable_set = set(variables)
        if not len(variable_set) == len(variables):
            raise ValueError("all 'variables' must be unique.")
        if not variable_set.issubset(S1MiningConfig.possible_variables):
            raise ValueError(f"All 'variables' must be one out of {S1MiningConfig.possible_variables}.")

    @staticmethod
    def _check_units(units: str) -> None:
        if not units in S1MiningConfig.possible_units:
            raise ValueError(f"'units' must be one of {S1MiningConfig.possible_units} but is {units}")

    @staticmethod
    def _check_output_directory(directory: str) -> None:
        if not isinstance(directory, str):
            raise ValueError("'output_dir' must be of type 'str'.")
        #TODO check if more checks are needed here

    @staticmethod
    def _check_batch_size(batch_size: int) -> None:
        if not isinstance(batch_size, int):
            raise TypeError(f"'batch_size' must be of type int but is of type {type(batch_size)}.")
        if batch_size < 1:
            raise ValueError(f"'batch_size' must be at least 1.")
        if batch_size > 500:
            raise Warning(f"A 'batch_size' larger than 500 is not recommended. Currently it is set to {batch_size}")

    @staticmethod
    def _check_config(config: dict) -> None:
        """
        Checks content of the given config. Throws exceptions or warnings if
        certain conditions are not met.
        """
        S1MiningConfig._check_config_keys(config, 
                                          S1MiningConfig.requiered_config_fields, 
                                          "config")

        S1MiningConfig._check_years(config["years"])
        S1MiningConfig._check_field_assets(config["field_asset_paths"], config["years"])
        S1MiningConfig._check_requested_variables(config["variables"])
        S1MiningConfig._check_units(config["units"])
        S1MiningConfig._check_output_directory(config["output_dir"])
        S1MiningConfig._check_batch_size(config["batch_size"])
    # -------------------------
    # Getters
    # -------------------------
    def get_full_config(self) -> dict:
        return self.config.copy()

    def get_years(self) -> list:
        return self.config["years"].copy()

    def get_all_fields_paths(self) -> dict:
        return self.config["field_asset_paths"].copy()

    def get_field_path_at_year(self, year: int) -> str:
        if year not in self.config["years"]:
            raise ValueError(
                f"{year} outside allowed years: {self.config['years']}"
            )
        return self.config["field_asset_paths"][str(year)]
    
    def get_goal_variables(self) -> list:
        """ returns variables to be implemented in final .nc file """
        return self.config["variables"].copy()
    
    def get_json_path(self) -> str:
        return self.path

    # -------------------------
    # String representation
    # -------------------------
    def __str__(self):
        return json.dumps(self.config, indent=4)
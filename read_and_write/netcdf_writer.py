from __future__ import annotations
import xarray as xr
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Optional
from S1.ReducedOrbitCollection import ReducedOrbitCollection

class NetCDFExporter:
    """
    Writes one NetCDF per variable, plus one shared RO-tracking NetCDF.
    """
 
    _output_dir : Path
    """
    Directory the .nc files are written to.
    """
        
    _object_id_name : str
    """
    Name of the OID dimension/coordinate (matches your collection's
    `self._object_id_name`), so files use consistent naming.
    """

    _file_dict : dict[str : Path]
    """
    Keeps track of where netcdf files per variable are stored.
    """
 
    def __init__(self, output_dir: Path, object_id_name: str = "OID"):
        """
        Initiates a NetCDFExporter instance. NetCDFs will be written to the
        'output_dir' and the 'object_id_name' will be used as ID column in
        the writing of the NetCDFs.
        """
        self._output_dir = Path(output_dir)
        self._output_dir.mkdir(parents=True, exist_ok=True)
        self._object_id_name = object_id_name
 
    def export_all(
        self,
        reduced_collection: ReducedOrbitCollection,
        wide_variable_dfs: dict[str, pd.DataFrame],
        wide_ro_df: pd.DataFrame,
        embed_ro: bool = False,
    ) -> None:
        """
        wide_variable_dfs : output of collection.create_wide_variable_dfs()
        wide_ro_df        : output of collection.create_wide_ro_tracking_df()
        embed_ro          : if True, also copy the RO grid into every
                             per-variable file (self-contained files at
                             the cost of duplicated data on disk).
        """
        #TODO check this logic
        dataframe_dict: dict[str, pd.DataFrame] = reduced_collection.create_wide_variable_dfs()
        ro_index, ro_names = self._encode_ro_categorical(wide_ro_df)
 
        # always write the single source-of-truth RO file
        self._write_ro_netcdf(ro_index, ro_names)
 
        for variable, df in wide_variable_dfs.items():
            self._write_variable_netcdf(
                variable,
                df,
                ro_index_to_embed=(ro_index, ro_names) if embed_ro else None,
            )
 
    # -- internals -----------------------------------------------------
 
    def _to_dataarray(self, values: np.ndarray, index, columns, name: str) -> xr.DataArray:
        #TODO check this logic
        return xr.DataArray(
            values,
            dims=(self.object_id_name, "timestamp"),
            coords={self.object_id_name: index, "timestamp": columns},
            name=name,
        )
 
    def _encode_ro_categorical(self, wide_ro_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Index]:
        #TODO: check this logic
        """Map RO identifiers (any hashable, usually str) -> int32 codes."""
        wide_ro_df = wide_ro_df.sort_index().sort_index(axis=1)
        unique_ros = pd.Index(sorted(wide_ro_df.stack().dropna().unique()))
        code_map = {ro: i for i, ro in enumerate(unique_ros)}
        codes = wide_ro_df.applymap(lambda v: code_map.get(v, -1)).astype("int32")
        return codes, unique_ros
 
    def _write_variable_netcdf(
        self,
        variable: str,
        df: pd.DataFrame,
        ro_index_to_embed: Optional[tuple[pd.DataFrame, pd.Index]] = None,
    ) -> None:
        #TODO check this logic
        df = df.sort_index().sort_index(axis=1)
        da = self._to_dataarray(df.values, df.index, df.columns, variable)
        ds = da.to_dataset()
 
        if ro_index_to_embed is not None:
            ro_codes, ro_names = ro_index_to_embed
            ro_aligned = ro_codes.reindex(index=df.index, columns=df.columns).fillna(-1).astype("int32")
            ds["ro_index"] = self._to_dataarray(ro_aligned.values, df.index, df.columns, "ro_index")
            ds["ro_names"] = xr.DataArray(ro_names.values, dims=("ro",), name="ro_names")
            ds["ro_index"].attrs["description"] = (
                "index into ro_names giving the RO each observation came from; -1 = missing"
            )
 
        ds[variable].attrs.setdefault("long_name", variable)
        path = self.output_dir / f"{variable}.nc"
        ds.to_netcdf(path)
 
    def _write_ro_netcdf(self, ro_index: pd.DataFrame, ro_names: pd.Index) -> None:
        #TODO check this logic
        da = self._to_dataarray(ro_index.values, ro_index.index, ro_index.columns, "ro_index")
        ds = da.to_dataset()
        ds["ro_names"] = xr.DataArray(ro_names.values, dims=("ro",), name="ro_names")
        ds["ro_index"].attrs["description"] = (
            "index into ro_names giving the RO each observation came from; -1 = missing"
        )
        ds.to_netcdf(self.output_dir / "ro_tracking.nc")
import os
import ee
import numpy as np
import FeatureManipulation.PolygonFeatureUtils as PolygonFeatureUtils
import FeatureManipulation.FeatureCollectionUtils as FeatureCollectionUtils
from S1.ImmutableCollection import S1ImmutableCollection

ee.Initialize()

years = (2020)

asset_dict = {
    2020 : "test_path"
}

root_data_path = "test_root_path"
batch_size = 9999

for year in years:
    # Path where to store the data (for the named year per orbit)
    out_path_year = os.path.join(root_data_path, year)
    os.makedirs(out_path_year, exist_ok=True)

    field_asset_path = asset_dict[str(year)] #TODO
    fields = ee.FeatureCollection(field_asset_path)

    StartDate = f"{year}-01-01"
    EndDate   = f"{year}-12-31"

    fields = FeatureCollectionUtils.buffer_fields(fields, -10)
    fields = FeatureCollectionUtils.add_centroid_property(fields)
    batch_dict = FeatureCollectionUtils.split_features_into_batches(fields)

    s1_collection = S1ImmutableCollection(fields, StartDate, EndDate)
    for s1_ro_collection in s1_collection.split_into_relative_orbit_collections():
        s1_ro_collection.filter_border_noise()
        s1_ro_collection.add_linear_cross_polarization()
        s1_ro_collection.add_azimuth_and_local_incidence_angle()
        for batch_id, batch in batch_dict.items():
            s1_ro_collection.reduce_to_csv(batch, out_path_year, batch_id)


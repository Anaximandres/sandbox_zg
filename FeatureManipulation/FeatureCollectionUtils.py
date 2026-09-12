import ee
import math
import FeatureManipulation.PolygonFeatureUtils as PolygonFeatureUtils
import pandas as pd
import os
from utils.Batch import BatchID

def add_centroid_property(features: ee.FeatureCollection) -> ee.FeatureCollection:
    """
    Takes an ee.FeatureCollection instance that consists of ee.Features
    that describe a polygon and adds the centroid as a property called 
    'polygon_centroid' to them
    """
    return features.map(PolygonFeatureUtils.add_centroid_property)

import ee


def get_feature_properties(features: ee.FeatureCollection) -> set[str]:
    """
    Returns the set of property names shared by every feature in this
    feature collection.

    Raises:
        ValueError: if the collection is empty, or if features in the
            collection don't all have the same set of properties.
    """
    size = features.size().getInfo()
    if size == 0:
        return set()

    # Server-side: for each feature, produce its sorted property-name list.
    # Sorting means differently-ordered-but-identical property sets compare equal.
    per_feature_names = features.map(
        lambda f: ee.Feature(None, {"names": f.propertyNames().sort()})
    ).aggregate_array("names")

    names_list = per_feature_names.getInfo()  # single round trip

    first, *rest = names_list
    if any(names != first for names in rest):
        raise ValueError(
            "Features in the collection do not all share the same properties."
        )

    return set(first)

def buffer_fields(features: ee.FeatureCollection, buffer_size: int = -10) -> ee.FeatureCollection:
    """
    Returns the input buffered by a given distance.

    If the distance is positive, the geometry is expanded, 
    and if the distance is negative, the geometry is contracted.
    """
    return features.map(lambda field: PolygonFeatureUtils.buffer_field(field, buffer_size))

def split_features_into_batches(features: ee.FeatureCollection, batch_size: int = 500) -> dict[str, ee.FeatureCollection]:
    """
    Splits the given feature collection into a list of feature collections, 
    each of size no larger than the batch size.
    """
    features_size = features.size().getInfo()  # bring size client-side for control flow
    assert features_size is not None
    if features_size <= batch_size:
        return {"1of1": features}

    num_batches = math.ceil(features_size / batch_size)
    feature_list = features.toList(features_size)  # server-side ee.List of all features

    batch_dict = {}
    batch_names = sorted(BatchID.generate_batch_ids(num_batches))
    for i in range(num_batches):
        start = i * batch_size
        end = min(start + batch_size, features_size)
        batch = ee.FeatureCollection(feature_list.slice(start, end))
        batch_dict[batch_names[i]] = batch

    return batch_dict

def feature_collection_to_df(collection: ee.FeatureCollection, batch_size:int=5000, include_geometry:bool = False) -> pd.DataFrame:
    """
    Creates a pandas dataframe based on the given ee.FeatureCollection instance.
    Each feature in of that instance will be represented by a seperate row.
    """

    size = collection.size().getInfo()
    assert size is not None
    rows = []
    for start in range(0, size, batch_size):
        # Slice out just this batch of features and fetch it
        batch_fc = ee.FeatureCollection(collection.toList(batch_size, start))
        batch_info = batch_fc.getInfo()
        assert batch_info is not None
        for feature in batch_info['features']:
            row = dict(feature['properties'])

            if include_geometry:
                geom = feature.get('geometry')
                if geom:
                    row['geometry_type'] = geom.get('type')
                    row['geometry_coordinates'] = geom.get('coordinates')

            rows.append(row)

    return pd.DataFrame(rows)

def feature_collection_to_csv(collection: ee.FeatureCollection, out_path: str) -> str:
    """
    Writes the given collection to a csv with every feature on a seperate row
    and properties as column values.
    """
    if not out_path.endswith('.csv'):
        raise ValueError("'out_path' must be a .csv file.")
    out_dir = os.path.dirname(out_path)
    if out_dir and not os.path.isdir(out_dir):
        raise ValueError(f"Directory '{out_dir}' does not exist.")

    df = feature_collection_to_df(collection)
    df.to_csv(out_path, index=False)
    print(f"Wrote {len(df)} rows, {len(df.columns)} columns to {out_path}")
    return out_path

import ee
import typing

def add_centroid_property(feature: ee.Feature) -> ee.Feature:
    """
    Takes an ee.Feature instance that is a polygon and
    adds the centroid as a propertu called 'polygon_centroid'
    """
    polygon_centroid = feature.geometry().centroid()
    updated = feature.set({'polygon_centroid': polygon_centroid})
    return typing.cast(ee.Feature, updated)

def buffer_field(feature: ee.Feature, buffer_size: int = -10) -> ee.Feature:
    """
    Returns the input buffered by a given distance.

    If the distance is positive, the geometry is expanded, 
    and if the distance is negative, the geometry is contracted.
    :param feature: polygon in projection ESPG:42
    """
    return feature.buffer(buffer_size)


import os
import pytest
import ee
from EeImageCollections.ImageCollection import ImageCollection
from EeImageCollections.S1_GRD.S1GRD_MultiOrbitCollection import S1GRD_MultiOrbitCollection
from typing import Literal

pytestmark = pytest.mark.skipif(
    not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"),
    reason="Earth Engine credentials not configured"
)

def create_polygon():
    return ee.Geometry.Polygon([[
        [4.8, 52.3],
        [5.0, 52.3],
        [5.0, 52.4],
        [4.8, 52.4],
        [4.8, 52.3],
    ]])

def create_test_instance():
    roi = create_polygon()
    return S1GRD_MultiOrbitCollection.of(roi, '2024-01-01', '2024-12-31', 'db')

def create_test_instance_linear():
    roi = create_polygon()
    return S1GRD_MultiOrbitCollection.of(roi, '2024-01-01', '2024-12-31', 'linear')


def test_earth_engine_initialization():
    ee.Initialize()
    assert ee.Number(1).getInfo() == 1

def test_get_bands():
    ee.Initialize()
    collection = create_test_instance()
    assert {'VV', 'VH', 'angle'} == collection.get_bands()

def test_get_units_db():
    ee.Initialize()
    collection = create_test_instance()
    assert 'db' == collection.get_units()

def test_get_units_linear():
    ee.Initialize()
    collection = create_test_instance_linear()
    assert 'linear' == collection.get_units()

def test_get_relative_orbits():
    ee.Initialize()
    collection = create_test_instance_linear()
    relative_orbits = collection.get_relative_orbits()
    assert relative_orbits
    assert isinstance(relative_orbits, set)
    assert all(isinstance(ro, int) for ro in relative_orbits)
    relative_orbits.add(9999)
    assert relative_orbits != collection.get_relative_orbits()

def test_get_time_period():
    ee.Initialize()
    roi = create_polygon()
    start_date = '2024-01-01'
    end_date = '2024-12-31'
    collection =  S1GRD_MultiOrbitCollection.of(roi, start_date, end_date, 'db')
    assert (start_date, end_date) == collection.get_time_period()

def test_get_start_year():
    ee.Initialize()
    roi = create_polygon()
    start_date = '2024-01-01'
    end_date = '2024-12-31'
    collection =  S1GRD_MultiOrbitCollection.of(roi, start_date, end_date, 'db')
    assert 2024 == collection.get_start_year()

def test_get_relative_orbit_info():
    ee.Initialize()
    collection = create_test_instance_linear()
    my_dict = collection.get_relative_orbit_info()
    assert isinstance(my_dict, dict)
    assert all(isinstance(key, int) for key in my_dict.keys())
    assert all(isinstance(value, Literal['ASCENDING', 'DESCENDING']) for value in my_dict.values())
    assert set(my_dict.keys()) == collection.get_relative_orbits()

def test_get_collection_name():
    ee.Initialize()
    collection = create_test_instance()
    assert 'COPERNICUS/S1_GRD' == collection.get_collection_name()
    linear_collection = create_test_instance_linear()
    assert 'COPERNICUS/S1_GRD_FLOAT' == collection.get_collection_name()

def test_get_collection_id():
    ee.Initialize()
    collection = create_test_instance()
    collection2 = create_test_instance()
    linear_collection = create_test_instance_linear()
    assert collection == collection2
    assert collection.get_collection_id != linear_collection.get_collection_id()

def test_get_scale():
    ee.Initialize()
    collection = create_test_instance()
    isinstance(collection.get_scale(), ee.Number())

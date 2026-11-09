import pytest
from shapely.geometry import box
from app.gis import read_aoi_geojson,tile_plan,bound_coverage,approximate_area_km2

def test_small():
    g=read_aoi_geojson({"type":"Polygon","coordinates":[[[88,23],[88.1,23],[88.1,23.1],[88,23.1],[88,23]]]})
    assert 100<approximate_area_km2(g)<130
    assert len(tile_plan(g))==1

def test_multi_tiles():
    assert len(tile_plan(box(88.7,23.7,89.2,24.2)))==4

def test_coverage():
    assert bound_coverage(box(0,65,1,66),"SRTMGL1") is None
    assert bound_coverage(box(0,59.5,1,60.5),"SRTMGL1").bounds[3]==60

def test_bad_coordinates():
    with pytest.raises(ValueError):
        read_aoi_geojson({"type":"Polygon","coordinates":[[[200,0],[201,0],[201,1],[200,1],[200,0]]]})

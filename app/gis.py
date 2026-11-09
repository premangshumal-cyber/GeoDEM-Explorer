"""AOI geometry, shapefile validation and geographic request tiling."""
import json
import math
from pathlib import Path
import zipfile
import geopandas as gpd
from shapely.geometry import box, mapping, shape
from shapely.ops import unary_union

DATASETS = {
    "COP30": {"name":"Copernicus GLO-30","resolution":"~30 m","lat_limit":90,"description":"Digital Surface Model"},
    "AW3D30": {"name":"ALOS AW3D30","resolution":"~30 m","lat_limit":82,"description":"Digital Surface Model"},
    "SRTMGL1": {"name":"NASA SRTM GL1","resolution":"~30 m","lat_limit":56,"north_limit":60,"description":"Radar DEM"},
    "NASADEM": {"name":"NASADEM","resolution":"~30 m","lat_limit":56,"north_limit":60,"description":"Reprocessed SRTM"},
    "COP90": {"name":"Copernicus GLO-90","resolution":"~90 m","lat_limit":90,"description":"Digital Surface Model"}
}

def polygonal(g):
    if g.is_empty:
        raise ValueError("Empty study area")
    if not g.is_valid:
        g=g.buffer(0)
    if g.geom_type in ("Polygon","MultiPolygon"):
        return g
    if g.geom_type=="GeometryCollection":
        pieces=[p for p in g.geoms if p.geom_type in ("Polygon","MultiPolygon")]
        if pieces:
            return unary_union(pieces)
    raise ValueError("AOI must contain polygons, not lines or points")

def validate(g):
    g=polygonal(g)
    w,s,e,n=g.bounds
    if not all(math.isfinite(v) for v in (w,s,e,n)) or not (-180<=w<e<=180 and -90<=s<n<=90):
        raise ValueError("AOI requires valid longitude/latitude in WGS84")
    if e-w>180:
        raise ValueError("Antimeridian crossing is not supported yet")
    if len(g.wkb)>8000000:
        raise ValueError("Geometry too complex")
    return g

def read_aoi_geojson(data):
    kind=data.get("type")
    if kind=="FeatureCollection":
        fs=data.get("features",[])
        if not fs or len(fs)>10000:
            raise ValueError("Invalid feature count")
        items=[shape(f["geometry"]) for f in fs if f.get("geometry")]
        if not items:
            raise ValueError("No polygon geometry in file")
        g=unary_union(items)
    elif kind=="Feature":
        g=shape(data["geometry"])
    else:
        g=shape(data)
    return validate(g)

def read_shapefile_zip(archive_path:Path,folder:Path):
    folder.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(archive_path) as z:
        members=[v for v in z.infolist() if not v.is_dir()]
        if len(members)>100 or sum(v.file_size for v in members)>150*1024*1024:
            raise ValueError("Unsafe archive size or number of files")
        paths=[Path(v.filename) for v in members]
        if any(p.is_absolute() or ".." in p.parts for p in paths):
            raise ValueError("Unsafe archive path")
        shp=[p for p in paths if p.suffix.lower()==".shp"]
        if len(shp)!=1:
            raise ValueError("ZIP must contain one shapefile")
        name=shp[0]
        parts={p.suffix.lower() for p in paths if p.with_suffix("").as_posix().lower()==name.with_suffix("").as_posix().lower()}
        if not {".shp",".shx",".dbf",".prj"}.issubset(parts):
            raise ValueError("ZIP needs matching .shp, .shx, .dbf and .prj")
        for member in members:
            p=Path(member.filename)
            if p.suffix.lower() not in {".shp",".shx",".dbf",".prj",".cpg"}:
                continue
            dest=folder/p.name
            if dest.exists():
                raise ValueError("Duplicate shapefile component")
            with z.open(member) as source,dest.open("wb") as target:
                import shutil
                shutil.copyfileobj(source,target)
    frame=gpd.read_file(folder/name.name)
    if frame.empty or frame.crs is None:
        raise ValueError("Empty shapefile or missing .prj")
    return validate(unary_union([g for g in frame.to_crs("EPSG:4326").geometry if g is not None and not g.is_empty]))

def approximate_area_km2(g):
    from pyproj import Geod
    area,_=Geod(ellps="WGS84").geometry_area_perimeter(g)
    return abs(area)/1e6

def bound_coverage(g,d):
    meta=DATASETS[d]
    clipped=g.intersection(box(-180,-meta["lat_limit"],180,meta.get("north_limit",meta["lat_limit"])))
    return polygonal(clipped) if not clipped.is_empty and clipped.area>0 else None

def tile_plan(g,step=1):
    w,s,e,n=g.bounds
    result=[]
    for y in range(math.floor(s/step),math.ceil(n/step)):
        for x in range(math.floor(w/step),math.ceil(e/step)):
            section=g.intersection(box(x*step,y*step,(x+1)*step,(y+1)*step))
            if not section.is_empty and section.area>1e-12:
                a,b,c,d=section.bounds
                pad=0.00004
                result.append({"west":max(-180,a-pad),"south":max(-90,b-pad),"east":min(180,c+pad),"north":min(90,d+pad)})
    return result

def save_feature(g,path):
    path.write_text(json.dumps({"type":"FeatureCollection","features":[{"type":"Feature","properties":{},"geometry":mapping(g)}]}),encoding="utf-8")

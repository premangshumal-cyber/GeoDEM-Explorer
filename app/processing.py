"""OpenTopography downloader, GDAL mosaic/cutline and ZIP packaging."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from zipfile import ZipFile, ZIP_DEFLATED
import rasterio
import requests
from .gis import approximate_area_km2,bound_coverage,tile_plan,save_feature

DATA_DIR=Path(os.getenv("DATA_DIR","./data")).resolve()
DATA_DIR.mkdir(parents=True,exist_ok=True)
POOL=ThreadPoolExecutor(max_workers=int(os.getenv("JOB_WORKERS","2")))
JOBS={}
LOCK=threading.Lock()

def get_job(id):
    with LOCK:
        return dict(JOBS[id]) if id in JOBS else None

def update(id,**fields):
    with LOCK:
        JOBS[id].update(fields)

def create_job(id,aoi,datasets):
    plans={}
    maximum=int(os.getenv("MAX_TILES_PER_DATASET","64"))
    for name in datasets:
        clip=bound_coverage(aoi,name)
        tiles=tile_plan(clip) if clip is not None else []
        if len(tiles)>maximum:
            raise ValueError(f"{name} needs {len(tiles)} requests (limit {maximum}); select a smaller AOI")
        plans[name]={"aoi":clip,"tiles":tiles}
    total_tiles=sum(len(item["tiles"]) for item in plans.values())
    total_limit=int(os.getenv("MAX_TOTAL_TILE_REQUESTS","999"))
    if total_tiles>total_limit:
        raise ValueError(f"Request requires {total_tiles} tiles across datasets, exceeding the server limit of {total_limit}. Reduce products or AOI.")
    with LOCK:
        busy=sum(1 for j in JOBS.values() if j["status"] in ("queued","running"))
        if busy>=int(os.getenv("MAX_ACTIVE_JOBS","2")):
            raise ValueError("The free DEM worker is busy. Try again when the current job finishes.")
        JOBS[id]={"id":id,"status":"queued","progress":0,"message":"Queued","datasets":datasets,
                  "files":[],"errors":[],"area_km2":round(approximate_area_km2(aoi),2),
                  "tiles_planned":{n:len(p["tiles"]) for n,p in plans.items()},
                  "created_at":datetime.now(timezone.utc).isoformat()}
    POOL.submit(worker,id,plans)
    return get_job(id)

def fetch_tile(session,name,bbox,out,key):
    params={"demtype":name,"outputFormat":"GTiff","API_Key":key,**bbox}
    timeout=int(os.getenv("REQUEST_TIMEOUT_SECONDS","240"))
    try:
        with session.get("https://portal.opentopography.org/API/globaldem",params=params,stream=True,timeout=(20,timeout)) as r:
            if r.status_code!=200:
                raise RuntimeError(f"OpenTopography HTTP {r.status_code}: check coverage, quota and API authorization")
            typ=r.headers.get("content-type","").lower()
            if "json" in typ or "html" in typ or "text/" in typ:
                raise RuntimeError("Provider response was not a GeoTIFF")
            size=0
            with out.open("wb") as target:
                for block in r.iter_content(chunk_size=1048576):
                    if block:
                        size+=len(block)
                        if size>int(os.getenv("MAX_TILE_MB","1500"))*1024*1024:
                            raise RuntimeError("Raster tile exceeds server byte limit")
                        target.write(block)
        with rasterio.open(out) as src:
            if not src.count or not src.width or not src.height:
                raise RuntimeError("Empty provider raster")
    except requests.RequestException as e:
        out.unlink(missing_ok=True)
        raise RuntimeError("OpenTopography connection error: "+type(e).__name__) from None
    except Exception:
        out.unlink(missing_ok=True)
        raise

def run_gdal(args):
    try:
        p=subprocess.run(args,capture_output=True,text=True,timeout=240,check=False)
    except FileNotFoundError:
        raise RuntimeError("GDAL commands unavailable; install environment.yml") from None
    if p.returncode:
        raise RuntimeError("GDAL error: "+(p.stderr or p.stdout)[-1000:])

def process_one(job_id,name,plan,root,session,key,done,total):
    if not plan["tiles"]:
        return None,done,"No coverage for this AOI"
    tile_folder=root/("tiles_"+name)
    tile_folder.mkdir(exist_ok=True)
    paths=[]
    try:
        for i,bbox in enumerate(plan["tiles"]):
            path=tile_folder/f"tile_{i:04d}.tif"
            update(job_id,message=f"{name}: download {i+1}/{len(plan['tiles'])}")
            fetch_tile(session,name,bbox,path,key)
            paths.append(path)
            done+=1
            update(job_id,progress=round(done/total*85,1))
        clip=root/(name+"_boundary.geojson")
        save_feature(plan["aoi"],clip)
        vrt=root/(name+"_mosaic.vrt")
        run_gdal(["gdalbuildvrt","-overwrite","-resolution","highest",str(vrt),*[str(p) for p in paths]])
        update(job_id,message=name+": merge and crop")
        out=root/(name+"_clipped.tif")
        run_gdal(["gdalwarp","-overwrite","-of","GTiff","-cutline",str(clip),"-crop_to_cutline",
                  "-dstnodata","-9999","-co","TILED=YES","-co","COMPRESS=DEFLATE",
                  "-co","BIGTIFF=IF_SAFER","-wm","32","-wo","NUM_THREADS=1",str(vrt),str(out)])
        with rasterio.open(out) as src:
            info={"dataset":name,"filename":out.name,"size_bytes":out.stat().st_size,
                  "width":src.width,"height":src.height,"crs":str(src.crs),
                  "nodata":src.nodata,"resolution":list(src.res),"bounds":list(src.bounds)}
        return info,done,None
    finally:
        shutil.rmtree(tile_folder,ignore_errors=True)

def worker(job_id,plans):
    folder=DATA_DIR/job_id
    folder.mkdir(exist_ok=True)
    key=os.getenv("OPENTOPOGRAPHY_API_KEY","")
    total=sum(len(v["tiles"]) for v in plans.values()) or 1
    done=0
    outputs=[]
    warnings=[]
    update(job_id,status="running",message="Processing DEMs")
    try:
        with requests.Session() as session:
            session.headers.update({"User-Agent":"GeoDEMExplorer/1.0 (research GIS)"})
            for name,plan in plans.items():
                try:
                    result,done,reason=process_one(job_id,name,plan,folder,session,key,done,total)
                    if result:
                        outputs.append(result)
                    if reason:
                        warnings.append(name+": "+reason)
                except Exception as e:
                    warnings.append(name+": "+str(e).replace(key,"[redacted]")[:400])
                update(job_id,files=list(outputs),errors=list(warnings),progress=min(90,round(done/total*85,1)))
        if not outputs:
            raise RuntimeError("No products completed: "+" | ".join(warnings))
        manifest={"project":"GeoDEM Explorer","created":datetime.now(timezone.utc).isoformat(),
                  "source":"OpenTopography Global DEM API","selected":list(plans),
                  "outputs":outputs,"warnings":warnings}
        (folder/"metadata.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
        update(job_id,message="Preparing ZIP",progress=95)
        archive=folder/"GeoDEM_Explorer_outputs.zip"
        with ZipFile(archive,"w",ZIP_DEFLATED,compresslevel=1,allowZip64=True) as z:
            for item in outputs:
                z.write(folder/item["filename"],item["filename"])
            z.write(folder/"metadata.json","metadata.json")
        update(job_id,status="completed",progress=100,message="Ready for download",files=outputs,errors=warnings)
    except Exception as e:
        update(job_id,status="failed",message=str(e).replace(key,"[redacted]")[:800],errors=warnings)

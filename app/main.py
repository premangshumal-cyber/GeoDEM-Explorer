"""FastAPI app: area upload, download jobs and web UI."""
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import uuid
from fastapi import FastAPI,UploadFile,File,HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel,Field
from .gis import DATASETS,read_aoi_geojson,read_shapefile_zip,approximate_area_km2
from .processing import DATA_DIR,create_job,get_job

ROOT=Path(__file__).resolve().parent
app=FastAPI(title="GeoDEM Explorer",version="1.0")
app.mount("/static",StaticFiles(directory=str(ROOT/"static")),name="static")

class JobRequest(BaseModel):
    aoi:dict
    datasets:list[str]=Field(min_length=1,max_length=5)

@app.get("/")
def index():
    return FileResponse(ROOT/"static"/"index.html")

@app.get("/api/health")
def health():
    return {"status":"ok"}

@app.get("/api/config")
def config():
    key=os.getenv("OPENTOPOGRAPHY_API_KEY","")
    return {"datasets":DATASETS,"key_configured":bool(key) and key!="YOUR_PERSONAL_API_KEY",
            "max_tiles":int(os.getenv("MAX_TILES_PER_DATASET","64")),
            "max_area_km2":float(os.getenv("MAX_AREA_KM2","300000"))}

@app.post("/api/aoi/upload")
async def upload_aoi(file:UploadFile=File(...)):
    ext=Path(file.filename or "").suffix.lower()
    if ext not in (".zip",".geojson",".json"):
        raise HTTPException(400,"Upload a GeoJSON or zipped shapefile")
    limit=int(os.getenv("MAX_UPLOAD_MB","25"))*1024*1024
    content=await file.read(limit+1)
    if len(content)>limit:
        raise HTTPException(413,"Upload size limit exceeded")
    try:
        if ext==".zip":
            with TemporaryDirectory(dir=DATA_DIR) as temp:
                folder=Path(temp)
                archive=folder/"aoi.zip"
                archive.write_bytes(content)
                geom=read_shapefile_zip(archive,folder/"extract")
        else:
            geom=read_aoi_geojson(json.loads(content))
        return {"type":"Feature","properties":{},"geometry":geom.__geo_interface__,
                "area_km2":round(approximate_area_km2(geom),2)}
    except Exception as e:
        raise HTTPException(422,str(e)) from None

@app.post("/api/jobs")
def submit(req:JobRequest):
    key=os.getenv("OPENTOPOGRAPHY_API_KEY","")
    if not key or key=="YOUR_PERSONAL_API_KEY":
        raise HTTPException(503,"Server API key not configured")
    if len(set(req.datasets))!=len(req.datasets) or any(d not in DATASETS for d in req.datasets):
        raise HTTPException(400,"Unsupported or duplicate dataset")
    try:
        geom=read_aoi_geojson(req.aoi)
        area=approximate_area_km2(geom)
        if area>float(os.getenv("MAX_AREA_KM2","300000")):
            raise ValueError(f"AOI {area:,.0f} km² exceeds current server area limit")
        return create_job(uuid.uuid4().hex,geom,req.datasets)
    except ValueError as e:
        raise HTTPException(422,str(e)) from None

@app.get("/api/jobs/{job_id}")
def status(job_id:str):
    job=get_job(job_id)
    if job is None:
        raise HTTPException(404,"Unknown job")
    return job

@app.get("/api/jobs/{job_id}/download/{filename}")
def download(job_id:str,filename:str):
    job=get_job(job_id)
    if not job or job["status"]!="completed":
        raise HTTPException(404,"Job not complete")
    allowed={p["filename"] for p in job["files"]}|{"GeoDEM_Explorer_outputs.zip","metadata.json"}
    if filename not in allowed:
        raise HTTPException(404,"File not part of job")
    path=DATA_DIR/job_id/filename
    if not path.is_file():
        raise HTTPException(404,"File not found")
    return FileResponse(path,filename=filename,media_type="application/octet-stream")

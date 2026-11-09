"""End-to-end synthetic GDAL smoke test. Never calls the external DEM provider."""
import shutil
import time
import uuid
import numpy as np
import pytest
import rasterio
from rasterio.transform import from_bounds
from shapely.geometry import box
from app import processing

@pytest.mark.skipif(not shutil.which("gdalbuildvrt") or not shutil.which("gdalwarp"),reason="GDAL CLI not available")
def test_mosaic_crop_and_zip(tmp_path,monkeypatch):
    monkeypatch.setattr(processing,"DATA_DIR",tmp_path)
    monkeypatch.setenv("OPENTOPOGRAPHY_API_KEY","nonproduction-test-key")
    def synthetic_tile(session,dataset,bbox,target,api_key):
        assert dataset=="COP30"
        assert api_key=="nonproduction-test-key"
        values=np.full((1,30,30),123,dtype="int16")
        with rasterio.open(target,"w",driver="GTiff",height=30,width=30,count=1,
                           dtype="int16",crs="EPSG:4326",nodata=-9999,
                           transform=from_bounds(bbox["west"],bbox["south"],bbox["east"],bbox["north"],30,30)) as dst:
            dst.write(values)
    monkeypatch.setattr(processing,"fetch_tile",synthetic_tile)
    job_id=uuid.uuid4().hex
    created=processing.create_job(job_id,box(88.9,23.9,89.1,24.1),["COP30"])
    assert created["tiles_planned"]["COP30"]==4
    deadline=time.monotonic()+35
    while time.monotonic()<deadline:
        job=processing.get_job(job_id)
        if job["status"] in ("completed","failed"):
            break
        time.sleep(0.2)
    assert job["status"]=="completed",job["message"]
    assert len(job["files"])==1
    outfile=tmp_path/job_id/"COP30_clipped.tif"
    archive=tmp_path/job_id/"GeoDEM_Explorer_outputs.zip"
    assert outfile.exists() and archive.exists()
    with rasterio.open(outfile) as src:
        pixels=src.read(1,masked=True)
        assert src.crs.to_epsg()==4326
        assert pixels.count()>0
        assert np.all(pixels.compressed()==123)

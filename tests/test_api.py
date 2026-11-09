from fastapi.testclient import TestClient
from app.main import app
client=TestClient(app)

def test_home():
    assert "GeoDEM" in client.get("/").text

def test_config():
    c=client.get("/api/config")
    assert c.status_code==200
    assert {"COP30","AW3D30","NASADEM","SRTMGL1","COP90"}.issubset(c.json()["datasets"])
    assert "api_key" not in c.json()

def test_upload_geojson():
    data=b'{"type":"Polygon","coordinates":[[[88,23],[88.1,23],[88.1,23.1],[88,23.1],[88,23]]]}'
    result=client.post("/api/aoi/upload",files={"file":("aoi.geojson",data,"application/json")})
    assert result.status_code==200
    assert result.json()["area_km2"]>100

def test_unsafe_extension():
    assert client.post("/api/aoi/upload",files={"file":("bad.exe",b"x","application/octet-stream")}).status_code==400

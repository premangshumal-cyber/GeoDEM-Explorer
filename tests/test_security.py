"""Security regression tests for public GDAL job submission."""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def sample_job():
    return {
        "aoi": {"type":"Polygon","coordinates":[[[88,23],[88.1,23],[88.1,23.1],[88,23.1],[88,23]]]},
        "datasets":["COP30"]
    }

def test_jobs_require_private_code(monkeypatch):
    monkeypatch.setenv("GEODEM_ACCESS_TOKEN","a-private-test-access-code")
    monkeypatch.setenv("OPENTOPOGRAPHY_API_KEY","fake-local-test-api-key")
    response=client.post("/api/jobs",json=sample_job())
    assert response.status_code==401
    response=client.post("/api/jobs",json=sample_job(),headers={"X-GeoDEM-Access-Token":"wrong"})
    assert response.status_code==401

def test_missing_backend_code_fails_closed(monkeypatch):
    monkeypatch.delenv("GEODEM_ACCESS_TOKEN",raising=False)
    response=client.post("/api/jobs",json=sample_job())
    assert response.status_code==503

def test_config_never_returns_credentials(monkeypatch):
    monkeypatch.setenv("GEODEM_ACCESS_TOKEN","test-secret-code")
    monkeypatch.setenv("OPENTOPOGRAPHY_API_KEY","secret-provider-key")
    result=client.get("/api/config")
    assert result.status_code==200
    assert "test-secret-code" not in result.text
    assert "secret-provider-key" not in result.text
    assert result.json()["token_required"] is True

def test_cors_allows_frontend_only():
    r=client.options("/api/jobs",headers={"Origin":"https://geodem-explorer.vercel.app",
        "Access-Control-Request-Method":"POST",
        "Access-Control-Request-Headers":"x-geodem-access-token,content-type"})
    assert r.headers.get("access-control-allow-origin")=="https://geodem-explorer.vercel.app"

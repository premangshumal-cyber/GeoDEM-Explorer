import pytest
from shapely.geometry import box
from app import processing

def test_total_tile_budget(monkeypatch):
    monkeypatch.setenv("MAX_TOTAL_TILE_REQUESTS","2")
    monkeypatch.setenv("MAX_TILES_PER_DATASET","10")
    with pytest.raises(ValueError, match="tiles across datasets"):
        processing.create_job("no-job-created",box(88.9,23.9,89.1,24.1),["COP30"])

def test_busy_free_worker(monkeypatch):
    monkeypatch.setenv("MAX_TOTAL_TILE_REQUESTS","8")
    monkeypatch.setenv("MAX_ACTIVE_JOBS","1")
    monkeypatch.setattr(processing,"JOBS",{"busy":{"status":"running"}})
    with pytest.raises(ValueError,match="worker is busy"):
        processing.create_job("test-busy",box(88,23,88.01,23.01),["COP30"])

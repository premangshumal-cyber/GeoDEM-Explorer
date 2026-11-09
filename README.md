# GeoDEM Explorer

Interactive DEM download, tile mosaic, polygon clipping and GeoTIFF export for five global elevation products: Copernicus GLO-30 (COP30), ALOS AW3D30 (AW3D30), NASA SRTM GL1 (SRTMGL1), NASADEM, and Copernicus GLO-90 (COP90).

## Run on Windows

1. Clone this repository using Git, then open **Anaconda Prompt** inside it.
2. Run: conda env create -f environment.yml
3. Run: conda activate geodem-explorer
4. Set the server-only key in Anaconda Prompt: set OPENTOPOGRAPHY_API_KEY=YOUR_PERSONAL_KEY
5. Start: python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
6. Visit http://127.0.0.1:8000 or API docs http://127.0.0.1:8000/docs

Do not put a personal API key in GitHub source, JavaScript, or a public web page. It must be in the server environment. The GitHub repository is code storage, not a running server. To deploy publicly, first obtain an approved OpenTopography integration/enterprise arrangement and add authentication, quotas, persistent jobs, object storage and cleanup.

## Usage

Draw a polygon or rectangle on the interactive Leaflet map, or upload GeoJSON or a ZIP of one shapefile (.shp, .shx, .dbf, .prj). Select any combination of the five DEMs. Click Process. The server queries OpenTopography for intersecting geographic tile subsets, builds a VRT mosaic using gdalbuildvrt, clips to the exact boundary using gdalwarp, and provides individual compressed GeoTIFF files plus a ZIP and metadata. Very small areas are cropped, and multi-tile areas are merged. Source resolution is preserved, not artificially increased. Dataset latitude coverage and voids vary.

### Configuration
Copy .env.example for reference. The app reads environment variables (it does not auto-read .env):
- OPENTOPOGRAPHY_API_KEY: private server key (required for jobs)
- DATA_DIR: output folder (default ./data)
- MAX_UPLOAD_MB: 25
- MAX_TILES_PER_DATASET: 64
- MAX_AREA_KM2: 300000
- JOB_WORKERS: 2
- REQUEST_TIMEOUT_SECONDS: 240

Run tests: python -m pytest -q. GitHub Actions tests do not use your key.

### Limitations / safety
This version is for **trusted personal/local use**, not unauthenticated public hosting. Jobs are in-memory, output files remain on disk until deleted, and the current implementation does not support antimeridian-crossing AOIs. Maximum area/tile settings are safety/quotas controls; country-scale work may require a cloud worker, enterprise data provider approval and greater storage. Both 30 m and 90 m denote approximate nominal product resolution. Copernicus and ALOS are digital surface models, not necessarily bare-earth DTMs. The provider may reject individual requests because of coverage, quota or entitlement.

### API
GET /api/health, GET /api/config, POST /api/aoi/upload, POST /api/jobs, GET /api/jobs/{id}, GET /api/jobs/{id}/download/{filename}

Provider: https://opentopography.org/developers/
Terms: https://opentopography.org/usageterms

Attribution: This work is based on API services provided by the OpenTopography Facility with support from the National Science Foundation under NSF Award Numbers 2410799, 2410800 & 2410801.

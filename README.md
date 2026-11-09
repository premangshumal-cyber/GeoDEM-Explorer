# GeoDEM Explorer

Interactive DEM download, tile mosaic, polygon clipping and GeoTIFF export for five global elevation products: Copernicus GLO-30 (COP30), ALOS AW3D30 (AW3D30), NASA SRTM GL1 (SRTMGL1), NASADEM, and Copernicus GLO-90 (COP90).

## Run on Windows

1. Clone this repository using Git, then open **Anaconda Prompt** inside it.
2. Run: conda env create -f environment.yml
3. Run: conda activate geodem-explorer
4. Set the server-only key in Anaconda Prompt: set OPENTOPOGRAPHY_API_KEY=YOUR_ROTATED_PERSONAL_KEY
5. Set a separate private processing access code: set GEODEM_ACCESS_TOKEN=YOUR_OWN_LONG_RANDOM_ACCESS_CODE
6. Start: python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
7. Visit http://127.0.0.1:8000 or API docs http://127.0.0.1:8000/docs

At the website, enter your processing access code in the private code field and connect to the local backend. **The code must differ from the OpenTopography provider key.**

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


## Docker / Docker Compose

This optional container workflow needs Docker Desktop. Make a local \`.env\` file by copying \`.env.example\`, and replace the placeholder with **your own key** (do not commit \`.env\`):

    docker compose up --build

Then browse to http://127.0.0.1:8000 . Compose binds the app to localhost for safer personal use and saves generated files to the local data folder. For a server deployment, configure OPENTOPOGRAPHY_API_KEY in the hosting provider's **private environment variables**; GitHub Actions secrets alone do not inject it into an independently hosted app. **Do not publish the current unauthenticated server to the Internet.**

Latest checked CI builds are available in the GitHub Actions tab.

## Public Vercel website + separate GDAL server

The website at https://geodem-explorer.vercel.app/ now uses **no-key OpenStreetMap map tiles**, not the CARTO basemap. It also has a backend address field, a private processing access-code field, CORS handling and a server-readiness check. A background DEM job can be submitted once the **separate Docker GDAL backend is deployed**. The Vercel frontend alone cannot run large GDAL mosaics. See [DEPLOY_BACKEND.md](DEPLOY_BACKEND.md) for Docker and paid persistent Render configuration. The backend is not automatically hosted by the Vercel frontend. Set `GEODEM_BACKEND_URL` as a Vercel environment variable to prefill its publicly accessible HTTPS address; **never** set the OpenTopography key or access code on the frontend.

OpenStreetMap standard raster tiles are community-run and intended for normal interactive map viewing only. Respect https://operations.osmfoundation.org/policies/tiles/ .

# External GDAL processing service

The [Vercel website](https://geodem-explorer.vercel.app/) is a static user interface. Its code is in `public/`. DEM processing lives in the **separate Python FastAPI + GDAL backend** in `app/`. It runs as a continuously available Docker service and must have adequate scratch disk space for elevation tiles.

## Architecture

Browser (Vercel, free OpenStreetMap base map)
 -> HTTPS requests to GDAL service
 -> FastAPI validates AOI, bounds, selected DEMs, per-job access code
 -> OpenTopography Global DEM API (private key only on server)
 -> GDAL VRT mosaicking + cutline crop + compressed GeoTIFFs
 -> individual TIFF or ZIP downloads.

The public website uses **no map key**; this is separate from OpenTopography's required **elevation download API key**. Keep both the provider key and processing access code on the backend only.

## Docker setup

Use Docker Desktop locally or a Docker hosting service such as Railway, Render, Fly.io or a VM. The repository's `Dockerfile` creates an image with GDAL, Rasterio and FastAPI. On a host, configure:

- `OPENTOPOGRAPHY_API_KEY`: rotate the key shared in chat and use the new private key
- `GEODEM_ACCESS_TOKEN`: a separate, long, unpredictable secret that you type into the site's processing access-code field; **never reuse the provider key**
- `GEODEM_CORS_ORIGINS`: `https://geodem-explorer.vercel.app` (include other intended frontends only)
- `DATA_DIR`: a writable persistent directory, e.g. `/app/data`
- `MAX_AREA_KM2`: max geodesic area for a request, default 300000
- `MAX_TILES_PER_DATASET`: max number of intersecting 1° tile subsets, default 64
- `JOB_WORKERS`: recommend 1 on small compute plans
- `PORT`: platform-provided port, Docker defaults to 8000.

Launch locally with a private `.env` (ignored by Git), for example:

```sh
docker compose up --build
```

Visit `http://localhost:8000/api/health` and `http://localhost:8000/api/config`. The first should report `{"status":"ok"}`, the second should report `key_configured:true` when a valid-looking key is configured (it does **not** test entitlement or the provider).

## Deploy on Render

A `render.yaml` blueprint is provided for a Docker web service with a persistent disk. **It uses a paid instance/storage configuration**, not an unconditional free tier. Connect this GitHub repo in Render, review costs and settings before accepting, then supply the private variables there. The initial build may be sizable because Conda installs GDAL.

Once Render shows the service as live:
1. Copy its HTTPS `*.onrender.com` URL.
2. Enter it in **GDAL processing server** on the Vercel website and click **Connect**.
3. Enter your private `GEODEM_ACCESS_TOKEN` into **Private processing access code**.
4. Draw a reasonably small polygon and select COP90 for a first test. Click **Process elevation data**.
5. Observe progress. Download the final ZIP or GeoTIFF.

Alternatively, set the public backend *address only* as `GEODEM_BACKEND_URL` in **Vercel → GeoDEM Explorer → Settings → Environment Variables** and redeploy. The backend URL is not secret. This makes the Connect field populate automatically. Do **not** place either secret in Vercel's frontend variables.

## Current limitations

This is a **single-process, bounded research prototype**. The job registry is in memory and is lost on restart; output GeoTIFFs persist only while the attached backend storage persists. A container restart interrupts running downloads and users need to submit a new job. Jobs are not multi-node coordinated. Individual downloads are accessible via unpredictable job IDs (treat job URLs as private). File cleanup/retention limits, strong user accounts, billing controls, malware checks, durable queue, object storage, and automated retries remain necessary before opening the backend to arbitrary public users.

Do **not** put `GEODEM_ACCESS_TOKEN` or `OPENTOPOGRAPHY_API_KEY` in source code, HTML, public JavaScript, a browser URL, screenshots or public logs. The site asks for the access code at runtime and holds it in browser memory only.

OpenStreetMap tile hosting is community funded and intended for interactive map viewing; see https://operations.osmfoundation.org/policies/tiles/ for acceptable use. No map bulk-preloading is performed.

Large national-scale 30 m DEMs may exceed provider quotas, available disk or the configured per-job limits. The application refuses such requests rather than pretending to finish them.

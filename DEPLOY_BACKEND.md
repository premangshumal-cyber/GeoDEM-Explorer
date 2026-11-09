# GeoDEM Explorer: FREE Render GDAL worker

This repository's `render.yaml` now deploys a **free** Render Docker web service (512 MB memory, 0.1 CPU, no persistent disk). It implements the same five DEM sources but with much smaller limits. The Vercel frontend stays at https://geodem-explorer.vercel.app and continues to use no-key OpenStreetMap tiles.

## Activate on Render

1. In Render Dashboard, open **GeoDEM GDAL Backend** Blueprint and approve the planned free `geodem-gdal-backend` service.
2. Set `OPENTOPOGRAPHY_API_KEY` privately in the Render environment. **Rotate the key previously pasted in chat first.** Never put it in GitHub or Vercel frontend code.
3. The Blueprint creates a random `GEODEM_ACCESS_TOKEN`. Retrieve it from the service's private Environment settings and enter it into the web site's **Private processing access code** field. This is NOT the provider API key.
4. Wait for Render's build to become Live, and check `https://<service>.onrender.com/api/health`.
5. In Vercel project settings, set the non-secret `GEODEM_BACKEND_URL` to the Render HTTPS origin and redeploy, or paste the URL into the site's GDAL processing server field and press Connect.
6. Test **one small polygon (under 100 km²)** and **one DEM**, preferably COP90. If successful, try other datasets and download a GeoTIFF or ZIP.

## Free-tier constraints

- Maximum AOI area: **100 km²** (geodesic area; geographic span also matters).
- At most **4 intersecting 1° subsets per dataset** and **8 tile requests across all products** per job.
- Maximum single fetched tile: 64 MiB.
- One processing job at a time; one GDAL thread; limited RAM footprint.
- Files are temporary and may disappear on service sleep/restart/redeploy; download immediately.
- Render free services sleep after 15 minutes of idle and take time to wake; initial connection check may take over one minute.
- This is a **personal testing tool**, not a public multi-user service. Requests still consume your own OpenTopography provider quota; do not share the processing access token.
- There is no free persistent disk or durable job queue. Very large country/state AOIs are intentionally rejected.

## Architecture

Vercel frontend → private-code-gated HTTPS FastAPI on Render → OpenTopography API → GDAL mosaic → polygon clip → GeoTIFF/ZIP.

The five dataset IDs are COP30, AW3D30, SRTMGL1, NASADEM and COP90. Coverage and data availability differ; not every source has valid elevations everywhere. The map background itself needs no API key.

## For larger jobs later

Move the existing Docker backend to a paid persistent worker with more memory/storage, a shared queue and object storage. Do not remove limits on Render's free 512-MB container.

Sources:
- https://render.com/docs/free
- https://render.com/docs/compute-plans
- https://render.com/docs/blueprint-spec

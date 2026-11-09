# Vercel deployment

The `public/` directory contains a **static, browser-only frontend** for Vercel. It supports maps, drawing polygons, GeoJSON and ZIP shapefile input (using browser-side libraries), and previewing the five datasets. It **does not run the FastAPI/GDAL backend**. The processing button is intentionally disabled with an explanatory message to avoid misleading visitors. The backend in `app/` must run on a separate persistent server/container with GDAL, storage and user authentication before live DEM downloads can be offered.

The `vercel.json` file sets `outputDirectory` to `public`. Link this repository to a Vercel project and deploy `main`. No OpenTopography key should be configured on the public frontend. Never expose a personal API key to visitors.

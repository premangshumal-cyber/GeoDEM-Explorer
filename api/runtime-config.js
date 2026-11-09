// Server-side Vercel function: only exposes the public URL of an external GDAL processor.
// The private OpenTopography key and GEODEM_ACCESS_TOKEN must never be sent here.
export default function handler(_req, res) {
  const raw = (process.env.GEODEM_BACKEND_URL || '').trim().replace(/\/+$/, '');
  let url = '';
  try {
    const parsed = new URL(raw);
    if (parsed.protocol === 'https:') url = parsed.origin + parsed.pathname.replace(/\/+$/, '');
  } catch (_) { /* intentionally unconfigured */ }
  res.setHeader('Cache-Control', 'no-store');
  res.status(200).json({backend_url: url});
}

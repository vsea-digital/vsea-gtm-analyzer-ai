# vsea-gtm-analyzer-ai

ADK-powered GTM analyzer backend for VentureSea. Replaces the Gemini-via-Cloudflare call embedded in `venturesea-gtm-analyzer-v7.html` with a proper service.

## Two analysis modes

| Mode | Endpoint | Input | Grounding |
|------|----------|-------|-----------|
| Pitch-deck | `POST /api/v1/analyze/document` | `gcs_uri` (from `/upload`), `market`, `industry` | Structured JSON output (`response_schema`) |
| Website research | `POST /api/v1/analyze/url` | `url`, `market`, `industry` | `google_search` tool |

Both return the same `GTMBrief` JSON schema (identical shape to the one the existing HTML renderer expects).

## Endpoints

```
POST /api/v1/upload              multipart file → GCS → { request_id, gcs_uri, ... }
POST /api/v1/analyze/document    { gcs_uri, market, industry } → GTMBrief
POST /api/v1/analyze/url         { url, market, industry }     → GTMBrief
GET  /api/v1/health              liveness
```

All `/api/v1/*` endpoints require `X-API-Key: $SERVICE_API_KEY`.

## Local setup

```bash
cd vsea-gtm-analyzer-ai
cp .env.example .env                      # edit values if needed
cp ../vsea_ats/advisia-digital-gcp.json secrets/gcp-sa.json
uv sync
uv run uvicorn main:app --reload --port 8003
```

### Create the GCS bucket (one-time)

```bash
gsutil mb -l asia-southeast1 gs://vsea-gtm-uploads

# Auto-delete everything under gtm-uploads/ after 1 day (safety net for
# uploads whose analyze call didn't run).
cat > /tmp/lifecycle.json <<'EOF'
{
  "lifecycle": {
    "rule": [
      { "action": {"type": "Delete"},
        "condition": {"age": 1, "matchesPrefix": ["gtm-uploads/"]} }
    ]
  }
}
EOF
gsutil lifecycle set /tmp/lifecycle.json gs://vsea-gtm-uploads
```

## Quick smoke test

```bash
# 1. upload
curl -s -X POST http://localhost:8003/api/v1/upload \
  -H "X-API-Key: vsea-gtm-dev-key" \
  -F file=@tests/fixtures/sample.pdf
# → { "gcs_uri": "gs://.../pitch.pdf", ... }

# 2. analyze document
curl -s -X POST http://localhost:8003/api/v1/analyze/document \
  -H "X-API-Key: vsea-gtm-dev-key" \
  -H "Content-Type: application/json" \
  -d '{"gcs_uri":"gs://.../pitch.pdf","market":"Indonesia","industry":"Fintech"}'

# 3. analyze url
curl -s -X POST http://localhost:8003/api/v1/analyze/url \
  -H "X-API-Key: vsea-gtm-dev-key" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://gojek.com","market":"Indonesia","industry":"Fintech"}'
```

## Tests

```bash
uv run pytest tests -v
```

## Docker

```bash
docker compose build
docker compose up
```

The SA file at `./secrets/gcp-sa.json` is mounted read-only into the container at `/secrets/gcp-sa.json` and `GOOGLE_APPLICATION_CREDENTIALS` is set accordingly.

## Frontend integration — retain the existing HTML flow

Goal: keep `venturesea-gtm-analyzer-v7.html`'s UX (upload tab, URL tab, market/industry dropdowns, loading steps, `renderReport`) exactly as-is. Only the two functions that talk to Gemini change — `callGeminiWithURL` and `callGeminiWithFile`. Their signatures and return value (the parsed `GTMBrief` object) stay the same, so `startAnalysis()` (HTML line ~754) keeps working untouched.

### What changes in the HTML

**1. Point CONFIG at the new backend.** Replace lines 578–585:

```js
const CONFIG = {
  API_BASE: "http://localhost:8003/api/v1",       // or your deployed host
  API_KEY: "vsea-gtm-dev-key",                    // matches SERVICE_API_KEY on the backend
  FORMSPREE_ENDPOINT: "https://formspree.io/f/xyknvzqr",
  ADMIN_PASSWORD: "venturesea2025"
};
```

`MODEL` / `MAX_TOKENS` move server-side — delete them.

**2. Replace `callGeminiWithURL` (lines 793–814) with:**

```js
async function callGeminiWithURL(url, market, industry) {
  const response = await fetch(`${CONFIG.API_BASE}/analyze/url`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': CONFIG.API_KEY
    },
    body: JSON.stringify({ url, market, industry })
  });
  return await handleResponse(response);
}
```

**3. Replace `callGeminiWithFile` (lines 816–842) with a two-step upload-then-analyze:**

```js
async function callGeminiWithFile(base64, isPDF, market, industry, fileName) {
  // Step 1: upload the raw file via multipart (base64 no longer needed — see note below)
  const gcsUri = await uploadFile(uploadedFile);
  // Step 2: analyze
  const response = await fetch(`${CONFIG.API_BASE}/analyze/document`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': CONFIG.API_KEY
    },
    body: JSON.stringify({ gcs_uri: gcsUri, market, industry })
  });
  return await handleResponse(response);
}

async function uploadFile(file) {
  const fd = new FormData();
  fd.append('file', file, file.name);
  const resp = await fetch(`${CONFIG.API_BASE}/upload`, {
    method: 'POST',
    headers: { 'X-API-Key': CONFIG.API_KEY },   // no Content-Type — browser sets the boundary
    body: fd
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    throw new Error(err.detail || `Upload failed (${resp.status})`);
  }
  const { gcs_uri } = await resp.json();
  return gcs_uri;
}
```

**4. Simplify `handleResponse` (lines 844–851):** the backend already returns a parsed `GTMBrief`, so the function just needs to surface errors and return JSON:

```js
async function handleResponse(response) {
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    if (response.status === 401) throw new Error('Missing or invalid API key.');
    if (response.status === 413) throw new Error('File too large (50MB max).');
    if (response.status === 415) throw new Error('Unsupported file type. Use PDF or PPTX.');
    if (response.status === 429) throw new Error('Rate limit reached. Please wait a moment.');
    throw new Error(err.detail || `Error ${response.status}`);
  }
  return await response.json();
}
```

**5. Delete these — no longer used on the frontend:**
- `fileToBase64` (lines 784–791) — multipart upload replaces base64.
- `buildPrompt` (lines 872–881) — now server-side in `src/agents/gtm_agent/prompts.py`.
- `parseGeminiResponse` (lines 853–870) — now server-side in `src/services/agent_runner.py`.

Everything else — `renderReport`, the tab switcher, the market/industry dropdowns, the loading-step animation — is unchanged.

### CORS

In dev, the backend defaults to `CORS_ORIGINS=*`, which covers local file:// and any localhost port. In prod, set `CORS_ORIGINS` to the exact frontend origin (e.g. `CORS_ORIGINS=https://gtm.venturesea.com`) — multiple comma-separated values allowed.

### API key handling (important)

The `X-API-Key` is embedded in the HTML, so it is **not a secret from the user's browser**. It's a cheap defense against drive-by traffic, not auth. Two options for production:

1. **Keep the simple model (current plan)**: embed `SERVICE_API_KEY` in the HTML. Rotate if abused. Add rate-limiting (IP-based or Cloudflare WAF) in front of the service.
2. **Restore a proxy layer**: keep the existing Cloudflare Worker but point it at this backend instead of Gemini directly. The Worker adds `X-API-Key` server-side; the browser talks only to the Worker. Best if you care about hiding the key.

We recommend option 2 before any public launch. For internal/link-gated use, option 1 is fine.

### Quick verification

After editing the HTML, open it in a browser:

1. Upload tab → pick a PDF → market + industry → **Analyze**. Network tab should show `POST /upload` (200) then `POST /analyze/document` (200). `renderReport` runs against the response and the report appears.
2. URL tab → paste a website → **Analyze**. Network tab should show `POST /analyze/url` (200).
3. If you see `401`, the `X-API-Key` doesn't match `SERVICE_API_KEY` in `.env`.
4. If you see a CORS error, set `CORS_ORIGINS` to your page's origin in `.env` and restart the server.

## Notes

- **Model**: `gemini-3-flash-preview` (configurable in `src/configs/config.toml`). If the model name changes at deploy time, update the toml.
- **Legacy `.ppt` files** are rejected with HTTP 415 — users should re-save as `.pptx`. PPTX slides are parsed via `python-pptx` and sent to Gemini as interleaved text + image Parts.
- **PDFs** go inline (≤50 MB) with mime `application/pdf` — Gemini reads them natively.
- **URL mode** uses ADK's built-in `google_search` tool. Gemini disallows `tools` + `response_schema` together, so URL mode relies on the prompt-embedded JSON structure and the `parse_gtm_json()` fallback parser.
- **Frontend compatibility**: response shape is identical to what `renderReport()` in `venturesea-gtm-analyzer-v7.html` expects. Drop-in replacement for the current Cloudflare proxy, modulo adding the `X-API-Key` header.

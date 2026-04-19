# vsea-gtm-analyzer-ai

ADK-powered GTM analyzer backend for VentureSea. Replaces the Gemini-via-Cloudflare call embedded in `venturesea-gtm-analyzer-v7.html` with a proper service.

## Two analysis modes

| Mode | Endpoint | Input | Grounding |
|------|----------|-------|-----------|
| Pitch-deck | `POST /api/v1/analyze/document` | `gcs_uri` (from `/upload`), `market`, `industry` | Structured JSON output (`response_schema`) |
| Website research | `POST /api/v1/analyze/url` | `url`, `market`, `industry` | `google_search` tool |

Both return the same `GTMBrief` JSON schema (identical shape to the one the existing HTML renderer expects).

## API reference

Base URL (prod): `https://gtm-api.venturesea.tech/api/v1`

All endpoints except `/health` require header `X-API-Key: <SERVICE_API_KEY>`. Interactive docs are served at `/docs` (Swagger) and `/redoc`.

---

### `GET /health`

Liveness probe. No auth.

```bash
curl https://gtm-api.venturesea.tech/api/v1/health
```

**200 →**
```json
{
  "status": "ok",
  "service": "vsea-gtm-analyzer-ai",
  "version": "0.1.0",
  "model": "gemini-3-flash-preview"
}
```

---

### `POST /upload`

Stage a pitch deck in GCS. Returns a `gcs_uri` to pass to `/analyze/document`.

- **Auth**: `X-API-Key` required
- **Content-Type**: `multipart/form-data`
- **Body field**: `file` — the PDF or PPTX binary
- **Limits**: 50 MB; `.pdf` and `.pptx` only (legacy `.ppt` rejected — re-save as `.pptx`)

```bash
curl -X POST https://gtm-api.venturesea.tech/api/v1/upload \
  -H "X-API-Key: $KEY" \
  -F file=@pitch.pdf
```

**200 →**
```json
{
  "request_id": "c1f4a9...",
  "gcs_uri": "gs://vsea-gtm-uploads/gtm-uploads/c1f4a9.../pitch.pdf",
  "filename": "pitch.pdf",
  "mime_type": "application/pdf",
  "size_bytes": 4521933
}
```

**Error codes:** `400` empty file · `401` bad/missing key · `413` over 50 MB · `415` unsupported extension · `502` GCS error.

---

### `POST /analyze/document`

Analyze a previously-uploaded deck. Runs the document agent, returns the `GTMBrief`, then best-effort deletes the GCS object.

- **Auth**: `X-API-Key` required
- **Content-Type**: `application/json`

**Request body**
| Field | Type | Notes |
|---|---|---|
| `gcs_uri` | string | From `/upload` |
| `market` | string | e.g. `"Singapore"`, `"Indonesia"` |
| `industry` | string | free-form, e.g. `"Fintech"` |

```bash
curl -X POST https://gtm-api.venturesea.tech/api/v1/analyze/document \
  -H "X-API-Key: $KEY" \
  -H "Content-Type: application/json" \
  -d '{"gcs_uri":"gs://...","market":"Singapore","industry":"Fintech"}'
```

**200 →** `GTMBrief` (see schema below). Typical latency: 15–25s.

**Error codes:** `400` malformed URI · `401` bad key · `415` unsupported blob · `422` schema validation failed · `502` GCS or Gemini failure.

---

### `POST /analyze/url`

Analyze a company from its website. Uses ADK's `google_search` tool for grounding — Gemini actively browses the site and SERP.

- **Auth**: `X-API-Key` required
- **Content-Type**: `application/json`

**Request body**
| Field | Type | Notes |
|---|---|---|
| `url` | string | must be a valid HTTP(S) URL |
| `market` | string | |
| `industry` | string | |

```bash
curl -X POST https://gtm-api.venturesea.tech/api/v1/analyze/url \
  -H "X-API-Key: $KEY" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://gojek.com","market":"Indonesia","industry":"Fintech"}'
```

**200 →** `GTMBrief`. Typical latency: 10–20s.

**Error codes:** `401` bad key · `422` malformed URL · `502` Gemini/grounding failure.

---

### `GTMBrief` response schema

Identical shape to what the current HTML renderer (`renderReport()`) consumes — drop-in compatible.

```jsonc
{
  "companyName": "string",                              // always present
  "product": "string",                                  // always present
  "gtmScore": 0,                                        // 0-100
  "verdict": "Go" | "Proceed with Caution" | "Hold",    // score-driven: >=60 Go, 30-59 Caution, <30 Hold
  "verdictReason": "string",
  "summary": "string",
  "scoreBreakdown": [                                   // always 6 dimensions, in this order
    { "dimension": "Market Opportunity",        "score": 0, "max": 25, "note": "" },
    { "dimension": "Competitive Landscape",     "score": 0, "max": 20, "note": "" },
    { "dimension": "Regulatory Feasibility",    "score": 0, "max": 20, "note": "" },
    { "dimension": "Product-Market Fit",        "score": 0, "max": 20, "note": "" },
    { "dimension": "GTM Execution Feasibility", "score": 0, "max": 15, "note": "" },
    { "dimension": "Macro & Timing",            "score": 0, "max": 10, "note": "" }
  ],
  "marketOpportunity": {
    "headline": "string",
    "narrative": "string",
    "keyStats": [ { "label": "string", "value": "string" } ]      // 3 items
  },
  "marketSizing": {
    "tam":    { "label": "Total Addressable Market",      "value": "string", "pct": 85, "note": "" },
    "sam":    { "label": "Serviceable Addressable Market","value": "string", "pct": 55, "note": "" },
    "som":    { "label": "Serviceable Obtainable Market", "value": "string", "pct": 22, "note": "" },
    "cagr":   "string",
    "growth": "string"
  },
  "marketAnalysis": {
    "overview": "string",
    "trends": ["string"],    // 4 items
    "risks":  ["string"]     // 3 items
  },
  "opportunities": [ { "title": "string", "desc": "string" } ],    // 3 items
  "competitors": [
    { "rank": 1, "name": "string", "hq": "string", "desc": "string",
      "threat": "High" | "Medium" | "Low", "weakness": "string" }
    // always 3 items
  ],
  "regulatory": [
    { "level": "critical" | "medium" | "low",
      "agency": "string", "title": "string", "desc": "string" }
    // always 5 items
  ],
  "gtmPlan": {
    "phase1": { "timing": "Month 1-3",   "title": "string", "items": ["string"] },   // 4 items each
    "phase2": { "timing": "Month 4-9",   "title": "string", "items": ["string"] },
    "phase3": { "timing": "Month 10-18", "title": "string", "items": ["string"] }
  }
}
```

String fields marked with empty-string defaults (e.g. `note`, `desc`, `weakness`) are guaranteed present but may be `""` if the model omitted them. Structural fields (scores, enums, list counts) are always populated — if Gemini returns malformed structural data, the endpoint 502s instead of returning garbage.

---

### CORS

Preflight allow-list, env-driven (`CORS_ORIGINS` + `CORS_ORIGIN_REGEX`). Default prod config allows:

- `https://www.venturesea.co` and `https://venturesea.co`
- `http://localhost:*` and `http://127.0.0.1:*` (via regex, any port)
- `null` origin (for HTML opened as `file://`)

Any other origin gets `400 Bad Request` on preflight.

---

### Client example (the current `venturesea-gtm-analyzer-v7.html` flow)

```js
const API_BASE = "https://gtm-api.venturesea.tech/api/v1";
const API_KEY = "<SERVICE_API_KEY>";   // stored in CONFIG, sent in X-API-Key

// URL mode
const brief = await fetch(`${API_BASE}/analyze/url`, {
  method: "POST",
  headers: { "Content-Type": "application/json", "X-API-Key": API_KEY },
  body: JSON.stringify({ url, market, industry })
}).then(r => r.json());

// Document mode — two hops
const fd = new FormData();
fd.append("file", file);
const { gcs_uri } = await fetch(`${API_BASE}/upload`, {
  method: "POST",
  headers: { "X-API-Key": API_KEY },   // no Content-Type; browser sets multipart boundary
  body: fd
}).then(r => r.json());

const brief = await fetch(`${API_BASE}/analyze/document`, {
  method: "POST",
  headers: { "Content-Type": "application/json", "X-API-Key": API_KEY },
  body: JSON.stringify({ gcs_uri, market, industry })
}).then(r => r.json());
```

See `renderReport(brief)` in the HTML — unchanged. The `GTMBrief` shape is identical to the legacy Cloudflare-proxy response.

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

## Production deploy (vsea-hostinger-1)

### One-time VM bootstrap

SSH into `vsea-hostinger-1`, then:

```bash
# 1. Clone
cd ~
git clone https://github.com/vsea-digital/vsea-gtm-analyzer-ai.git
cd vsea-gtm-analyzer-ai

# 2. Populate env/ and secrets/
mkdir -p env secrets
cp env/gtm-analyzer.env.example env/gtm-analyzer.env
$EDITOR env/gtm-analyzer.env                          # fill in GOOGLE_API_KEY, SERVICE_API_KEY, GCS_BUCKET_NAME

# 3. Drop the SA JSON in — reuse from ~/vsea-ats if already present
cp ~/vsea-ats/secrets/vsea-ats-sa-key.json secrets/gcp-sa.json
# (or scp from your machine; the file is not in git)

# 4. First boot (service binds only to 127.0.0.1; NPM reaches it)
sg docker -c 'docker compose -f docker-compose.prod.yml up -d --build'

# 5. Verify host-internal reachability
curl -s http://127.0.0.1:8003/api/v1/health
```

The service listens on `127.0.0.1:8003` only. It is **not** reachable directly from the public internet — nginx-proxy-manager fronts it at `https://gtm-api.venturesea.tech`.

### DNS + NPM one-time setup

1. Add DNS A record `gtm-api.venturesea.tech → <VM public IP>` (wherever `venturesea.tech` is managed).
2. In the existing nginx-proxy-manager UI → **Hosts → Proxy Hosts → Add Proxy Host**:
   - **Domain Names**: `gtm-api.venturesea.tech`
   - **Scheme**: `http`
   - **Forward Hostname / IP**: `127.0.0.1`
   - **Forward Port**: `8003`
   - **Block Common Exploits**: ✓
   - **Cache Assets** / **Websockets Support**: off (we don't need them)
3. **SSL tab**:
   - SSL Certificate: *Request a new SSL Certificate*
   - Force SSL: ✓
   - HTTP/2: ✓
   - Email: your admin email
   - Agree to Let's Encrypt TOS: ✓
4. Save. NPM issues the cert via HTTP-01; takes ~30s.
5. Verify from your laptop:

```bash
curl -s https://gtm-api.venturesea.tech/api/v1/health
```

### Ongoing deploys

GitHub Actions does the rest. Tag a release locally and push:

```bash
git tag v0.1.0 && git push origin v0.1.0
```

CI/CD job `deploy` SSHes to the VM, checks out the tag, rebuilds, recreates the container, and smoke-tests `/health`. Required GitHub secrets (same values as the ATS deploy uses): `VPS_HOST`, `VPS_USER`, `VPS_SSH_KEY`, `VPS_PORT`.

### TLS / load balancer

**Current setup — raw IP + HTTP.** Sufficient for internal testing and for calling from the HTML served over `http://` or opened as `file://`. **Not sufficient for prod**: browsers block HTTP calls from an `https://www.venturesea.co` page (mixed content).

**Upgrade path when we're ready to call this from the production HTML:**

1. Point a subdomain at the VM — e.g. add A record `gtm-api.venturesea.co → <VM-IP>`.
2. Add a proxy host in the existing nginx-proxy-manager (NPM) on the VM:
   - Domain: `gtm-api.venturesea.co`
   - Forward to: `127.0.0.1` : `8003` (same VM, so host network)
   - Enable "Request Let's Encrypt Cert" + "Force SSL" + "HTTP/2"
3. Flip the compose port binding from `0.0.0.0:8003:8003` → `127.0.0.1:8003:8003` (only NPM needs to reach it).
4. Update `CORS_ORIGINS` on the VM env file if the frontend origin changes.
5. Update the frontend `CONFIG.API_BASE` to `https://gtm-api.venturesea.co/api/v1`.

No new load balancer needed — NPM gives us SSL, HTTP/2, and sane default headers; a single VM doesn't need a separate LB. Add one (Cloudflare, or a second VM behind a managed LB) only if/when you hit a scaling ceiling. Gemini latency (~10–20s per call) dominates response time, so a single 4-vCPU container will handle small user counts fine — RAM ceiling is the thing to watch.

## CORS

Two env vars drive the allow-list:

| Var | Purpose | Example |
|---|---|---|
| `CORS_ORIGINS` | Exact-match allow-list, comma-separated | `https://www.venturesea.co,https://venturesea.co` |
| `CORS_ORIGIN_REGEX` | Regex for dynamic dev origins | `^(https?://(localhost\|127\.0\.0\.1)(:\d+)?\|null)$` |

The regex shown above covers: `http://localhost:<any>`, `http://127.0.0.1:<any>`, and `null` (what the browser sends when you open the HTML file directly from disk). Keep both set in prod — the regex never matches a non-dev origin.

If `CORS_ORIGINS=*` and no regex is set, the middleware opens up entirely and disables credentials (Starlette rule). Leave `*` for throwaway dev only.

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

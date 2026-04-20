# vsea-gtm-analyzer-ai

ADK-powered GTM analyzer backend for VentureSea. Drives the `venturesea-gtm-analyzer` frontend. Powered by **Claude Sonnet 4.6** via LiteLlm, with Anthropic's native `web_search` server tool for live URL grounding.

## Two analysis modes

| Mode | Endpoint | Input | Grounding |
|------|----------|-------|-----------|
| Pitch-deck | `POST /api/v1/analyze/document` | `gcs_uri` (from `/upload`), `market`, `industry` | Claude reads the deck inline (PDF or PPTX) |
| Website research | `POST /api/v1/analyze/url` | `url`, `market`, `industry`, plus optional company context | Anthropic native `web_search_20250305` server tool |

Both return the same `GTMBrief` JSON schema (identical shape to what the HTML renderer expects).

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
  "model": "claude-sonnet-4-6"
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

**Error codes:** `400` malformed URI · `401` bad key · `415` unsupported blob · `422` schema validation failed · `502` GCS or Claude failure.

---

### `POST /analyze/url`

Analyze a company from its website. Uses Anthropic's native `web_search_20250305` server tool — Claude runs searches against the open web, cites sources, and returns a final answer in a single API call (server-side agentic loop). Optional context fields (`company_description`, `customers`, `stage`, `business_model`, `gtm_goals`) are threaded into the prompt *only when non-empty*, so the frontend can send them unconditionally.

- **Auth**: `X-API-Key` required
- **Content-Type**: `application/json`

**Request body**
| Field | Type | Required | Notes |
|---|---|---|---|
| `url` | string | ✓ | must be a valid HTTP(S) URL |
| `market` | string | ✓ | e.g. `"Singapore"` |
| `industry` | string | ✓ | e.g. `"Fintech"` |
| `company_description` | string | | "What does your company do?" — frontend treats this as required |
| `customers` | string | | "Who are your primary customers?" |
| `stage` | string | | "Company stage / revenue" (dropdown) |
| `business_model` | string | | "Primary business model" (dropdown) |
| `gtm_goals` | string | | "Any specific GTM challenges or goals?" |

Empty or whitespace-only optional fields are skipped in the prompt.

```bash
curl -X POST https://gtm-api.venturesea.tech/api/v1/analyze/url \
  -H "X-API-Key: $KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://gojek.com",
    "market": "Indonesia",
    "industry": "Fintech",
    "company_description": "Super-app offering ride-hailing, payments, and food delivery",
    "customers": "Urban commuters and SME merchants",
    "stage": "Public",
    "business_model": "Marketplace + fintech",
    "gtm_goals": "Expand Vietnam footprint"
  }'
```

**200 →** `GTMBrief`. Typical latency: 20–60s (web_search adds multiple internal round-trips).

**Error codes:** `401` bad key · `422` malformed URL · `502` Claude / web_search failure (transient 5xx are already retried 3× with backoff).

---

### `GTMBrief` response schema

Matches what the frontend renderer (`renderReport()` in `javascript/gtm-analyzer.js`) consumes. Fields marked *new in v7* are additive — the existing renderer ignores them harmlessly.

```jsonc
{
  "companyName": "string",
  "product": "string",
  "gtmScore": 0,                                        // 0-100
  "structuralBlocker": false,                           // NEW v7 — true when a hard regulatory/structural wall triggers a <=45 score cap
  "blockerExplanation": "string",                       // NEW v7 — empty when structuralBlocker=false
  "verdict": "Strong Go" | "Conditional Go" | "Proceed with Caution" | "No Go",
  // v7 thresholds: 75-100 Strong Go · 55-74 Conditional Go · 35-54 Proceed with Caution · 0-34 No Go
  "verdictReason": "string",
  "summary": "string",
  "scoreBreakdown": [                                   // v7 is 7 dimensions totalling 100 pts
    { "dimension": "Market Size & Tailwind",      "score": 0, "max": 20, "note": "", "blocker": false },
    { "dimension": "Regulatory Feasibility",      "score": 0, "max": 20, "note": "", "blocker": false },
    { "dimension": "Competitive Intensity",       "score": 0, "max": 15, "note": "", "blocker": false },
    { "dimension": "Entry Barrier Realism",       "score": 0, "max": 15, "note": "", "blocker": false },
    { "dimension": "Timing Alignment",            "score": 0, "max": 15, "note": "", "blocker": false },
    { "dimension": "GTM Execution Clarity",       "score": 0, "max": 10, "note": "", "blocker": false },
    { "dimension": "Company-Market Readiness",    "score": 0, "max":  5, "note": "", "blocker": false }
  ],
  "marketOpportunity": {
    "headline": "string",
    "narrative": "string",
    "keyStats": [ { "label": "string", "value": "string" } ]
  },
  "marketSizing": {
    "tam":    { "label": "Total Addressable Market",      "value": "string", "pct": 85.0, "note": "" },
    "sam":    { "label": "Serviceable Addressable Market","value": "string", "pct": 55.0, "note": "" },
    "som":    { "label": "Serviceable Obtainable Market", "value": "string", "pct":  1.5, "note": "" },
    // `pct` is a float (0–100) — Claude legitimately returns fractional SOM shares
    "cagr":   "string",
    "growth": "string"
  },
  "marketAnalysis": {
    "overview": "string",
    "trends": ["string"],
    "risks":  ["string"]
  },
  "opportunities": [ { "title": "string", "desc": "string" } ],
  "competitors": [
    { "rank": 1, "name": "string", "hq": "string", "desc": "string",
      "threat": "High" | "Medium" | "Low", "weakness": "string" }
  ],
  "regulatory": [
    { "level": "critical" | "medium" | "low",
      "agency": "string", "title": "string", "desc": "string",
      "blocker": false }                                // NEW v7
  ],
  "gtmPlan": {
    "phase1": { "timing": "string", "title": "string", "items": ["string"] },
    "phase2": { "timing": "string", "title": "string", "items": ["string"] },
    "phase3": { "timing": "string", "title": "string", "items": ["string"] }
  }
}
```

**Pinned enums** (frontend CSS keys off these — do not broaden):
- `verdict ∈ {"Strong Go", "Conditional Go", "Proceed with Caution", "No Go"}`
- `competitors[i].threat ∈ {"High", "Medium", "Low"}`  → CSS class `threat-High` etc.
- `regulatory[i].level ∈ {"critical", "medium", "low"}`  → CSS class `reg-critical` etc.

Flavour-text fields with empty-string defaults (e.g. `note`, `desc`, `weakness`, `blockerExplanation`) are always present but may be `""`. Structural fields (scores, enums) are always populated — if Claude returns malformed structural data, the endpoint 502s instead of returning garbage.

---

### CORS

Preflight allow-list, env-driven (`CORS_ORIGINS` + `CORS_ORIGIN_REGEX`). Default prod config allows:

- `https://www.venturesea.co` and `https://venturesea.co`
- `http://localhost:*` and `http://127.0.0.1:*` (via regex, any port)
- `null` origin (for HTML opened as `file://`)

Any other origin gets `400 Bad Request` on preflight.

---

### Client example (matches the `venturesea-gtm-analyzer` frontend)

```js
const API_BASE = "https://gtm-api.venturesea.tech/api/v1";
const API_KEY  = "<SERVICE_API_KEY>";   // stored in CONFIG, sent in X-API-Key

// URL mode — the 5 context fields are optional; send "" for any the user didn't fill
const brief = await fetch(`${API_BASE}/analyze/url`, {
  method: "POST",
  headers: { "Content-Type": "application/json", "X-API-Key": API_KEY },
  body: JSON.stringify({
    url, market, industry,
    company_description: companyDesc,
    customers, stage, business_model, gtm_goals,
  })
}).then(r => r.json());

// Document mode — two hops
const fd = new FormData();
fd.append("file", file);
const { gcs_uri } = await fetch(`${API_BASE}/upload`, {
  method: "POST",
  headers: { "X-API-Key": API_KEY },   // no Content-Type; browser sets the multipart boundary
  body: fd
}).then(r => r.json());

const brief = await fetch(`${API_BASE}/analyze/document`, {
  method: "POST",
  headers: { "Content-Type": "application/json", "X-API-Key": API_KEY },
  body: JSON.stringify({ gcs_uri, market, industry })
}).then(r => r.json());
```

`renderReport(brief)` in the frontend consumes this directly.

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
$EDITOR env/gtm-analyzer.env                          # fill in ANTHROPIC_API_KEY, GOOGLE_API_KEY (for ADK), SERVICE_API_KEY, GCS_BUCKET_NAME

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

No new load balancer needed — NPM gives us SSL, HTTP/2, and sane default headers; a single VM doesn't need a separate LB. Add one (Cloudflare, or a second VM behind a managed LB) only if/when you hit a scaling ceiling. Claude latency (doc mode ~15s; URL mode 20–60s because web_search runs multiple internal round-trips) dominates response time, so a single 4-vCPU container handles small user counts fine — RAM ceiling is the thing to watch.

## CORS

Two env vars drive the allow-list:

| Var | Purpose | Example |
|---|---|---|
| `CORS_ORIGINS` | Exact-match allow-list, comma-separated | `https://www.venturesea.co,https://venturesea.co` |
| `CORS_ORIGIN_REGEX` | Regex for dynamic dev origins | `^(https?://(localhost\|127\.0\.0\.1)(:\d+)?\|null)$` |

The regex shown above covers: `http://localhost:<any>`, `http://127.0.0.1:<any>`, and `null` (what the browser sends when you open the HTML file directly from disk). Keep both set in prod — the regex never matches a non-dev origin.

If `CORS_ORIGINS=*` and no regex is set, the middleware opens up entirely and disables credentials (Starlette rule). Leave `*` for throwaway dev only.

## Frontend integration

The frontend lives in `venturesea-gtm-analyzer` (separate repo). It already calls this backend — `javascript/gtm-analyzer.js` sends the URL payload with the 5 context fields and consumes the `GTMBrief` response via `renderReport()`. No migration required.

### API key handling

The `X-API-Key` is embedded in the frontend HTML, so it is **not a secret from the user's browser**. It's a cheap defense against drive-by traffic, not auth. For production consider either (a) rotating `SERVICE_API_KEY` if abused and adding rate-limiting (Cloudflare WAF) in front of the service, or (b) restoring a thin proxy (Worker / edge function) that adds `X-API-Key` server-side so the browser never sees it.

### Quick verification after a deploy

1. `curl https://gtm-api.venturesea.tech/api/v1/health` — expect `"model": "claude-sonnet-4-6"`.
2. From the frontend: URL tab → paste a website + fill the required "What does your company do?" → **Analyze**. Network tab: `POST /analyze/url` → 200 in 20–60s.
3. Pitch-deck tab → upload a PDF/PPTX → **Analyze**. Network tab: `POST /upload` (200) then `POST /analyze/document` (200) in ~15s.
4. `401` → `X-API-Key` doesn't match `SERVICE_API_KEY` in the env file.
5. CORS error → update `CORS_ORIGINS` to the frontend origin and restart.

## Notes

- **Model**: `claude-sonnet-4-6` via LiteLlm, pinned in `src/models/models.py`. Requires `ANTHROPIC_API_KEY` in the environment. `num_retries=3` (tenacity-backed, exponential backoff) is set at the factory so transient 429 / 5xx / timeouts / connection drops retry automatically; 4xx client errors (bad key, grammar-too-large) are not retried.
- **URL mode grounding** uses Anthropic's native server-side `web_search_20250305` tool, injected at the LiteLlm client layer (see `_WebSearchLiteLLMClient` in `src/models/models.py`). ADK's tool pipeline strips unknown items, so we inject inside the `LiteLLMClient.acompletion` override. The wrapper also scrubs Anthropic's server-tool-use markers (ids starting with `srvtoolu_`, tool name `web_search`) from both streaming and non-streaming responses so ADK's aggregator never dispatches them as phantom client-side tool calls.
- **Doc mode** does *not* use `output_schema` — Anthropic rejects the compiled strict JSON grammar for a schema this size. The route validates with `parse_gtm_json()` + `GTMBrief.model_validate()` instead. The prompt's "Return ONLY valid JSON" directive + `ENUM FIELDS — MUST use these exact values` block keep Claude on shape.
- **Legacy `.ppt` files** are rejected with HTTP 415 — users should re-save as `.pptx`. PPTX slides are parsed via `python-pptx` and sent as interleaved text + image Parts; PDFs (≤50 MB) go inline with mime `application/pdf`.
- **Frontend compatibility** (`javascript/gtm-analyzer.js`): response shape matches what `renderReport()` consumes. The v7 additions (`structuralBlocker`, `blockerExplanation`, per-item `blocker`) are purely additive — the renderer ignores them. See the "Pinned enums" note in the `GTMBrief` section above for the three fields that must stay locked in their current Literal shape.

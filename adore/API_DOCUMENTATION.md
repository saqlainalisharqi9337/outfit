# Adore — ML API Documentation

Base URL (local): `http://127.0.0.1:8000`  
OpenAPI UI: `/docs`  
Service version: `1.2.0` (see `ml_service/app/main.py`)

## Authentication

Optional shared secret:

- Set `ADORE_API_KEY` in the ML process environment.
- Clients must send header `X-API-Key: <same value>`.
- If `ADORE_API_KEY` is unset, the API is open (local demo default).

Health probes (`/health/live`, `/health/ready`, `/health`, `/`) never require the key.

## CORS

- `ADORE_CORS_ORIGINS` — comma-separated origins, or `*` (default) for local demos.
- Example: `ADORE_CORS_ORIGINS=http://localhost:*,http://127.0.0.1:*`

## Upload limits

- Max body: **12 MB**
- Max decoded resolution: 40 megapixels; longest side thumbnail-capped at 4096 px
- Oversized uploads → HTTP `413`
- Unreadable images → HTTP `400`

## Endpoints

### `GET /`

```json
{"docs": "/docs", "health": "/health/live", "ready": "/health/ready"}
```

### `GET /health/live`

Liveness (no model load). `{ "ok": true, "status": "alive", "service": "adore-ml", "version": "…" }`

### `GET /health/ready`

Readiness after warmup. `{ "ok": true|false, "status": "ready"|"warming", … }`

### `GET /health`

Full status: classifier map, detector status, dress-upperwear gate, pipeline string.

### `POST /analyze-clothing`

`multipart/form-data` field `file` (image).

Typical response fields:

| Field | Meaning |
|---|---|
| `category` / `subcategory` | Taxonomy labels |
| `confidence` | Lead prediction score |
| `color` / `secondaryColor` | Dominant colours |
| `items[]` | Extra detected garments |
| `detected[]` | Structured detections (bbox, region, label) when available |
| `isolatedProduct` | Close-up product framing |
| `needsHumanReview` | Below confidence threshold or unknown/fallback |
| `latencyMs` / `serviceVersion` | Observability |

### `POST /analyze-skin-tone`

`multipart/form-data` field `file`.

```json
{
  "skinTone": "…",
  "ita": 0.0,
  "usedFallback": false,
  "message": "…"
}
```

### `POST /detect`

Detector-only view for localisation debugging. Returns person box, COCO bag-like objects, proposal regions, and thresholds. **Does not** invent shirt/pants labels — those come from classifiers on `/analyze-clothing`.

## Flutter client

`lib/services/image_analysis_service.dart` posts to `/analyze-clothing` with a 45 s timeout and falls back to on-device heuristics on any failure.

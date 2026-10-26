# Adore — Limitations

## Product

- Checkout is **simulated** — orders are stored in Supabase without real payment.
- Offline “Continue as Ayesha” does not write to Supabase.
- Settings notification toggle is preference-only (no push provider).
- Favorites list is thin (metadata, limited outfit preview).
- Pattern on wardrobe items is user-selected; no automatic fabric-pattern CNN.

## ML / vision

- Pipeline is **classification + Stage A COCO YOLO assist**, not a trained 13-class clothing detector (`DETECTION_LIMITATIONS.md`).
- Fixed region fallbacks assume a roughly centred upright subject when no person box exists.
- Live weak classes historically: **hat**, **heels**, occasional dress/skirt/jacket routing collisions.
- Lowerwear and sneaker behaviour is intentionally frozen behind regression tests.
- Unified `clothing_mobilenetv2.keras` was never required once specialists shipped.
- Stage B Fashionpedia training is **not started**.

## Infrastructure

- Local ML default has open CORS (`*`) unless `ADORE_CORS_ORIGINS` is set.
- API key auth is optional (`ADORE_API_KEY`); unset means open local access.
- No multi-tenant rate limiting beyond upload size/resolution guards.
- Weather depends on Open-Meteo availability.

## Documentation honesty

Do not claim 100% clothing accuracy or “custom YOLO clothing detection” in demos or reports. Prefer the pipeline label in `ML_PIPELINE.md` and `DETECTION_LIMITATIONS.md`.

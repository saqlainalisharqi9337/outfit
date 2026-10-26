# Adore — Project Architecture

**Product:** Smart Cloth Advisor and Outfit Recommender (FYP Group 24)  
**Stack:** Flutter + Provider · Supabase · FastAPI ML · Open-Meteo

## Tier overview

```
Flutter app (lib/)                 FastAPI (ml_service/)              Supabase
─────────────────                  ─────────────────────              ────────
Auth, wardrobe, outfits  ──HTTP──>  /analyze-clothing                 Auth (email/pw)
Shop, calendar, trends             /analyze-skin-tone                 Postgres + RLS
Weather + recommendations          /detect, /health*                  Storage (avatars, wardrobe)
On-device analysis fallback        MobileNet + ResNet + YOLO Stage A  Realtime-ready tables
```

The client degrades gracefully: if the ML service is unreachable, clothing upload still runs `LocalImageAnalysis` and asks the user to confirm category.

## Flutter layout

| Layer | Path | Role |
|---|---|---|
| Screens | `lib/screens/**` | Auth, onboarding, home, wardrobe, outfit, calendar, shop, profile |
| Services | `lib/services/**` | Auth, wardrobe, recommendation, weather, shopping, image analysis, NLP |
| Providers | `lib/providers/**` | Auth, wardrobe, weather, cart, events, recommendations |
| Models | `lib/models/**` | User, wardrobe item, product, detected clothing |
| Config | `lib/config/**` | Supabase URL/key, demo account |
| Assets | `assets/data/**`, `assets/images/adore_logo.jpg` | Seed JSON + brand mark |

Entry: `lib/main.dart` → `lib/app.dart` (`RootGate`: splash → login → onboarding → `AppShell`).

Bottom navigation (`lib/screens/shell/app_shell.dart`): Home, Wardrobe, Outfit, Calendar, Shop, Profile.

## Supabase

Nine core tables (see `supabase/migrations/20260830000000_adore_schema.sql`):

`profiles`, `wardrobe_items`, `events`, `favorites`, `outfit_feedback`, `products`, `trends`, `cart_items`, `orders`.

Additive migrations:

- `body_type` on `profiles`
- `pattern_confidence` / `pattern_source` on `wardrobe_items`

RLS: users own their profile, wardrobe, events, favorites, cart, and orders. Products and trends are readable seed data.

Storage buckets: `avatars`, `wardrobe`.

## ML service

Package: `ml_service/app/`. Version `1.2.0`.

| Module | Role |
|---|---|
| `main.py` | HTTP API, upload guards, warmup, CORS / optional API key |
| `outfit_parser.py` | Full-image analyze + region proposals + merge |
| `clothing_classifier.py` | ImageNet + specialist routing |
| `garment_classifier.py` / `footwear_classifier.py` / `dress_upperwear_gate.py` | PyTorch ResNet specialists |
| `accessory_classifier.py` / `lowerwear_classifier.py` / `silhouette_classifier.py` | MobileNetV2 specialists |
| `object_detector.py` / `region_proposals.py` | Stage A YOLO (COCO person/bags) |
| `color_detection.py` / `skin_tone.py` | Colour + ITA skin tone |
| `config.py` | Environment-driven thresholds |

## Cross-cutting concerns

- **Secrets:** only the Supabase publishable key lives in Flutter (`lib/config/supabase_config.dart`). Never ship the service-role key.
- **ML URL:** `AppConstants.mlServiceUrl()` → `10.0.2.2:8000` on Android emulator, `127.0.0.1:8000` elsewhere; override with `--dart-define=ML_SERVICE_URL=...`.
- **Checkout:** simulated FYP orders only — no payment gateway.
- **Detection honesty:** Stage A is pretrained COCO YOLO assisting classification; it is not a trained 13-class clothing detector (see `DETECTION_LIMITATIONS.md`).

## Related docs

- [ML_PIPELINE.md](ML_PIPELINE.md)
- [API_DOCUMENTATION.md](API_DOCUMENTATION.md)
- [RECOMMENDATION_ENGINE.md](RECOMMENDATION_ENGINE.md)
- [NLP_DOCUMENTATION.md](NLP_DOCUMENTATION.md)
- [DATASET_DOCUMENTATION.md](DATASET_DOCUMENTATION.md)
- [DEPLOYMENT.md](DEPLOYMENT.md)
- [LIMITATIONS.md](LIMITATIONS.md)

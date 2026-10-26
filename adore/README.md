# Adore — Smart Cloth Advisor and Outfit Recommender

Final Year Project, Group 24, University of Azad Jammu & Kashmir Muzaffarabad.

Adore is a Flutter app that answers **“What should this user wear right now?”** using culture, live weather, skin tone, occasion, wardrobe items, and preferences. Backend is **Supabase only** (Auth, Postgres, Storage). There is no Firebase.

## Stack

| Layer | Choice |
| --- | --- |
| App | Flutter / Dart, Material 3, Provider |
| Auth / DB / files | Supabase Auth, Postgres + RLS, Storage |
| Weather | Open-Meteo (no API key) |
| Clothing ML | Fine-tuned MobileNetV2 via `ml_service` (see `ml_service/README.md`). On-device geometry fallback if the API is down |

## Run

```bash
cd adore
flutter pub get
flutter run -d chrome
```

Client config: `lib/config/supabase_config.dart` (publishable key only). Never put the Postgres password or service-role key in Flutter.

## Supabase schema

Run these in the SQL Editor (paste **file contents**, not the path):

1. `supabase/migrations/20260830000000_adore_schema.sql`
2. `supabase/migrations/20260830010000_demo_test_profile.sql` (creates the FYP demo user)

Auth → Email: turn **Confirm email** off for demos. Free-plan email sending is rate-limited; use the demo account instead of registering repeatedly.

### Demo login

- Email: `ayesha@adore.test`
- Password: `AdoreDemo@24`

Complete profile: Ayesha Khan, Pakistani, Muzaffarabad, modest preference, wardrobe + events.

## ML service (optional)

```bash
cd ml_service
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Android emulator URL: `http://10.0.2.2:8000`. Override with `--dart-define=ML_SERVICE_URL=...`.

If the service is not running, clothing upload still estimates dominant color on-device and asks you to confirm category.

## Docs

- [CONTEXT.md](CONTEXT.md) — **master context**: problem, architecture, flow charts, ER diagram (open with `context.cmd`)
- [PROJECT_ARCHITECTURE.md](PROJECT_ARCHITECTURE.md) — tiers and data flow
- [ML_PIPELINE.md](ML_PIPELINE.md) / [API_DOCUMENTATION.md](API_DOCUMENTATION.md)
- [RECOMMENDATION_ENGINE.md](RECOMMENDATION_ENGINE.md) / [NLP_DOCUMENTATION.md](NLP_DOCUMENTATION.md)
- [DATASET_DOCUMENTATION.md](DATASET_DOCUMENTATION.md) / [TESTING_REPORT.md](TESTING_REPORT.md)
- [LIMITATIONS.md](LIMITATIONS.md) / [DEPLOYMENT.md](DEPLOYMENT.md)
- [ANDROID_TEST_REPORT.md](ANDROID_TEST_REPORT.md)

## What is implemented

- Brand logo / launcher icon (`assets/images/adore_logo.jpg`)
- Register / login / logout / forgot-password (Supabase Auth)
- Profile setup: gender, culture, skin tone (photo assist + manual), preferences, country/city
- Wardrobe: camera, gallery, AI/on-device analysis, edit, delete, filters
- Live weather + 3-day forecast, device location or country → city
- Recommendation engine with hard filters, weighted scores, explanations, missing-item shop links
- Home, Outfit, Calendar (event outfits), Trends, Shop, cart, simulated checkout
- Saved outfits, demo orders, settings

Checkout stores an order in Supabase and **does not take real payment**.

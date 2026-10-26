# Adore — Deployment Guide

## Prerequisites

- Flutter SDK (stable) for the client
- Python 3.10+ with `ml_service/.venv`
- Supabase project with migrations from `supabase/migrations/` applied
- Optional: Android Studio / emulator for device builds

## 1. Supabase

1. Create a project and paste the contents of:
   - `supabase/migrations/20260830000000_adore_schema.sql`
   - `supabase/migrations/20260830010000_demo_test_profile.sql`
   - body-type / pattern migrations (or `SETUP_ALL.sql`)
2. Create storage buckets `avatars` and `wardrobe` (public read as designed).
3. Auth → Email: disable “Confirm email” for demos if needed.
4. Put the **publishable** URL/key in `lib/config/supabase_config.dart` only.

Demo login: `ayesha@adore.test` / `AdoreDemo@24` (see `README.md`).

## 2. ML service (local)

```bash
cd ml_service
python -m venv .venv
# Windows:
.\.venv\Scripts\pip install -r requirements.txt
copy .env.example .env
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Health checks:

- `GET http://127.0.0.1:8000/health/live`
- `GET http://127.0.0.1:8000/health/ready`
- `GET http://127.0.0.1:8000/health`

### Environment

See `ml_service/.env.example`. Important:

| Variable | Purpose |
|---|---|
| `ADORE_CORS_ORIGINS` | `*` locally; lock to your web origins in production |
| `ADORE_API_KEY` | Optional; when set, require `X-API-Key` on analyze/detect |

Models must exist under `ml_service/models/` (specialists + optional `yolov8n.pt`). Dataset for retrain lives at `D:\fyp project\dataset` (outside the repo).

## 3. Flutter client

```bash
cd adore
flutter pub get
flutter run -d chrome
# Android emulator with ML on the host:
flutter run -d emulator-5554 --dart-define=ML_SERVICE_URL=http://10.0.2.2:8000
```

If the ML service is down, wardrobe upload still uses on-device colour/heuristics and confirmation dropdowns.

## 4. Production hardening checklist

- [ ] Set `ADORE_CORS_ORIGINS` to real origins (no `*` behind a public URL)
- [ ] Set a strong `ADORE_API_KEY` and configure the Flutter client if you expose ML publicly
- [ ] Terminate TLS (reverse proxy) in front of uvicorn
- [ ] Keep Supabase service-role key off devices
- [ ] Confirm `/health/ready` before routing traffic
- [ ] Do not claim Stage B clothing YOLO unless those weights are trained and shipped

## 5. Related docs

- [PROJECT_ARCHITECTURE.md](PROJECT_ARCHITECTURE.md)
- [API_DOCUMENTATION.md](API_DOCUMENTATION.md)
- [ml_service/LAUNCH_READINESS.md](ml_service/LAUNCH_READINESS.md)
- [ANDROID_TEST_REPORT.md](ANDROID_TEST_REPORT.md)

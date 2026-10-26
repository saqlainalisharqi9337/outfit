# Android test report — Adore

**Date:** 3 September 2026  
**Build:** `1.0.0+1`  
**Target:** Android (emulator and/or physical device) + Chrome web (logo/icon verification)

## Environment

| Item | Value |
|---|---|
| Flutter | Stable channel (project SDK `^3.10.7`) |
| ML service | `uvicorn app.main:app --host 127.0.0.1 --port 8000` |
| Emulator ML URL | `--dart-define=ML_SERVICE_URL=http://10.0.2.2:8000` |
| Supabase | Project configured via `lib/config/supabase_config.dart` |
| Demo account | `ayesha@adore.test` / `AdoreDemo@24` |

## Launcher / brand

| Check | Result |
|---|---|
| `assets/images/adore_logo.jpg` bundled | Pass |
| Splash / login show `AdoreLogo` | Pass (code wired) |
| `android/.../mipmap-*/ic_launcher.png` replaced | Pass |
| `web/icons/Icon-*.png` + `favicon.png` replaced | Pass |

## Journey checklist

Run with ML service healthy (`GET /health/ready` → `ok: true`).

| # | Step | Expected | Result |
|---|---|---|---|
| 1 | Cold start → splash | Brand logo + “Adore” + tagline | Pass* |
| 2 | Login / Continue as Ayesha | Home shell | Pass* |
| 3 | Profile shows body type | Editable if online | Pass* |
| 4 | Wardrobe → Add photo | Analysis returns category/colour; bbox when detections present | Pass* |
| 5 | Confirm pattern + save | Item appears in wardrobe | Pass* |
| 6 | Outfit / NLP phrase | Recommendations + explanations | Pass* |
| 7 | Calendar event outfit | Event list updates | Pass* |
| 8 | Shop → cart → checkout | Simulated order stored (online) | Pass* |
| 9 | Kill ML service → add clothing | On-device fallback, no crash | Pass* |
| 10 | Location / weather | Open-Meteo card loads or graceful error | Pass* |

\*Automated/code-path verification and prior web sessions. Re-run on a connected emulator before the viva and tick any device-specific notes below.

## Device notes

```
Device: ______________________________
Android version: _____________________
flutter devices output: ______________
Issues found: ________________________
```

## Commands used

```bash
cd ml_service
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000

cd ..
flutter pub get
flutter run -d chrome
# or
flutter run -d emulator-5554 --dart-define=ML_SERVICE_URL=http://10.0.2.2:8000
flutter test
```

## Known limitations on Android

- First analyze can be slow until ML warmup finishes.
- Camera / gallery permissions must be granted.
- Emulator cannot reach `127.0.0.1` on the host — use `10.0.2.2`.
- Hat / heels remain the weakest live classes; user confirmation dropdowns cover mistakes.

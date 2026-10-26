# Adore — Project Context & Documentation

**Title:** Smart Cloth Advisor and Outfit Recommender  
**Institution:** University of Azad Jammu & Kashmir, Muzaffarabad  
**Type:** Final Year Project (Group 24)  
**App:** Flutter (`adore`) · **ML:** FastAPI (`ml_service`) · **Backend:** Supabase  

This file is the **master context** for the project: problem, architecture, flows, data, and diagrams. Detailed specs live in the linked docs at the end.

Open this file from Windows with `context.cmd`.

---

## 1. Problem and goal

People often own clothes but still cannot decide **what to wear right now**. Advice from fashion sites ignores:

- what is **in the user’s wardrobe**
- **live weather**
- **culture** and modest dress
- **gender** (men’s vs women’s garments)
- **skin tone** colour harmony
- **occasion** (office, wedding, university, …)

Adore answers: *What should this user wear, from their own clothes, for this weather, culture, gender, skin tone, and occasion?*

If a slot is missing (for example no jacket on a cold day), the app can suggest a **shop** item — checkout is simulated for the FYP, not a real payment gateway.

---

## 2. System context

```mermaid
flowchart LR
  User[User phone / Chrome]
  App[Adore Flutter app]
  SB[(Supabase Auth + Postgres + Storage)]
  ML[FastAPI ML service :8000]
  WX[Open-Meteo weather]
  Shop[Seeded shop JSON]

  User --> App
  App --> SB
  App --> ML
  App --> WX
  App --> Shop
  ML -.->|classifies photos| App
```

| External system | Role |
|---|---|
| Supabase | Email login, profile, wardrobe photos, events, cart, orders |
| FastAPI `ml_service` | Clothing labels + colours; optional skin-tone assist |
| Open-Meteo | Temperature, condition, forecast (no API key) |
| On-device analysis | Fallback if ML is down (`LocalImageAnalysis`) |

---

## 3. High-level architecture

```mermaid
flowchart TB
  subgraph client [Flutter client]
    UI[Screens + AppShell]
    P[Providers]
    S[Services]
    UI --> P --> S
  end

  subgraph ml [ml_service]
    API[FastAPI /analyze-clothing]
    CL[clothing_classifier + specialist gates]
    OP[outfit_parser merge]
    API --> OP --> CL
  end

  subgraph cloud [Supabase]
    Auth[Auth]
    DB[(Postgres + RLS)]
    ST[Storage avatars / wardrobe]
  end

  S -->|HTTP multipart| API
  S -->|SDK| Auth
  S -->|SDK| DB
  S -->|SDK| ST
  S -->|HTTPS| WX2[Open-Meteo]
```

### Flutter layers

| Layer | Path | Role |
|---|---|---|
| Screens | `lib/screens/` | Login, wardrobe, outfit, shop, calendar, profile |
| Providers | `lib/providers/` | App state (auth, wardrobe, weather, recommendations) |
| Services | `lib/services/` | API calls, recommendation engine, NLP parser |
| Models | `lib/models/` | User, wardrobe item, outfit, product |
| Catalog | `lib/utils/clothing_catalog.dart` | Labels, gender/weather/occasion rules |
| Entry | `lib/main.dart` → `lib/app.dart` | Splash → login → onboarding → `AppShell` |

### Bottom navigation

Home · Wardrobe · **Outfit** · Calendar · Shop · Profile

---

## 4. User journey

```mermaid
flowchart TD
  A[Splash] --> B{Backend ready?}
  B -->|no| C[Backend setup screen]
  B -->|yes| D{Logged in?}
  D -->|no| E[Login / Register]
  D -->|yes| F{Onboarding complete?}
  E --> F
  F -->|no| G[Profile: gender, culture, skin, city]
  F -->|yes| H[App shell]
  G --> H
  H --> I[Add clothes]
  H --> J[Generate outfit]
  H --> K[Calendar events]
  H --> L[Shop / cart]
```

### Typical session

1. User sets **gender, culture, skin tone, location**.
2. User uploads wardrobe photos (camera or gallery).
3. ML (or on-device fallback) suggests category / subcategory / colour; user can confirm.
4. Weather loads for the profile city (or device GPS).
5. User taps **Generate Outfit** (optional NLP line: *“office look for a cold day”*).
6. Engine returns up to **5** ranked outfits with explanations.
7. Missing pieces can link to the in-app shop.

---

## 5. Clothing analysis (ML) flow

```mermaid
flowchart TD
  U[Upload image] --> P[parse_outfit]
  P --> F[classify_clothing full frame]
  F --> G[Specialist gates]
  G --> J[jacket / t-shirt]
  G --> SH[shoes / sneakers / heels / flats]
  G --> H[hat / bag / watch / shirt]
  G --> LW[trousers / skirt / lowerwear]
  P --> C[detect_colors]
  P --> Y[Optional YOLO person/bag boxes]
  Y --> R[Crop regions and classify]
  R --> M[Merge unique items]
  F --> M
  C --> M
  M --> JSON[JSON: category, subcategory, colour, items]
```

Specialists live in `ml_service/app/` (`*_gate.py`, `clothing_classifier.py`). Routing prefers a confident specialist (for example `shoes_gate`) so oxfords are not labelled as heels.

**API (local):** `http://127.0.0.1:8000`

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Model load status |
| POST | `/analyze-clothing` | Wardrobe photo → labels |
| POST | `/analyze-skin-tone` | Face crop → ITA band |

See [API_DOCUMENTATION.md](API_DOCUMENTATION.md) and [ML_PIPELINE.md](ML_PIPELINE.md).

---

## 6. Outfit recommendation flow

```mermaid
flowchart TD
  Start[Generate Outfit] --> In[Profile + wardrobe + weather + occasion]
  In --> NLP{NLP text?}
  NLP -->|yes| Parse[NlpRequestParser keywords]
  NLP -->|no| Band
  Parse --> Band[WeatherBand from temperature]
  Band --> Hard[Hard filters]
  Hard --> G[Drop wrong gender]
  Hard --> W[Drop wrong weather]
  Hard --> O[Drop wrong occasion]
  G --> Split[Split: uppers, outers, lowers, shoes, accessories]
  Split --> Layer{Cold or office?}
  Layer -->|yes| Jacket[Pick matching jacket / coat / blazer]
  Layer -->|no| Combos[Build combinations]
  Jacket --> Combos
  Combos --> Score[Weighted score]
  Score --> Top[Top 5 diverse outfits]
  Top --> UI[Outfit cards + explanations]
```

### Scoring weights (`assets/data/recommendation_weights.json`)

| Factor | Weight | Meaning |
|---|---|---|
| Weather | 0.28 | Temperature / rain fit |
| Culture | 0.18 | Pakistani, Western, modest, … |
| Occasion | 0.14 | Office vs casual vs wedding |
| Colour | 0.14 | Skin tone + colour harmony |
| Preference | 0.09 | Favourite colours / styles |
| Wardrobe | 0.09 | Prefer owned items |
| Body type | 0.08 | Silhouette ranking |

**Gender (hard rule):** men’s outfits never include dresses, heels, blouses, dupattas, fashion handbags, or a generic women’s `bag`. Women’s outfits never include men’s-only items such as neckties. Shared items (shirt, trousers, sneakers, jacket) stay available to both.

**Cold weather:** every look includes a jacket, coat, or blazer chosen to match the shirt, trousers, and shoes.

Entry point: `RecommendationService.recommend()` in `lib/services/recommendation_service.dart`.

---

## 7. Sequence: generate outfit

```mermaid
sequenceDiagram
  actor U as User
  participant OS as OutfitScreen
  participant RP as RecommendationProvider
  participant RS as RecommendationService
  participant WP as WeatherProvider
  participant WD as WardrobeProvider

  U->>OS: Tap Generate / submit NLP
  OS->>WP: current weather
  OS->>WD: wardrobe items
  OS->>RP: generate(user, wardrobe, weather)
  RP->>RS: recommend(...)
  RS->>RS: hard filters + score + layer jacket
  RS-->>RP: RecommendationResult
  RP-->>OS: outfits
  OS-->>U: Best match / alternatives
```

---

## 8. Sequence: add clothing

```mermaid
sequenceDiagram
  actor U as User
  participant Add as Add clothing screen
  participant IA as ImageAnalysisService
  participant ML as FastAPI :8000
  participant SB as Supabase Storage + DB

  U->>Add: Camera or gallery
  Add->>IA: analyze image
  IA->>ML: POST /analyze-clothing
  alt ML down
    IA->>IA: LocalImageAnalysis
  end
  ML-->>Add: category, subcategory, colour
  U->>Add: Confirm / edit
  Add->>SB: upload photo + insert wardrobe_items
```

---

## 9. Data model (Supabase)

```mermaid
erDiagram
  profiles ||--o{ wardrobe_items : owns
  profiles ||--o{ events : plans
  profiles ||--o{ favorites : saves
  profiles ||--o{ outfit_feedback : rates
  profiles ||--o{ cart_items : shops
  profiles ||--o{ orders : places
  products ||--o{ cart_items : referenced

  profiles {
    uuid id PK
    text gender
    text culture
    text skin_tone
    text body_type
    text city
  }
  wardrobe_items {
    uuid id PK
    uuid user_id FK
    text category
    text subcategory
    text color
    text image_url
  }
  events {
    uuid id PK
    uuid user_id FK
    text occasion
    timestamptz starts_at
  }
  products {
    uuid id PK
    text subcategory
    numeric price
  }
```

Schema: `supabase/migrations/20260830000000_adore_schema.sql`.  
Row Level Security: users only see their own wardrobe, events, cart, and orders.

---

## 10. Clothing taxonomy (simplified)

```mermaid
flowchart LR
  subgraph cat [Categories]
    UW[upperwear]
    LW[lowerwear]
    FW[footwear]
    AC[accessories]
    DR[dress]
  end
  UW --> Shirt[shirt t-shirt jacket]
  LW --> Pants[trousers jeans shorts]
  FW --> Shoe[shoes sneakers heels flats]
  AC --> Acc[watch bag hat dupatta]
  DR --> Dress[dress gown]
```

Canonical lists: `ClothingCatalog` in `lib/utils/clothing_catalog.dart`.

---

## 11. ML specialist map (clothing)

```mermaid
flowchart TB
  IMG[Product photo] --> R{Router}
  R --> JG[jacket_gate]
  R --> TG[tshirt_gate]
  R --> SG[shoes_gate]
  R --> SN[sneakers_gate]
  R --> HG[heels_gate]
  R --> FG[flats_gate]
  R --> SH[shirt_gate]
  R --> HT[hat_gate]
  R --> BG[bag_gate]
  R --> TR[trousers_gate]
  JG --> UW[upperwear]
  TG --> UW
  SG --> FO[footwear]
  SN --> FO
  HG --> FO
  FG --> FO
```

Gates are **not** swapped casually: lowerwear and sneaker contracts are covered by regression tests.

---

## 12. Folder map

```
adore/
  lib/                    Flutter app
  assets/data/            products, trends, recommendation weights
  supabase/migrations/    Postgres schema
  ml_service/             FastAPI + Keras/PyTorch models
  test/                   Flutter unit tests
  CONTEXT.md              this file
  context.cmd             Windows opener for this file
```

---

## 13. How to run

**App**

```bat
cd /d "D:\fyp project\adore"
flutter pub get
flutter run -d chrome
```

**ML API** (optional but used for wardrobe AI)

```bat
cd /d "D:\fyp project\adore\ml_service"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

**Demo login:** `ayesha@adore.test` / `AdoreDemo@24` (female Pakistani profile).  
For men’s outfits, set **Profile → Gender → Male**.

---

## 14. Related documentation

| Document | Contents |
|---|---|
| [README.md](README.md) | Setup, demo account, feature list |
| [PROJECT_ARCHITECTURE.md](PROJECT_ARCHITECTURE.md) | Tiers and modules |
| [ML_PIPELINE.md](ML_PIPELINE.md) | Classifiers and routing |
| [API_DOCUMENTATION.md](API_DOCUMENTATION.md) | HTTP endpoints |
| [RECOMMENDATION_ENGINE.md](RECOMMENDATION_ENGINE.md) | Scoring and filters |
| [NLP_DOCUMENTATION.md](NLP_DOCUMENTATION.md) | Keyword outfit requests |
| [DATASET_DOCUMENTATION.md](DATASET_DOCUMENTATION.md) | Training data |
| [TESTING_REPORT.md](TESTING_REPORT.md) | Test evidence |
| [LIMITATIONS.md](LIMITATIONS.md) | Known FYP limits |
| [DEPLOYMENT.md](DEPLOYMENT.md) | Ship notes |
| [DETECTION_LIMITATIONS.md](DETECTION_LIMITATIONS.md) | YOLO is not a 13-class clothing detector |

---

## 15. FYP honesty notes

- Outfit **recommendation is rule-based scoring**, not a generative AI fashion model.
- NLP is a **keyword parser**, not ChatGPT.
- Checkout **does not take real payment**.
- YOLO only helps find person/bag boxes; **garment names come from classifiers**.

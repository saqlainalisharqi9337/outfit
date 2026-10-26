# Adore — Recommendation Engine

Entry point: `RecommendationService.recommend()` in `lib/services/recommendation_service.dart`.

Weights live in `assets/data/recommendation_weights.json` and must sum to **1.00**:

| Component | Weight | Role |
|---|---|---|
| weather | 0.28 | Season / temperature band fit |
| culture | 0.18 | Cultural / modest preference alignment |
| occasion | 0.14 | Event type fit |
| color | 0.14 | Palette harmony with skin tone and items |
| preference | 0.09 | Liked styles / colours |
| wardrobe | 0.09 | Prefer owned items |
| bodyType | 0.08 | Silhouette compatibility |

Extra bonuses (hardcoded, additive): trend (~×0.04) and personalization (~×0.05).

## Pipeline

1. Derive `WeatherBand` + effective season (live temperature can override calendar season).
2. Build preferred / excluded type and style sets from the user profile.
3. **Hard filters** (item dropped if any match):
   - gender mismatch
   - excluded item type / style
   - very cold vs summer-only pieces
   - hot weather vs winter outerwear
   - rain vs sandals-style footwear
4. Partition by `ClothingCategory`, soft-score items, take top-N per category.
5. Combine outfits (cap ~160), score, sort, dedupe, diversify → typically **5** outfits.
6. Attach `List<String>` explanations (including body-type line when set).

## Body type

`BodyType` enum on the profile (onboarding + edit profile).  
`ClothingCatalog.bodyTypeScore` ranks silhouettes; unset body type scores neutrally.

## NLP bridge

`OutfitScreen` can parse a short natural-language request via `NlpRequestParser` and feed occasion / weather / colour / style filters into the same recommender (see `NLP_DOCUMENTATION.md`).

## Shop gap fill

When an outfit is missing a category, recommendation results can surface shop product links from seeded `products` data.

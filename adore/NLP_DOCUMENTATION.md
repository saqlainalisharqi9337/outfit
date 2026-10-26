# Adore — NLP Documentation

Module: `lib/services/nlp_request_parser.dart`  
Tests: `test/nlp_body_pattern_test.dart`

## What it is

A **keyword parser**, not a trained language model. It maps short English phrases to structured outfit filters consumed by `RecommendationService`.

## Output shape (`NlpOutfitRequest`)

| Field | Type | Examples of triggers |
|---|---|---|
| `occasion` | `Occasion?` | wedding, office, university, party, gym, travel, … |
| `weatherBand` | `WeatherBand?` | freezing, cold, hot, mild |
| `rainy` | `bool` | rain, drizzle, wet weather |
| `modest` | `bool?` | modest, covered, hijab-friendly cues |
| `colors` | `List<String>` | black, white, red, blue, … (catalog colours) |
| `style` | `String?` | casual, formal, sporty, … |
| `gender` | `Gender?` | men / women phrasing |

`hasFilters` is true when any structured field is set.

## Example phrases

- `"office outfit for a cold rainy day"`
- `"modest black dress for a wedding"`
- `"casual weekend look in blue"`
- `"gym clothes for hot weather"`
- `"formal event, not too revealing"`

## UI

`lib/screens/outfit/outfit_screen.dart` exposes a text field; parsed filters are applied when requesting recommendations.

## Limits

- English keyword lists only; no synonym expansion beyond the coded lists.
- Ambiguous sentences may leave fields null — the recommender then uses profile + weather defaults.
- Not connected to the ML clothing classifier.

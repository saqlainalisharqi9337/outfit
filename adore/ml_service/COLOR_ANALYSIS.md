# Garment colour analysis

Clothing **type** still comes from the existing detector and specialist
gates. Colour and pattern are a separate stage that runs **after** a
garment box (or crop) exists.

```text
IMAGE
  → clothing detection / classification  (unchanged)
  → individual garment crop or mask
  → colour analysis (this module)
  → pattern analysis (spatial layout of colour clusters)
  → recommendation engine (uses catalog `color` + `secondaryColor`)
```

## Why the old path was replaced

`color_detection.py` named every pixel and took the majority. Bright
flowers, white stripes, and studio backdrops could outrank the true
base colour. The new pipeline ranks clusters by **area**, not brightness.

## Algorithm

1. **Crop** the detector bounding box with a configurable inset
   (`ADORE_COLOR_INSET`, default 6%) so the wall around the garment is
   less likely to leak in.
2. **Isolate pixels** with OpenCV GrabCut (Rother et al., 2004) when the
   crop is large enough. Fallback: CIE Lab distance from the border,
   flood-filled, then kept only in a border rim so interior white stripes
   are not deleted with a white studio wall.
3. **Gray-world** white-balance on foreground pixels only, so sunlight vs
   indoor tungsten is less likely to rename navy as black.
4. **K-Means in CIE Lab** (`sklearn.cluster.MiniBatchKMeans`, numpy
   fallback). Lab is used instead of RGB because lighting shifts RGB
   much more than Lab chroma.
5. **Name** each centroid from a fixed 20-colour palette (nearest Lab
   neighbour). Nearby clusters merge (`ADORE_COLOR_MERGE_LAB`).
6. **Drop** clusters below `ADORE_COLOR_MIN_SHARE` (default 4%) so logos,
   buttons, and stitching do not become the primary colour.
7. **Rank by share:**
   - primary: largest remaining cluster
   - secondary: share ≥ `ADORE_COLOR_SECONDARY_MIN` (12%)
   - accent: share ≥ `ADORE_COLOR_ACCENT_MIN` (6%)
8. **Pattern** from the cluster map: solid, striped, checked, floral,
   printed, gradient, patterned. `isMulticolor` is true when more than
   one meaningful colour remains.

## API

`POST /analyze-clothing` still returns `color` and `secondaryColor` for
the wardrobe and recommender. Additive fields:

- `primaryColor`, `secondaryColors`, `accentColors`
- `colorDistribution` (fractions 0–1)
- `pattern`, `patternType`, `isMulticolor`
- `colorClusters` (rgb / hsv / lab / share)

Each entry in `detected[]` / `detections[]` has the same colour fields,
computed from **that item’s box**, not the full photo.

`POST /debug-colors` returns the same analysis plus PNG panels
(crop → mask → clusters → percentages) as base64.

## Thresholds (environment)

| Variable | Default | Role |
|---|---|---|
| `ADORE_COLOR_MIN_SHARE` | 0.04 | ignore logos / noise |
| `ADORE_COLOR_SECONDARY_MIN` | 0.12 | secondary colour floor |
| `ADORE_COLOR_ACCENT_MIN` | 0.06 | accent colour floor |
| `ADORE_COLOR_SOLID_MIN` | 0.82 | treat as solid |
| `ADORE_COLOR_MERGE_LAB` | 14 | merge similar Lab clusters |
| `ADORE_COLOR_INSET` | 0.06 | box inset against background |
| `ADORE_COLOR_K_MAX` | 6 | max K-Means k |
| `ADORE_COLOR_MAX_SIDE` | 256 | analysis resolution |

## Recommendation mapping

The recommender still reads `WardrobeItem.color`. Extra names are mapped:

`gray→grey`, `dark_red→maroon`, `dark_green→olive`, `light_blue→blue`,
`silver→grey`.

## Tests and report

```text
cd ml_service
.\.venv\Scripts\python.exe -m pytest tests/test_color_analysis.py tests/test_api.py -q
.\.venv\Scripts\python.exe eval_color_analysis.py
```

Debug collages: `ml_service/reports/color_debug/`.

## Limitations

- GrabCut can still leak on a busy patterned wall that looks like fabric.
- Gold embroidery vs yellow is hard under warm indoor light.
- Pattern labels are geometric heuristics, not a trained floral CNN.
- Very sheer / mesh garments mix background into the clusters.
- Local on-device analysis in Flutter is unchanged (ML-down fallback).

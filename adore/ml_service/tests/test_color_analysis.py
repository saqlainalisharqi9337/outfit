from __future__ import annotations

from app.color_analysis import analyze_garment_colors, catalog_color
from color_fixtures import CASES


def _names(analysis) -> set[str]:
    names = {analysis.primary_color, *analysis.secondary_colors, *analysis.accent_colors}
    names.update(analysis.color_distribution)
    return names


def test_solid_black_is_not_the_studio_background():
    case = next(c for c in CASES if c["id"] == "solid_black")
    result = analyze_garment_colors(case["builder"]())
    assert result.primary_color in case["primary"]
    assert result.pattern == "solid"


def test_floral_dress_keeps_black_as_primary_not_bright_red():
    case = next(c for c in CASES if c["id"] == "black_red_white_dress")
    result = analyze_garment_colors(case["builder"]())
    assert result.primary_color in case["primary"]
    found = _names(result)
    assert "red" in found or "dark_red" in found or "maroon" in found
    assert "white" in found or "cream" in found
    assert result.is_multicolor is True


def test_striped_shirt_keeps_blue_and_white():
    case = next(c for c in CASES if c["id"] == "blue_white_striped_shirt")
    result = analyze_garment_colors(case["builder"]())
    assert result.primary_color in case["primary"]
    found = _names(result)
    assert found & {"white", "cream", "silver"}
    assert result.is_multicolor is True


def test_black_gray_trousers_keep_both():
    case = next(c for c in CASES if c["id"] == "black_gray_trousers")
    result = analyze_garment_colors(case["builder"]())
    found = _names(result)
    assert found & {"black"}
    assert found & {"gray", "silver"}
    assert result.primary_color in {"black", "gray"}


def test_red_black_bag_is_not_only_the_brighter_half():
    case = next(c for c in CASES if c["id"] == "red_black_bag")
    result = analyze_garment_colors(case["builder"]())
    found = _names(result)
    assert found & {"red", "dark_red", "maroon"}
    assert found & {"black"}
    assert result.is_multicolor is True


def test_green_gold_traditional_preserves_gold():
    case = next(c for c in CASES if c["id"] == "green_gold_traditional")
    result = analyze_garment_colors(case["builder"]())
    assert result.primary_color in case["primary"]
    found = _names(result)
    assert found & {"gold", "yellow", "beige", "orange"}


def test_blue_wall_does_not_paint_a_black_shirt():
    case = next(c for c in CASES if c["id"] == "black_shirt_blue_wall")
    result = analyze_garment_colors(case["builder"](), bbox=[0.22, 0.12, 0.78, 0.88])
    assert result.primary_color == "black"
    assert result.primary_color not in case["forbidden"]


def test_tiny_yellow_logo_is_not_primary():
    case = next(c for c in CASES if c["id"] == "black_tiny_yellow_logo")
    result = analyze_garment_colors(case["builder"]())
    assert result.primary_color == "black"
    assert result.primary_color not in {"yellow", "gold"}


def test_catalog_mapping_for_recommendation_engine():
    assert catalog_color("gray") == "grey"
    assert catalog_color("dark_red") == "maroon"
    assert catalog_color("black") == "black"


def test_percentages_sum_near_one():
    result = analyze_garment_colors(CASES[1]["builder"]())
    total = sum(result.color_distribution.values())
    assert 0.85 <= total <= 1.05


def test_clothing_class_is_not_inferred_from_colour():
    """Colour module never returns a garment type."""
    result = analyze_garment_colors(CASES[0]["builder"]())
    assert not hasattr(result, "subcategory")
    payload = result.to_api()
    assert "subcategory" not in payload
    assert payload["color"] == catalog_color(result.primary_color)

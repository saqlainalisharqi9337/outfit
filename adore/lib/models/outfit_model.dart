import '../utils/enums.dart';
import 'product_model.dart';
import 'wardrobe_item.dart';

class OutfitSlot {
  const OutfitSlot({
    required this.category,
    this.item,
    this.missingSuggestion,
  });

  final ClothingCategory category;
  final WardrobeItem? item;
  final MissingItemSuggestion? missingSuggestion;

  bool get filledFromWardrobe => item != null;
}

class MissingItemSuggestion {
  const MissingItemSuggestion({
    required this.title,
    required this.reason,
    required this.category,
    required this.subcategory,
    required this.color,
    this.matchedProduct,
  });

  final String title;
  final String reason;
  final ClothingCategory category;
  final String subcategory;
  final String color;
  final ProductModel? matchedProduct;
}

class ScoreBreakdown {
  const ScoreBreakdown({
    required this.weather,
    required this.culture,
    required this.occasion,
    required this.color,
    required this.preference,
    required this.wardrobe,
    this.bodyType = 0.72,
    required this.finalScore,
  });

  final double weather;
  final double culture;
  final double occasion;
  final double color;
  final double preference;
  final double wardrobe;
  final double bodyType;
  final double finalScore;

  int get percent => (finalScore * 100).clamp(0, 100).round();
}

class OutfitRecommendation {
  const OutfitRecommendation({
    required this.id,
    required this.title,
    required this.slots,
    required this.breakdown,
    required this.explanations,
    required this.fromWardrobe,
    this.trendBoost = 0,
  });

  final String id;
  final String title;
  final List<OutfitSlot> slots;
  final ScoreBreakdown breakdown;
  final List<String> explanations;
  final bool fromWardrobe;
  final double trendBoost;

  List<WardrobeItem> get ownedItems =>
      slots.map((s) => s.item).whereType<WardrobeItem>().toList();

  List<MissingItemSuggestion> get missingItems => slots
      .map((s) => s.missingSuggestion)
      .whereType<MissingItemSuggestion>()
      .toList();
}

class RecommendationResult {
  const RecommendationResult({
    required this.outfits,
    required this.occasion,
    required this.generatedAt,
    this.emptyWardrobe = false,
  });

  final List<OutfitRecommendation> outfits;
  final Occasion occasion;
  final DateTime generatedAt;
  final bool emptyWardrobe;
}

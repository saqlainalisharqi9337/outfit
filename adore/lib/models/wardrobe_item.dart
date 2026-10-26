import '../utils/clothing_catalog.dart';
import '../utils/enums.dart';
import '../utils/json_helpers.dart';

class WardrobeItem {
  const WardrobeItem({
    required this.itemId,
    required this.userId,
    required this.imageUrl,
    required this.category,
    required this.subcategory,
    required this.color,
    this.secondaryColor,
    this.pattern = 'solid',
    this.patternSource = 'user',
    this.patternConfidence,
    this.material = 'unknown',
    this.style = 'casual',
    this.seasons = const [],
    this.formality = Formality.casual,
    this.cultureCompatibility = const [],
    this.weatherSuitability = const [],
    this.occasions = const [],
    this.aiConfidence,
    this.createdAt,
  });

  final String itemId;
  final String userId;
  final String imageUrl;
  final ClothingCategory category;
  final String subcategory;
  final String color;
  final String? secondaryColor;
  final String pattern;
  final String patternSource;
  final double? patternConfidence;
  final String material;
  final String style;
  final List<Season> seasons;
  final Formality formality;
  final List<String> cultureCompatibility;
  final List<WeatherBand> weatherSuitability;
  final List<Occasion> occasions;
  final double? aiConfidence;
  final DateTime? createdAt;

  factory WardrobeItem.fromMap(
    String itemId,
    String userId,
    Map<String, dynamic> data,
  ) {
    return WardrobeItem(
      itemId: (pick(data, 'id') as String?) ?? itemId,
      userId: (pick(data, 'user_id', 'userId') as String?) ?? userId,
      imageUrl: pick(data, 'image_url', 'imageUrl') as String? ?? '',
      category: enumFromString(
        ClothingCategory.values,
        pick(data, 'category') as String?,
        ClothingCategory.upperwear,
      ),
      subcategory: pick(data, 'subcategory') as String? ?? 'shirt',
      color: pick(data, 'color') as String? ?? 'black',
      secondaryColor: pick(data, 'secondary_color', 'secondaryColor') as String?,
      pattern: pick(data, 'pattern') as String? ?? 'solid',
      patternSource:
          pick(data, 'pattern_source', 'patternSource') as String? ?? 'user',
      patternConfidence:
          (pick(data, 'pattern_confidence', 'patternConfidence') as num?)
              ?.toDouble(),
      material: pick(data, 'material') as String? ?? 'unknown',
      style: pick(data, 'style') as String? ?? 'casual',
      seasons: stringList(pick(data, 'season', 'seasons'))
          .map((e) => enumFromString(Season.values, e, Season.spring))
          .toList(),
      formality: enumFromString(
        Formality.values,
        pick(data, 'formality') as String?,
        Formality.casual,
      ),
      cultureCompatibility:
          stringList(pick(data, 'culture_compatibility', 'cultureCompatibility')),
      weatherSuitability: stringList(pick(data, 'weather_suitability', 'weatherSuitability'))
          .map((e) => enumFromString(WeatherBand.values, e, WeatherBand.mild))
          .toList(),
      occasions: stringList(pick(data, 'occasion', 'occasions'))
          .map((e) => enumFromString(Occasion.values, e, Occasion.casualDayOut))
          .toList(),
      aiConfidence: (pick(data, 'ai_confidence', 'aiConfidence') as num?)?.toDouble(),
      createdAt: parseDate(pick(data, 'created_at', 'createdAt')),
    );
  }

  Map<String, dynamic> toRow() => {
        'id': itemId,
        'user_id': userId,
        'image_url': imageUrl,
        'category': category.name,
        'subcategory': subcategory,
        'color': color,
        'secondary_color': secondaryColor,
        'pattern': pattern,
        'pattern_source': patternSource,
        'pattern_confidence': patternConfidence,
        'material': material,
        'style': style,
        'season': seasons.map((e) => e.name).toList(),
        'formality': formality.name,
        'culture_compatibility': cultureCompatibility,
        'weather_suitability': weatherSuitability.map((e) => e.name).toList(),
        'occasion': occasions.map((e) => e.name).toList(),
        'ai_confidence': aiConfidence,
      };

  factory WardrobeItem.inferred({
    required String itemId,
    required String userId,
    required String imageUrl,
    required ClothingCategory category,
    required String subcategory,
    required String color,
    String? secondaryColor,
    double? aiConfidence,
    Culture? culture,
  }) {
    return WardrobeItem(
      itemId: itemId,
      userId: userId,
      imageUrl: imageUrl,
      category: category,
      subcategory: subcategory,
      color: color,
      secondaryColor: secondaryColor,
      style: ClothingCatalog.formalityForSubcategory(subcategory).name,
      seasons: ClothingCatalog.seasonsForSubcategory(subcategory),
      formality: ClothingCatalog.formalityForSubcategory(subcategory),
      cultureCompatibility: culture == null ? const [] : [culture.name],
      weatherSuitability:
          ClothingCatalog.weatherBandsForSubcategory(subcategory),
      occasions: ClothingCatalog.occasionsForSubcategory(subcategory),
      aiConfidence: aiConfidence,
      createdAt: DateTime.now(),
    );
  }

  WardrobeItem copyWith({
    String? imageUrl,
    ClothingCategory? category,
    String? subcategory,
    String? color,
    String? secondaryColor,
    String? pattern,
    String? patternSource,
    double? patternConfidence,
    String? material,
    String? style,
    List<Season>? seasons,
    Formality? formality,
    List<String>? cultureCompatibility,
    List<WeatherBand>? weatherSuitability,
    List<Occasion>? occasions,
  }) {
    return WardrobeItem(
      itemId: itemId,
      userId: userId,
      imageUrl: imageUrl ?? this.imageUrl,
      category: category ?? this.category,
      subcategory: subcategory ?? this.subcategory,
      color: color ?? this.color,
      secondaryColor: secondaryColor ?? this.secondaryColor,
      pattern: pattern ?? this.pattern,
      patternSource: patternSource ?? this.patternSource,
      patternConfidence: patternConfidence ?? this.patternConfidence,
      material: material ?? this.material,
      style: style ?? this.style,
      seasons: seasons ?? this.seasons,
      formality: formality ?? this.formality,
      cultureCompatibility: cultureCompatibility ?? this.cultureCompatibility,
      weatherSuitability: weatherSuitability ?? this.weatherSuitability,
      occasions: occasions ?? this.occasions,
      aiConfidence: aiConfidence,
      createdAt: createdAt,
    );
  }
}

import '../utils/clothing_catalog.dart';
import '../utils/enums.dart';
import '../utils/json_helpers.dart';

class ProductModel {
  const ProductModel({
    required this.id,
    required this.name,
    required this.description,
    required this.price,
    required this.imageUrl,
    required this.category,
    required this.subcategory,
    required this.color,
    required this.cultureTags,
    required this.weatherBands,
    this.currency = 'PKR',
    this.style = 'casual',
    this.seasonTags = const [],
  });

  final String id;
  final String name;
  final String description;
  final double price;
  final String imageUrl;
  final ClothingCategory category;
  final String subcategory;
  final String color;
  final List<String> cultureTags;
  final List<String> weatherBands;
  final String currency;
  final String style;
  final List<String> seasonTags;

  factory ProductModel.fromMap(String id, Map<String, dynamic> data) {
    return ProductModel(
      id: (pick(data, 'id') as String?) ?? id,
      name: pick(data, 'name') as String? ?? 'Clothing item',
      description: pick(data, 'description') as String? ?? '',
      price: (pick(data, 'price') as num?)?.toDouble() ?? 0,
      imageUrl: pick(data, 'image_url', 'imageUrl') as String? ?? '',
      category: enumFromString(
        ClothingCategory.values,
        pick(data, 'category') as String?,
        ClothingCategory.upperwear,
      ),
      subcategory: pick(data, 'subcategory') as String? ?? 'shirt',
      color: pick(data, 'color') as String? ?? 'black',
      cultureTags: stringList(pick(data, 'culture_tags', 'cultureTags')),
      weatherBands: stringList(pick(data, 'weather_bands', 'weatherBands')),
      currency: pick(data, 'currency') as String? ?? 'PKR',
      style: pick(data, 'style') as String? ?? 'casual',
      seasonTags: stringList(pick(data, 'season_tags', 'seasonTags')),
    );
  }

  Map<String, dynamic> toRow() => {
        'id': id,
        'name': name,
        'description': description,
        'price': price,
        'image_url': imageUrl,
        'category': category.name,
        'subcategory': subcategory,
        'color': color,
        'culture_tags': cultureTags,
        'weather_bands': weatherBands,
        'currency': currency,
        'style': style,
        'season_tags': seasonTags,
      };

  String get priceLabel => '$currency ${price.toStringAsFixed(0)}';
}

class CartItem {
  const CartItem({
    required this.product,
    this.quantity = 1,
  });

  final ProductModel product;
  final int quantity;

  double get lineTotal => product.price * quantity;

  Map<String, dynamic> toRow(String userId) => {
        'user_id': userId,
        'product_id': product.id,
        'name': product.name,
        'price': product.price,
        'image_url': product.imageUrl,
        'quantity': quantity,
      };

  CartItem copyWith({int? quantity}) =>
      CartItem(product: product, quantity: quantity ?? this.quantity);
}

class OrderModel {
  const OrderModel({
    required this.id,
    required this.userId,
    required this.items,
    required this.total,
    required this.status,
    required this.createdAt,
    this.note,
  });

  final String id;
  final String userId;
  final List<CartItem> items;
  final double total;
  final OrderStatus status;
  final DateTime createdAt;
  final String? note;

  Map<String, dynamic> toRow() => {
        'id': id,
        'user_id': userId,
        'items': items
            .map((e) => {
                  'product_id': e.product.id,
                  'name': e.product.name,
                  'price': e.product.price,
                  'image_url': e.product.imageUrl,
                  'quantity': e.quantity,
                })
            .toList(),
        'total': total,
        'status': status.name,
        'note': note,
        'is_simulated_checkout': true,
      };
}

class TrendModel {
  const TrendModel({
    required this.id,
    required this.title,
    required this.subtitle,
    required this.description,
    required this.imageUrl,
    required this.cultureTags,
    required this.colors,
    required this.itemTypes,
    required this.season,
    this.stylingIdea,
  });

  final String id;
  final String title;
  final String subtitle;
  final String description;
  final String imageUrl;
  final List<String> cultureTags;
  final List<String> colors;
  final List<String> itemTypes;
  final String season;
  final String? stylingIdea;

  factory TrendModel.fromMap(String id, Map<String, dynamic> data) {
    return TrendModel(
      id: (pick(data, 'id') as String?) ?? id,
      title: pick(data, 'title') as String? ?? '',
      subtitle: pick(data, 'subtitle') as String? ?? '',
      description: pick(data, 'description') as String? ?? '',
      imageUrl: pick(data, 'image_url', 'imageUrl') as String? ?? '',
      cultureTags: stringList(pick(data, 'culture_tags', 'cultureTags')),
      colors: stringList(pick(data, 'colors')),
      itemTypes: stringList(pick(data, 'item_types', 'itemTypes')),
      season: pick(data, 'season') as String? ?? 'all',
      stylingIdea: pick(data, 'styling_idea', 'stylingIdea') as String?,
    );
  }
}

class EventModel {
  const EventModel({
    required this.id,
    required this.name,
    required this.dateTime,
    required this.occasion,
    this.location,
    this.notes,
  });

  final String id;
  final String name;
  final DateTime dateTime;
  final Occasion occasion;
  final String? location;
  final String? notes;

  factory EventModel.fromMap(String id, Map<String, dynamic> data) {
    return EventModel(
      id: (pick(data, 'id') as String?) ?? id,
      name: pick(data, 'name') as String? ?? 'Event',
      dateTime: parseDate(pick(data, 'date_time', 'dateTime')) ?? DateTime.now(),
      occasion: enumFromString(
        Occasion.values,
        pick(data, 'occasion') as String?,
        Occasion.other,
      ),
      location: pick(data, 'location') as String?,
      notes: pick(data, 'notes') as String?,
    );
  }

  Map<String, dynamic> toRow(String userId) => {
        'id': id,
        'user_id': userId,
        'name': name,
        'date_time': dateTime.toIso8601String(),
        'occasion': occasion.name,
        'location': location,
        'notes': notes,
      };
}

class OutfitFeedback {
  const OutfitFeedback({
    required this.id,
    required this.outfitId,
    required this.type,
    required this.colors,
    required this.subcategories,
    required this.createdAt,
  });

  final String id;
  final String outfitId;
  final FeedbackType type;
  final List<String> colors;
  final List<String> subcategories;
  final DateTime createdAt;

  Map<String, dynamic> toRow(String userId) => {
        'id': id,
        'user_id': userId,
        'outfit_id': outfitId,
        'type': type.name,
        'colors': colors,
        'subcategories': subcategories,
      };

  factory OutfitFeedback.fromMap(String id, Map<String, dynamic> data) {
    return OutfitFeedback(
      id: (pick(data, 'id') as String?) ?? id,
      outfitId: pick(data, 'outfit_id', 'outfitId') as String? ?? '',
      type: enumFromString(
        FeedbackType.values,
        pick(data, 'type') as String?,
        FeedbackType.like,
      ),
      colors: stringList(pick(data, 'colors')),
      subcategories: stringList(pick(data, 'subcategories')),
      createdAt: parseDate(pick(data, 'created_at', 'createdAt')) ?? DateTime.now(),
    );
  }
}

class ClothingAnalysis {
  const ClothingAnalysis({
    required this.category,
    required this.subcategory,
    required this.color,
    this.secondaryColor,
    this.secondaryColors = const [],
    this.accentColors = const [],
    this.colorDistribution = const {},
    this.pattern = 'solid',
    this.isMulticolor = false,
    this.confidence = 0,
    this.usedFallback = false,
    this.message,
    this.detectedItems = const [],
  });

  final ClothingCategory category;
  final String subcategory;
  final String color;
  final String? secondaryColor;
  final List<String> secondaryColors;
  final List<String> accentColors;
  final Map<String, double> colorDistribution;
  final String pattern;
  final bool isMulticolor;
  final double confidence;
  final bool usedFallback;
  final String? message;
  final List<DetectedClothingItem> detectedItems;
}

class DetectedClothingItem {
  const DetectedClothingItem({
    required this.category,
    required this.subcategory,
    required this.confidence,
    this.color,
    this.secondaryColor,
    this.secondaryColors = const [],
    this.accentColors = const [],
    this.colorDistribution = const {},
    this.pattern,
    this.isMulticolor = false,
    this.bbox,
    this.region,
  });

  final ClothingCategory category;
  final String subcategory;
  final double confidence;
  final String? color;
  final String? secondaryColor;
  final List<String> secondaryColors;
  final List<String> accentColors;
  final Map<String, double> colorDistribution;
  final String? pattern;
  final bool isMulticolor;
  final List<double>? bbox;
  final String? region;

  factory DetectedClothingItem.fromJson(Map<String, dynamic> json) {
    final box = json['bbox'];
    final rawCategory = enumFromString(
      ClothingCategory.values,
      json['category'] as String?,
      ClothingCategory.accessories,
    );
    final rawSub =
        json['subcategory'] as String? ?? ClothingCatalog.unknownType;
    final normalized = ClothingCatalog.normalizeDetection(
      category: rawCategory,
      subcategory: rawSub,
    );
    final distRaw = json['colorDistribution'];
    final dist = <String, double>{};
    if (distRaw is Map) {
      for (final entry in distRaw.entries) {
        final value = entry.value;
        if (value is num) dist[entry.key.toString()] = value.toDouble();
      }
    }
    return DetectedClothingItem(
      category: normalized.$1,
      subcategory: normalized.$2,
      confidence: (json['confidence'] as num?)?.toDouble() ?? 0,
      color: ClothingCatalog.catalogColor(json['color'] as String?) ??
          json['color'] as String?,
      secondaryColor: ClothingCatalog.catalogColor(
            json['secondaryColor'] as String?,
          ) ??
          json['secondaryColor'] as String?,
      secondaryColors: [
        for (final item in (json['secondaryColors'] as List? ?? const []))
          if (item is String) item,
      ],
      accentColors: [
        for (final item in (json['accentColors'] as List? ?? const []))
          if (item is String) item,
      ],
      colorDistribution: dist,
      pattern: json['pattern'] as String?,
      isMulticolor: json['isMulticolor'] == true,
      bbox: box is List
          ? [
              for (final v in box)
                if (v is num) v.toDouble(),
            ]
          : null,
      region: json['region'] as String?,
    );
  }
}

class SkinToneAnalysis {
  const SkinToneAnalysis({
    required this.skinTone,
    this.ita,
    this.usedFallback = false,
    this.message,
  });

  final SkinTone skinTone;
  final double? ita;
  final bool usedFallback;
  final String? message;
}

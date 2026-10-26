import 'dart:convert';
import 'dart:typed_data';

import 'package:http/http.dart' as http;

import '../models/product_model.dart';
import '../utils/clothing_catalog.dart';
import '../utils/constants.dart';
import '../utils/enums.dart';
import 'local_image_analysis.dart';

class ImageAnalysisService {
  ImageAnalysisService({http.Client? client}) : _client = client ?? http.Client();

  final http.Client _client;

  Future<ClothingAnalysis> analyzeClothing(Uint8List bytes) async {
    final local = LocalImageAnalysis.analyzeClothing(bytes);
    try {
      final uri = Uri.parse('${AppConstants.mlServiceUrl()}/analyze-clothing');
      final request = http.MultipartRequest('POST', uri)
        ..headers.addAll(AppConstants.mlHeaders)
        ..files.add(
          http.MultipartFile.fromBytes(
            'file',
            bytes,
            filename: 'clothing.jpg',
          ),
        );
      final streamed =
          await _client.send(request).timeout(const Duration(seconds: 45));
      final body = await streamed.stream.bytesToString();
      if (streamed.statusCode != 200) return local;
      final json = jsonDecode(body) as Map<String, dynamic>;
      if (json['detectionStrategy'] == 'maskrcnn' || json['source'] == 'gemini') {
        final detected = _parseDetected(json);
        if (detected.isNotEmpty) {
          final lead = detected.first;
          final colors = _preferGarmentColor(
            localColor: local.color,
            localSecondary: local.secondaryColor,
            mlColor: json['color'] as String?,
            mlSecondary: json['secondaryColor'] as String?,
          );
          final patternRaw = (json['pattern'] as String?) ?? 'solid';
          final pattern = ClothingCatalog.patterns.contains(patternRaw)
              ? patternRaw
              : 'solid';
          return ClothingAnalysis(
            category: lead.category,
            subcategory: lead.subcategory,
            color: colors.$1,
            secondaryColor: colors.$2,
            secondaryColors: [
              for (final item in (json['secondaryColors'] as List? ?? const []))
                if (item is String) item,
            ],
            accentColors: [
              for (final item in (json['accentColors'] as List? ?? const []))
                if (item is String) item,
            ],
            colorDistribution: _colorDistribution(json['colorDistribution']),
            pattern: pattern,
            isMulticolor: json['isMulticolor'] == true,
            confidence: lead.confidence,
            usedFallback: false,
            message: json['message'] as String? ??
                'Detected ${lead.subcategory}.',
            detectedItems: detected,
          );
        }
        return ClothingAnalysis(
          category: ClothingCategory.accessories,
          subcategory: ClothingCatalog.unknownType,
          color: local.color,
          secondaryColor: local.secondaryColor,
          confidence: 0,
          usedFallback: true,
          message:
              'Not recognized. Please choose the category and type. '
              'A watch often scores too low to pass, and jewelry is not one of the trained classes.',
          detectedItems: const [],
        );
      }
      var extras = _parseDetected(json);
      var mlCategory = json['category'] as String?;
      var mlSubcategory = json['subcategory'] as String?;
      var mlConfidence = (json['confidence'] as num?)?.toDouble() ?? 0;
      var mlSource = json['source'] as String? ?? 'none';
      var mlMessage = json['message'] as String?;
      const footwear = {
        'heels',
        'shoes',
        'sneakers',
        'flats',
        'boots',
        'sandals',
        'loafers',
      };
      if (json['isolatedProduct'] == true) {
        DetectedClothingItem? shoe;
        for (final item in extras) {
          if (footwear.contains(item.subcategory) &&
              item.confidence >= 0.30 &&
              (shoe == null || item.confidence > shoe.confidence)) {
            shoe = item;
          }
        }
        // A close-up shoe can be mistaken for trouser legs by the
        // lowerwear model. Prefer the detected footwear item.
        if (shoe != null) {
          mlCategory = 'footwear';
          mlSubcategory = shoe.subcategory;
          mlConfidence = shoe.confidence;
          mlSource = 'accessory';
          mlMessage =
              'Detected ${shoe.subcategory} (${(shoe.confidence * 100).round()}%).';
        }
      }
      extras = _leadPantsOverDressOnCloseup(extras);
      extras = _dropBagWhenPantsLead(extras);
      DetectedClothingItem? pants;
      for (final item in extras) {
        if ({'trousers', 'jeans', 'shorts', 'shalwar', 'leggings'}.contains(item.subcategory)) {
          if (pants == null || item.confidence > pants.confidence) {
            pants = item;
          }
        }
      }
      if (pants != null &&
          ClothingCatalog.dressLabels.contains(mlSubcategory) &&
          pants.confidence >= 0.50) {
        mlCategory = 'lowerwear';
        mlSubcategory = pants.subcategory;
        mlConfidence = pants.confidence;
        mlSource = 'lowerwear';
        mlMessage =
            'Detected ${pants.subcategory} (${(pants.confidence * 100).round()}%).';
      }
      // Strong trousers/shorts must beat a weak ImageNet primary (e.g. blazer).
      if (pants != null &&
          pants.confidence >= 0.55 &&
          pants.confidence >= (mlConfidence ?? 0) + 0.15 &&
          !{'trousers', 'jeans', 'shorts', 'skirt', 'shalwar', 'leggings'}
              .contains(mlSubcategory)) {
        mlCategory = 'lowerwear';
        mlSubcategory = pants.subcategory;
        mlConfidence = pants.confidence;
        mlSource = 'lowerwear';
        mlMessage =
            'Detected ${pants.subcategory} (${(pants.confidence * 100).round()}%).';
      }
      // Tops must never stay as Dress when upperwear is competitive,
      // unless the 6-class upperwear head already called the item a dress/gown.
      final mlOwnsDress = mlSource == 'upperwear' &&
          ClothingCatalog.dressLabels.contains(mlSubcategory) &&
          mlConfidence >= 0.38;
      DetectedClothingItem? top;
      for (final item in extras) {
        if ({
          'shirt',
          't-shirt',
          'tshirt',
          'jacket',
          'hoodie',
          'blouse',
          'top',
        }.contains(item.subcategory)) {
          if (top == null || item.confidence > top.confidence) {
            top = item;
          }
        }
      }
      if (top != null &&
          ClothingCatalog.dressLabels.contains(mlSubcategory) &&
          top.confidence >= 0.40 &&
          !mlOwnsDress) {
        mlCategory = 'upperwear';
        mlSubcategory = top.subcategory;
        mlConfidence = top.confidence;
        mlSource = 'upperwear';
        mlMessage =
            'Detected ${top.subcategory} (${(top.confidence * 100).round()}%).';
      }
      if (top != null &&
          {'dupatta', 'hat', 'scarf'}.contains(mlSubcategory) &&
          !{
            'dupatta_gate',
            'hat_gate',
            'watch_gate',
            'bag_gate',
            'shoes_gate',
            'heels_gate',
            'sneakers_gate',
            'flats_gate',
          }.contains(mlSource) &&
          !{
            'shoes',
            'heels',
            'sneakers',
            'flats',
            'boots',
            'sandals',
            'loafers',
          }.contains(mlSubcategory) &&
          top.confidence >= 0.46) {
        mlCategory = 'upperwear';
        mlSubcategory = top.subcategory;
        mlConfidence = top.confidence;
        mlSource = 'shirt_gate';
        mlMessage =
            'Detected ${top.subcategory} (${(top.confidence * 100).round()}%).';
      }
      if ((mlSource == 'tshirt_gate') && mlSubcategory == 't-shirt') {
        mlCategory = 'upperwear';
      }
      if ((mlSource == 'jacket_gate') && mlSubcategory == 'jacket') {
        mlCategory = 'upperwear';
      }
      if ((mlSource == 'flats_gate') && mlSubcategory == 'flats') {
        mlCategory = 'footwear';
      }
      if ((mlSource == 'heels_gate') && mlSubcategory == 'heels') {
        mlCategory = 'footwear';
      }
      if ((mlSource == 'sneakers_gate') && mlSubcategory == 'sneakers') {
        mlCategory = 'footwear';
      }
      if ((mlSource == 'shoes_gate') && mlSubcategory == 'shoes') {
        mlCategory = 'footwear';
      }
      if ((mlSource == 'shirt_gate' || mlSource == 'upperwear') &&
          {
            'shirt',
            't-shirt',
            'hoodie',
            'jacket',
            'top',
            'blouse',
            'coat',
          }.contains(mlSubcategory)) {
        mlCategory = 'upperwear';
      }
      if (mlSource == 'upperwear' &&
          ClothingCatalog.dressLabels.contains(mlSubcategory)) {
        mlCategory = 'dress';
      }
      if (local.category == ClothingCategory.upperwear &&
          ClothingCatalog.dressLabels.contains(mlSubcategory) &&
          local.confidence >= 0.45 &&
          mlSource != 'upperwear' &&
          {'shirt', 't-shirt', 'tshirt', 'jacket', 'hoodie', 'blouse', 'top'}
              .contains(local.subcategory)) {
        mlCategory = 'upperwear';
        mlSubcategory = local.subcategory;
        mlConfidence = local.confidence;
        mlSource = 'local';
        mlMessage =
            'Detected ${local.subcategory} (${(local.confidence * 100).round()}%).';
      }
      if (pants != null &&
          ClothingCatalog.bagLabels.contains(mlSubcategory ?? '') &&
          pants.confidence >= 0.50) {
        mlCategory = 'lowerwear';
        mlSubcategory = pants.subcategory;
        mlConfidence = pants.confidence;
        mlSource = 'lowerwear';
        mlMessage =
            'Detected ${pants.subcategory} (${(pants.confidence * 100).round()}%).';
      }
      if (json['isolatedProduct'] == true) {
        extras = _leadHatOverLowerwearOnCloseup(extras);
        DetectedClothingItem? hat;
        for (final item in extras) {
          if (item.subcategory == 'hat') hat ??= item;
        }
        if (hat != null &&
            (ClothingCatalog.skirtLabels.contains(mlSubcategory) ||
                {'shorts', 'trousers', 'jeans'}.contains(mlSubcategory))) {
          mlCategory = 'accessories';
          mlSubcategory = 'hat';
          mlConfidence = hat.confidence;
          mlSource = 'accessory';
          mlMessage = 'Detected Hat (${(hat.confidence * 100).round()}%).';
        }
      }
      final resolved = ClothingCatalog.resolvePrediction(
        localCategory: local.category,
        localSubcategory: local.subcategory,
        localConfidence: local.confidence,
        mlCategory: enumFromString(
          ClothingCategory.values,
          mlCategory,
          local.category,
        ),
        mlSubcategory: mlSubcategory,
        mlConfidence: mlConfidence,
        mlSource: mlSource,
        mlUncertain: json['usedFallback'] == true,
        mlMessage: mlMessage,
        extraItemsMessage: extras.length > 1
            ? 'Also visible: ${extras.skip(1).map((e) => e.subcategory).join(', ')}.'
            : _extraItemsMessage(json['items']),
      );
      final colors = _preferGarmentColor(
        localColor: local.color,
        localSecondary: local.secondaryColor,
        mlColor: json['color'] as String?,
        mlSecondary: json['secondaryColor'] as String?,
      );
      final secondaryColors = [
        for (final item in (json['secondaryColors'] as List? ?? const []))
          if (item is String) item,
      ];
      final accentColors = [
        for (final item in (json['accentColors'] as List? ?? const []))
          if (item is String) item,
      ];
      final distRaw = json['colorDistribution'];
      final distribution = <String, double>{};
      if (distRaw is Map) {
        for (final entry in distRaw.entries) {
          final value = entry.value;
          if (value is num) {
            distribution[entry.key.toString()] = value.toDouble();
          }
        }
      }
      final patternRaw = (json['pattern'] as String?) ?? 'solid';
      final pattern = ClothingCatalog.patterns.contains(patternRaw)
          ? patternRaw
          : 'solid';
      return ClothingAnalysis(
        category: resolved.category,
        subcategory: resolved.subcategory,
        color: colors.$1,
        secondaryColor: colors.$2,
        secondaryColors: secondaryColors,
        accentColors: accentColors,
        colorDistribution: distribution,
        pattern: pattern,
        isMulticolor: json['isMulticolor'] == true,
        confidence: resolved.confidence,
        usedFallback: resolved.usedFallback,
        message: resolved.message,
        detectedItems: extras,
      );
    } catch (_) {
      return local;
    }
  }

  /// Save a labeled photo for later fine-tuning. Does not change the live model.
  Future<bool> teachClothing(Uint8List bytes, String label) async {
    try {
      final uri = Uri.parse('${AppConstants.mlServiceUrl()}/teach-clothing');
      final request = http.MultipartRequest('POST', uri)
        ..headers.addAll(AppConstants.mlHeaders)
        ..fields['label'] = label
        ..files.add(
          http.MultipartFile.fromBytes(
            'file',
            bytes,
            filename: 'clothing.jpg',
          ),
        );
      final streamed =
          await _client.send(request).timeout(const Duration(seconds: 20));
      return streamed.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  static Map<String, double> _colorDistribution(Object? distRaw) {
    final distribution = <String, double>{};
    if (distRaw is Map) {
      for (final entry in distRaw.entries) {
        final value = entry.value;
        if (value is num) {
          distribution[entry.key.toString()] = value.toDouble();
        }
      }
    }
    return distribution;
  }

  static (String, String?) _preferGarmentColor({
    required String localColor,
    required String? localSecondary,
    required String? mlColor,
    required String? mlSecondary,
  }) {
    final mapped = ClothingCatalog.catalogColor(mlColor);
    if (mapped != null) {
      final second = ClothingCatalog.catalogColor(mlSecondary);
      return (mapped, second == mapped ? null : second);
    }
    return (localColor, localSecondary);
  }

  List<DetectedClothingItem> _parseDetected(Map<String, dynamic> json) {
    final raw = json['detected'];
    if (raw is List && raw.isNotEmpty) {
      return [
        for (final row in raw)
          if (row is Map)
            DetectedClothingItem.fromJson(Map<String, dynamic>.from(row)),
      ].where((e) => e.subcategory != ClothingCatalog.unknownType).toList();
    }
    final extras = json['items'];
    final lead = DetectedClothingItem.fromJson(json);
    final more = <DetectedClothingItem>[];
    if (extras is List) {
      for (final row in extras) {
        if (row is! Map) continue;
        more.add(DetectedClothingItem.fromJson(Map<String, dynamic>.from(row)));
      }
    }
    return [
      lead,
      ...more,
    ].where((e) => e.subcategory != ClothingCatalog.unknownType).toList();
  }

  String? _extraItemsMessage(Object? raw) {
    if (raw is! List || raw.isEmpty) return null;
    final names = <String>[];
    for (final item in raw) {
      if (item is! Map) continue;
      final sub = item['subcategory'] as String?;
      final conf = (item['confidence'] as num?)?.toDouble();
      if (sub == null || sub == ClothingCatalog.unknownType) continue;
      names.add(
        conf == null ? sub : '$sub (${(conf * 100).round()}%)',
      );
    }
    if (names.isEmpty) return null;
    return 'Other visible items: ${names.join(', ')}.';
  }

  static List<DetectedClothingItem> _leadHatOverSkirtOnCloseup(
    List<DetectedClothingItem> items,
  ) {
    return _leadHatOverLowerwearOnCloseup(items);
  }

  static List<DetectedClothingItem> _leadHatOverLowerwearOnCloseup(
    List<DetectedClothingItem> items,
  ) {
    DetectedClothingItem? hat;
    var hasLower = false;
    for (final item in items) {
      if (item.subcategory == 'hat') hat ??= item;
      if (ClothingCatalog.skirtLabels.contains(item.subcategory) ||
          {'shorts', 'trousers', 'jeans'}.contains(item.subcategory)) {
        hasLower = true;
      }
    }
    if (hat == null || !hasLower) return items;
    return [
      hat,
      ...items.where(
        (item) =>
            item.subcategory != 'hat' &&
            !ClothingCatalog.skirtLabels.contains(item.subcategory) &&
            !{'shorts', 'trousers', 'jeans'}.contains(item.subcategory),
      ),
    ];
  }

  static List<DetectedClothingItem> _dropBagWhenPantsLead(
    List<DetectedClothingItem> items,
  ) {
    DetectedClothingItem? pants;
    for (final item in items) {
      if ({'trousers', 'jeans', 'shorts'}.contains(item.subcategory) &&
          item.confidence >= 0.50) {
        if (pants == null || item.confidence > pants.confidence) {
          pants = item;
        }
      }
    }
    if (pants == null) return items;
    return [
      for (final item in items)
        if (!ClothingCatalog.bagLabels.contains(item.subcategory)) item,
    ];
  }

  static List<DetectedClothingItem> _leadPantsOverDressOnCloseup(
    List<DetectedClothingItem> items,
  ) {
    DetectedClothingItem? pants;
    var hasDress = false;
    for (final item in items) {
      if ({'trousers', 'jeans', 'shorts'}.contains(item.subcategory) &&
          item.confidence >= 0.50) {
        if (pants == null || item.confidence > pants.confidence) {
          pants = item;
        }
      }
      if (ClothingCatalog.dressLabels.contains(item.subcategory)) {
        hasDress = true;
      }
    }
    if (pants == null || !hasDress) return items;
    return [
      pants,
      ...items.where(
        (item) =>
            item.subcategory != pants!.subcategory &&
            !ClothingCatalog.dressLabels.contains(item.subcategory),
      ),
    ];
  }

  Future<SkinToneAnalysis> analyzeSkinTone(
    Uint8List bytes, {
    SkinTone? previous,
  }) async {
    return LocalImageAnalysis.analyzeSkinTone(bytes, previous: previous);
  }
}

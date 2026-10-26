import 'dart:math';
import 'dart:typed_data';

import 'package:image/image.dart' as img;

import '../models/product_model.dart';
import '../utils/clothing_catalog.dart';
import '../utils/enums.dart';
import 'outfit_part_model.dart';

/// On-device color / type assist used when the FastAPI ML service is down.
class LocalImageAnalysis {
  static const _size = 192;
  static const _named = <String, List<int>>{
    'black': [20, 20, 20],
    'white': [245, 245, 245],
    'grey': [128, 128, 128],
    'red': [190, 30, 40],
    'blue': [40, 80, 180],
    'green': [40, 130, 70],
    'yellow': [230, 200, 50],
    'orange': [230, 120, 30],
    'brown': [110, 70, 40],
    'beige': [210, 190, 155],
    'pink': [220, 120, 150],
    'purple': [120, 60, 150],
    'navy': [20, 35, 80],
    'maroon': [110, 20, 40],
    'cream': [245, 235, 215],
    'olive': [110, 115, 50],
    'gold': [200, 160, 50],
    'teal': [30, 130, 130],
  };

  static ClothingAnalysis analyzeClothing(Uint8List bytes) {
    final decoded = img.decodeImage(bytes);
    if (decoded == null) {
      return const ClothingAnalysis(
        category: ClothingCategory.accessories,
        subcategory: ClothingCatalog.unknownType,
        color: 'black',
        usedFallback: true,
        message:
            'Could not read the image. Select category and color manually.',
      );
    }
    final resized = _keepAspect(decoded);
    final fg = _foreground(resized);
    final color = _colorFromPixels(
      fg.colorPixels,
      backgroundName: fg.backgroundName,
      backgroundRgb: fg.backgroundRgb,
    );
    final desc = _descriptorFrom(
      fg,
      color,
      resized.width / resized.height,
    );
    final model = OutfitPartModel.predict(desc.features);
    final type = _applyTrainedGuess(model, desc, fg);
    final normalized = ClothingCatalog.normalizeDetection(
      category: type.category,
      subcategory: type.subcategory,
    );
    final namedColor = _refineColor(desc.color, normalized.$2);
    final unknown = normalized.$2 == ClothingCatalog.unknownType;
    return ClothingAnalysis(
      category: normalized.$1,
      subcategory: normalized.$2,
      color: namedColor,
      secondaryColor:
          desc.secondaryColor == namedColor ? null : desc.secondaryColor,
      confidence: type.confidence,
      usedFallback: unknown || type.confidence < 0.55,
      message: unknown
          ? 'Uncertain. Please select the type.'
          : 'Detected ${normalized.$2} in $namedColor. Confirm if this looks wrong.',
    );
  }

  /// Public feature snapshot used by training and inference.
  static ClothingDescriptor? describe(Uint8List bytes) {
    final decoded = img.decodeImage(bytes);
    if (decoded == null) return null;
    final resized = _keepAspect(decoded);
    final fg = _foreground(resized);
    final color = _colorFromPixels(
      fg.colorPixels,
      backgroundName: fg.backgroundName,
      backgroundRgb: fg.backgroundRgb,
    );
    return _descriptorFrom(fg, color, resized.width / resized.height);
  }

  static ClothingDescriptor _descriptorFrom(
    _FgStats fg,
    ({String primary, String? secondary}) color,
    double imageAspect,
  ) {
    var brightness = 0.0;
    if (fg.colorPixels.isNotEmpty) {
      for (final p in fg.colorPixels) {
        brightness += (p[0] + p[1] + p[2]) / (3 * 255);
      }
      brightness /= fg.colorPixels.length;
    }
    final widthFrac =
        (fg.occupancy / (fg.fill * fg.heightFrac + 1e-6)).clamp(0.0, 1.0);
    return ClothingDescriptor(
      features: [
        fg.occupancy,
        (fg.aspect / 3).clamp(0.0, 1.0),
        fg.fill.clamp(0.0, 1.0),
        fg.cx,
        fg.cy,
        fg.heightFrac,
        (fg.flare / 2.5).clamp(0.0, 1.0),
        fg.upperMass,
        fg.lowerCenterFill,
        fg.edgeRatio,
        fg.hollow,
        (fg.blobs / 4).clamp(0.0, 1.0),
        (fg.largestBlob / 80).clamp(0.0, 1.0),
        fg.skinRatio,
        fg.lShape ? 1.0 : 0.0,
        fg.topHeavy ? 1.0 : 0.0,
        color.primary == 'gold' ? 1.0 : 0.0,
        color.primary == 'blue' || color.primary == 'navy' ? 1.0 : 0.0,
        {'gold', 'grey', 'white', 'cream', 'black'}.contains(color.primary)
            ? 1.0
            : 0.0,
        (imageAspect / 2).clamp(0.0, 1.0),
        widthFrac,
        brightness.clamp(0.0, 1.0),
        ...fg.grid9,
        ...fg.bands4,
        ...fg.hues6,
      ],
      color: color.primary,
      secondaryColor: color.secondary,
      lShape: fg.lShape,
      heightFrac: fg.heightFrac,
      occupancy: fg.occupancy,
      aspect: fg.aspect,
      flare: fg.flare,
      upperMass: fg.upperMass,
      denim: color.primary == 'blue',
      fill: fg.fill,
      blobs: fg.blobs,
      hollow: fg.hollow,
      largestBlob: fg.largestBlob,
      cy: fg.cy,
      lowerCenterFill: fg.lowerCenterFill,
      edgeRatio: fg.edgeRatio,
      topFrac: fg.topFrac,
    );
  }

  static String _refineColor(String color, String subcategory) {
    if (subcategory == 'jewelry' &&
        {'yellow', 'brown', 'beige', 'orange'}.contains(color)) {
      return 'gold';
    }
    if (subcategory == 'jeans' && color == 'teal') return 'blue';
    return color;
  }

  static ({ClothingCategory category, String subcategory, double confidence})
      _applyTrainedGuess(
    OutfitPrediction model,
    ClothingDescriptor desc,
    _FgStats fg,
  ) {
    final family = OutfitPartModel.predictFamily(desc.features);
    var sub = model.label;
    var confidence = model.confidence;

    final exclusive = _exclusiveAccessory(desc);
    if (exclusive != null) {
      sub = exclusive;
      confidence = 0.88;
    } else if (_looksLikeSunglasses(desc)) {
      sub = 'sunglasses';
      confidence = 0.84;
    } else if (_looksLikeHat(desc) || _looksLikeCap(desc)) {
      sub = 'hat';
      confidence = 0.90;
    } else if (_looksLikeShorts(desc)) {
      sub = 'shorts';
      confidence = 0.88;
    } else if (_looksLikeTrousers(desc)) {
      sub = desc.denim ? 'jeans' : 'trousers';
      confidence = 0.88;
    } else if (_looksLikeSkirt(desc)) {
      sub = 'skirt';
      confidence = 0.88;
    } else if (_isBodyGarment(desc) &&
        !_looksLikeDress(desc) &&
        !_looksLikeHat(desc) &&
        !_looksLikeCap(desc)) {
      // Hanging / laid-out shirts are often ImageNet cowboy_hat. Prefer
      // upperwear from geometry before accessory heuristics.
      sub = switch (desc.color) {
        'black' || 'navy' || 'grey' when desc.occupancy > 0.50 => 'hoodie',
        'black' || 'navy' || 'grey' => 'jacket',
        'white' || 'cream' || 'blue' => 'shirt',
        _ => 't-shirt',
      };
      confidence = 0.84;
    } else if (_explicitBagShape(desc) ||
        _looksLikeHandledBag(desc) ||
        _looksLikeBackpack(desc) ||
        _looksLikeClutch(desc)) {
      sub = 'bag';
      confidence = 0.90;
    } else if (_hatFromModel(desc)) {
      sub = 'hat';
      confidence = 0.86;
    } else if (_looksLikeBag(desc)) {
      sub = 'bag';
      confidence = 0.90;
    } else if (_looksLikeCloseupShoe(desc) ||
        (_looksLikeFootwear(desc) &&
            family.label != 'dress' &&
            family.label != 'accessory')) {
      sub = _footwearSub(desc, preferModel: true);
      confidence = 0.86;
    } else if (_looksLikeDress(desc) && !_bagLikeNotDress(desc)) {
      sub = 'dress';
      confidence = 0.88;
    } else if (_looksLikeJeans(desc)) {
      sub = 'jeans';
      confidence = 0.82;
    } else if (desc.blobs >= 2 &&
        !_looksLikeJewelry(desc) &&
        !_looksLikeSunglasses(desc) &&
        desc.occupancy >= 0.08 &&
        desc.occupancy < 0.50 &&
        desc.heightFrac < 0.42 &&
        (desc.aspect > 1.00 || desc.cy > 0.52)) {
      sub = _footwearSub(desc, preferModel: true);
      confidence = 0.86;
    } else if (desc.blobs >= 2 &&
        (family.label == 'dress' || family.label == 'accessory') &&
        desc.heightFrac < 0.72 &&
        desc.occupancy < 0.40 &&
        !_looksLikeJewelry(desc) &&
        !_looksLikeSunglasses(desc)) {
      sub = _footwearSub(desc, preferModel: true);
      confidence = 0.82;
    } else if (_looksLikeFootwear(desc) &&
        family.label != 'dress' &&
        family.label != 'upperwear' &&
        desc.aspect > 1.10) {
      sub = _footwearSub(desc, preferModel: true);
      confidence = 0.84;
    } else if (desc.occupancy > 0.38 &&
        desc.aspect > 0.75 &&
        desc.aspect < 1.50 &&
        desc.heightFrac > 0.48 &&
        desc.flare < 1.12 &&
        desc.blobs <= 1 &&
        !desc.denim &&
        !_looksLikeDress(desc) &&
        {'red', 'orange', 'pink', 'yellow', 'green', 'teal', 'purple'}
            .contains(desc.color) &&
        _isBodyGarment(desc)) {
      sub = 't-shirt';
      confidence = 0.72;
    } else if (family.confidence >= 0.36) {
      sub = OutfitPartModel.leafForFamily(family.label, desc.features);
      confidence = family.confidence;
      if (family.label == 'accessory') {
        if (_looksLikeHat(desc) || _looksLikeCap(desc)) {
          sub = 'hat';
        } else if (_looksLikeShorts(desc)) {
          sub = 'shorts';
        } else if (_looksLikeTrousers(desc)) {
          sub = desc.denim ? 'jeans' : 'trousers';
        } else if (_looksLikeSkirt(desc)) {
          sub = 'skirt';
        } else if (_looksLikeHandledBag(desc) ||
            _looksLikeBackpack(desc) ||
            _looksLikeClutch(desc) ||
            _looksLikeBag(desc)) {
          sub = 'bag';
        } else if (desc.cy > 0.56 &&
            desc.aspect > 1.20 &&
            desc.heightFrac < 0.42 &&
            !_looksLikeSunglasses(desc)) {
          sub = _footwearSub(desc, preferModel: true);
        }
      } else if (family.label == 'footwear') {
        if (_looksLikeSkirt(desc)) {
          sub = 'skirt';
        } else if (_looksLikeHandledBag(desc) ||
            _looksLikeBackpack(desc) ||
            _looksLikeClutch(desc) ||
            _looksLikeBag(desc)) {
          sub = 'bag';
        } else if (_hatLikeNotShoe(desc) || _looksLikeCap(desc)) {
          sub = 'hat';
        } else {
          sub = _footwearSub(desc, preferModel: true);
        }
      } else if (family.label == 'dress') {
        if (_looksLikeShorts(desc)) {
          sub = 'shorts';
          confidence = max(confidence, 0.86);
        } else if (_looksLikeTrousers(desc)) {
          sub = desc.denim ? 'jeans' : 'trousers';
          confidence = max(confidence, 0.86);
        } else if (_looksLikeSkirt(desc)) {
          sub = 'skirt';
          confidence = max(confidence, 0.86);
        } else if (desc.blobs >= 2 &&
            desc.cy > 0.56 &&
            desc.heightFrac < 0.45) {
          sub = _footwearSub(desc, preferModel: true);
          confidence = 0.80;
        }
      } else if (family.label == 'lowerwear') {
        if (_looksLikeShorts(desc)) {
          sub = 'shorts';
          confidence = max(confidence, 0.88);
        } else if (_looksLikeTrousers(desc)) {
          sub = desc.denim ? 'jeans' : 'trousers';
          confidence = max(confidence, 0.86);
        } else if (_looksLikeSkirt(desc)) {
          sub = 'skirt';
          confidence = max(confidence, 0.84);
        } else if (_looksLikeDress(desc)) {
          sub = 'dress';
          confidence = max(confidence, 0.82);
        } else if (_looksLikeJeans(desc)) {
          sub = 'jeans';
          confidence = max(confidence, 0.78);
        }
      } else if (family.label == 'upperwear' &&
          {'shirt', 't-shirt', 'hoodie', 'jacket', 'coat', 'sweater'}
              .contains(sub) &&
          !_isBodyGarment(desc) &&
          (_looksLikeHat(desc) || _looksLikeCap(desc) || _hatFromModel(desc))) {
        // Only rewrite a weak upperwear guess to hat when the crop is
        // actually cap-shaped — never for a hanging shirt panel.
        sub = 'hat';
        confidence = max(confidence, 0.82);
      }
    } else if (_looksLikeShorts(desc)) {
      sub = 'shorts';
      confidence = 0.84;
    } else if (_looksLikeSkirt(desc)) {
      sub = 'skirt';
      confidence = 0.84;
    } else if (_looksLikeDress(desc)) {
      sub = 'dress';
      confidence = 0.86;
    } else if (_looksLikeHat(desc) || _looksLikeCap(desc)) {
      sub = 'hat';
      confidence = 0.80;
    } else if (_looksLikeBag(desc)) {
      sub = 'bag';
      confidence = 0.82;
    } else if (_looksLikeFootwear(desc)) {
      sub = _footwearSub(desc, preferModel: true);
      confidence = 0.80;
    } else {
      return _classifyItem(fg, desc);
    }

    sub = _vetoImpossible(sub, desc);
    if (sub == ClothingCatalog.unknownType) {
      return (
        category: ClothingCategory.accessories,
        subcategory: ClothingCatalog.unknownType,
        confidence: confidence.clamp(0.10, 0.45),
      );
    }
    final normalized = ClothingCatalog.normalizeDetection(
      category: ClothingCategory.upperwear,
      subcategory: sub,
    );
    return (
      category: normalized.$1,
      subcategory: normalized.$2,
      confidence: confidence.clamp(0.40, 0.92),
    );
  }

  static String _vetoImpossible(String sub, ClothingDescriptor desc) {
    const tops = {
      'shirt',
      't-shirt',
      'hoodie',
      'jacket',
      'coat',
      'sweater',
    };
    const footwear = {
      'heels',
      'shoes',
      'sneakers',
      'flats',
      'boots',
      'sandals',
      'loafers',
    };
    if (sub == 'hat' &&
        _isBodyGarment(desc) &&
        !_looksLikeCap(desc) &&
        !_looksLikeHat(desc)) {
      return switch (desc.color) {
        'white' || 'cream' || 'blue' => 'shirt',
        'black' || 'navy' || 'grey' => 'jacket',
        _ => 't-shirt',
      };
    }
    if (tops.contains(sub) &&
        !_isBodyGarment(desc) &&
        !_explicitBagShape(desc) &&
        !_looksLikeTrousers(desc) &&
        !_looksLikeShorts(desc) &&
        !_looksLikeSkirt(desc) &&
        (_looksLikeHat(desc) || _looksLikeCap(desc) || _hatFromModel(desc)) &&
        !(desc.aspect > 1.50 && desc.cy > 0.48 && _looksLikeStiletto(desc))) {
      return 'hat';
    }
    if ((sub == 'hat' || tops.contains(sub) || footwear.contains(sub)) &&
        _looksLikeShorts(desc) &&
        desc.blobs >= 2) {
      return 'shorts';
    }
    if ((sub == 'hat' || tops.contains(sub) || footwear.contains(sub)) &&
        _looksLikeTrousers(desc)) {
      return desc.denim ? 'jeans' : 'trousers';
    }
    if (footwear.contains(sub) && _looksLikeBag(desc)) {
      return 'bag';
    }
    if (footwear.contains(sub) && _looksLikeSkirt(desc)) {
      return 'skirt';
    }
    if (sub == 'dress' && _looksLikeShorts(desc)) {
      return 'shorts';
    }
    if (sub == 'skirt' && _looksLikeShorts(desc)) {
      return 'shorts';
    }
    if (sub == 'dress' && _looksLikeTrousers(desc)) {
      return desc.denim ? 'jeans' : 'trousers';
    }
    if (sub == 'skirt' && _looksLikeTrousers(desc)) {
      return desc.denim ? 'jeans' : 'trousers';
    }
    if (sub == 'trousers' && _looksLikeShorts(desc)) {
      return 'shorts';
    }
    if (sub == 'shorts' && _looksLikeTrousers(desc)) {
      return desc.denim ? 'jeans' : 'trousers';
    }
    if (sub == 'dress' && _looksLikeSkirt(desc)) {
      return 'skirt';
    }
    if (footwear.contains(sub) &&
        (_looksLikeHat(desc) || _looksLikeCap(desc))) {
      return 'hat';
    }
    if (ClothingCatalog.dressNever.contains(sub) && _looksLikeDress(desc)) {
      return 'dress';
    }
    return sub;
  }

  /// Laid-out or hanging shirt / jacket / hoodie: a tall filled torso.
  static bool _isBodyGarment(ClothingDescriptor d) {
    return d.blobs <= 1 &&
        !d.lShape &&
        d.heightFrac > 0.48 &&
        d.occupancy > 0.28 &&
        d.aspect > 0.62 &&
        d.aspect < 1.45 &&
        d.flare < 1.20;
  }

  static bool _explicitBagShape(ClothingDescriptor d) {
    if (d.blobs > 1 || d.lShape) return false;
    // A near-round crown on a table is a cap, not a tote panel.
    if (d.aspect >= 0.98 &&
        d.aspect <= 1.22 &&
        d.heightFrac <= 0.52 &&
        d.upperMass >= 0.30) {
      return false;
    }
    return d.heightFrac >= 0.46 &&
        d.heightFrac <= 0.64 &&
        d.aspect >= 0.50 &&
        d.aspect <= 1.05 &&
        d.occupancy >= 0.12 &&
        d.occupancy < 0.52 &&
        d.cy >= 0.36 &&
        d.cy <= 0.64 &&
        d.flare < 1.12;
  }

  static bool _hatFromModel(ClothingDescriptor d) {
    if (_looksLikeTrousers(d) || _looksLikeShorts(d) || _looksLikeSkirt(d) || _looksLikeDress(d)) {
      return false;
    }
    if (d.topFrac > 0.18 && d.heightFrac > 0.52) return false;
    if (_isBodyGarment(d) ||
        _explicitBagShape(d) ||
        _looksLikeStiletto(d) ||
        _thickSoleNotVisor(d)) {
      return false;
    }
    if (d.heightFrac > 0.72) return false;
    if (d.aspect < 0.88 && d.heightFrac > 0.52 && d.upperMass < 0.30) {
      return false;
    }
    if (d.aspect > 1.70 && d.cy > 0.56 && d.upperMass < 0.30) return false;
    if (d.cy > 0.50 && d.flare > 1.10 && !d.lShape && d.fill > 0.70) {
      return false;
    }
    if (d.color == 'gold') return false;
    final hat = OutfitPartModel.predictAccessory(d.features);
    if (hat.label == 'hat' && hat.confidence >= 0.28) return true;
    final families = OutfitPartModel.rankedFamily(d.features);
    final accessory = families.where((e) => e.label == 'accessory');
    return accessory.isNotEmpty &&
        accessory.first.confidence >= 0.24 &&
        hat.label == 'hat';
  }

  static String? _exclusiveAccessory(ClothingDescriptor d) {
    if (_looksLikeBelt(d)) return 'belt';
    if (_looksLikeWatch(d)) return 'watch';
    if (_anyBag(d)) return null;
    if (_looksLikeJewelry(d)) return 'jewelry';
    return null;
  }

  static String? _accessoryGuess(ClothingDescriptor d) {
    if (_looksLikeBelt(d)) return 'belt';
    if (_looksLikeWatch(d)) return 'watch';
    if (_looksLikeSunglasses(d)) return 'sunglasses';
    if (_looksLikeTrousers(d) || _looksLikeShorts(d) || _looksLikeSkirt(d)) return null;
    if (_looksLikeHat(d) || _looksLikeCap(d)) return 'hat';
    if (_anyBag(d)) return 'bag';
    if (_looksLikeJewelry(d)) return 'jewelry';
    return null;
  }

  static bool _anyBag(ClothingDescriptor d) {
    return _looksLikeHandledBag(d) ||
        _looksLikeBackpack(d) ||
        _looksLikeClutch(d) ||
        _looksLikeProductBagPanel(d) ||
        _looksLikeBag(d) ||
        _explicitBagShape(d);
  }

  static bool _looksLikeBelt(ClothingDescriptor d) {
    return d.aspect > 2.2 &&
        d.heightFrac < 0.16 &&
        d.occupancy < 0.26 &&
        d.blobs <= 1 &&
        d.fill > 0.32;
  }

  static bool _looksLikeWatch(ClothingDescriptor d) {
    if (d.color == 'gold' || d.lShape || d.blobs > 1 || d.flare > 1.08) {
      return false;
    }
    final compact = d.aspect > 0.70 && d.aspect < 1.45;
    return compact &&
        d.occupancy >= 0.035 &&
        d.occupancy < 0.16 &&
        d.heightFrac >= 0.16 &&
        d.heightFrac < 0.40 &&
        d.fill > 0.40 &&
        d.hollow < 0.46 &&
        d.cy > 0.32 &&
        d.cy < 0.68 &&
        {'grey', 'black', 'navy'}.contains(d.color);
  }

  static bool _looksLikeJewelry(ClothingDescriptor d) {
    if (d.lShape) return false;
    if (_looksLikeHandledBag(d) ||
        _looksLikeBackpack(d) ||
        _looksLikeClutch(d) ||
        _explicitBagShape(d)) {
      return false;
    }
    // A filled bag body is not a pendant, even if it is small or metallic.
    if (d.fill > 0.40 &&
        d.occupancy >= 0.14 &&
        d.heightFrac >= 0.26 &&
        d.hollow < 0.32) {
      return false;
    }
    final gold = d.color == 'gold';
    final tiny = d.occupancy < 0.12 &&
        d.heightFrac < 0.34 &&
        d.blobs <= 1 &&
        d.aspect > 0.55 &&
        d.aspect < 1.55 &&
        !_looksLikeWatch(d);
    final goldSmall = gold &&
        d.heightFrac < 0.46 &&
        (d.occupancy < 0.20 ||
            (d.occupancy < 0.28 && (d.hollow > 0.32 || d.aspect < 1.55)));
    final goldPair = gold &&
        d.blobs >= 2 &&
        d.heightFrac < 0.42 &&
        d.occupancy < 0.24;
    final hollowRing = d.hollow > 0.42 &&
        d.occupancy < 0.20 &&
        d.heightFrac < 0.40 &&
        d.blobs <= 1 &&
        d.cy > 0.38 &&
        d.aspect < 1.55;
    final smallPair = d.blobs >= 2 &&
        d.occupancy < 0.11 &&
        d.heightFrac < 0.26 &&
        d.aspect < 2.00;
    return tiny || goldSmall || goldPair || hollowRing || smallPair;
  }

  static bool _looksLikeSunglasses(ClothingDescriptor d) {
    if (d.color == 'gold') return false;
    if (d.cy > 0.54) return false;
    if (d.heightFrac > 0.22 && d.fill > 0.40) return false;
    final frame = d.occupancy >= 0.03 &&
        d.occupancy < 0.28 &&
        d.heightFrac >= 0.08 &&
        d.heightFrac < 0.32 &&
        d.aspect > 1.50 &&
        d.aspect < 3.60 &&
        {'black', 'grey', 'brown', 'navy'}.contains(d.color);
    final lenses = d.hollow > 0.22 ||
        d.blobs >= 2 ||
        (d.aspect > 2.05 && d.heightFrac < 0.22);
    return frame && lenses;
  }

  static bool _looksLikeProductBagPanel(ClothingDescriptor d) {
    if (_looksLikeStiletto(d) || _looksLikeHat(d) || _looksLikeCap(d)) {
      return false;
    }
    if (d.blobs >= 3) return false;
    if (d.heightFrac < 0.28 || d.heightFrac > 0.72) return false;
    if (d.aspect < 0.62 || d.aspect > 1.48) return false;
    if (d.occupancy < 0.14 || d.occupancy > 0.58) return false;
    if (d.fill <= 0.30 || d.hollow > 0.38) return false;
    if (d.cy < 0.36 || d.cy > 0.66) return false;
    if (d.upperMass < 0.46) return false;
    if (d.flare >= 1.16) return false;
    if (d.flare >= 1.08 && d.upperMass < 0.50) return false;
    return true;
  }

  static bool _looksLikeBag(ClothingDescriptor d) {
    if (_looksLikeStiletto(d)) return false;
    if (_looksLikeHandledBag(d) ||
        _looksLikeBackpack(d) ||
        _looksLikeClutch(d) ||
        _looksLikeProductBagPanel(d)) {
      return true;
    }
    if (d.lShape || d.blobs >= 2) return false;
    if (_looksLikeHat(d) || _looksLikeCap(d)) return false;
    if (_skirtSilhouette(d)) return false;
    final compact = d.occupancy >= 0.12 &&
        d.occupancy < 0.52 &&
        d.heightFrac >= 0.26 &&
        d.heightFrac <= 0.64 &&
        d.aspect >= 0.50 &&
        d.aspect <= 1.40 &&
        d.fill > 0.30 &&
        d.hollow < 0.40 &&
        d.blobs <= 1 &&
        d.cy >= 0.34 &&
        d.cy <= 0.64;
    if (!compact) return false;
    if (d.heightFrac > 0.58 && d.aspect < 0.70 && d.flare > 1.10) return false;
    if (d.flare > 1.08 && d.lowerCenterFill > 0.40 && d.upperMass < 0.48) {
      return false;
    }
    if (d.aspect > 1.18 && (d.cy > 0.48 || d.hollow > 0.20)) return false;
    return true;
  }

  /// Tote / shoulder bag: filled body plus a handle, which looks L-shaped.
  static bool _looksLikeHandledBag(ClothingDescriptor d) {
    if (!d.lShape || d.blobs >= 3 || _looksLikeStiletto(d)) return false;
    if (d.flare >= 1.14) return false;
    if (d.aspect > 1.45) return false;
    if (d.cy > 0.66) return false;
    return d.occupancy >= 0.11 &&
        d.occupancy < 0.62 &&
        d.heightFrac >= 0.28 &&
        d.heightFrac <= 0.80 &&
        d.aspect >= 0.50 &&
        d.aspect <= 1.45 &&
        d.fill > 0.28 &&
        d.cy >= 0.34 &&
        d.cy <= 0.66 &&
        d.lowerCenterFill > 0.28;
  }

  static bool _looksLikeBackpack(ClothingDescriptor d) {
    if (d.blobs >= 2 || d.denim || _looksLikeStiletto(d)) return false;
    if (_looksLikeHat(d) || _looksLikeCap(d)) return false;
    return d.heightFrac >= 0.48 &&
        d.heightFrac <= 0.68 &&
        d.aspect >= 0.58 &&
        d.aspect <= 0.90 &&
        d.occupancy >= 0.14 &&
        d.occupancy < 0.40 &&
        d.fill > 0.32 &&
        d.cy >= 0.38 &&
        d.cy <= 0.58 &&
        d.flare < 1.16;
  }

  static bool _looksLikeClutch(ClothingDescriptor d) {
    if (d.lShape || d.blobs >= 2 || _looksLikeStiletto(d) || d.flare >= 1.10) {
      return false;
    }
    final classic = d.aspect > 1.15 &&
        d.aspect < 2.15 &&
        d.heightFrac >= 0.16 &&
        d.heightFrac <= 0.46 &&
        d.occupancy >= 0.10 &&
        d.occupancy < 0.28 &&
        d.fill > 0.35 &&
        d.cy >= 0.34 &&
        d.cy <= 0.62;
    final onSurface = d.aspect > 1.20 &&
        d.aspect < 2.30 &&
        d.heightFrac >= 0.16 &&
        d.heightFrac <= 0.46 &&
        d.occupancy >= 0.12 &&
        d.occupancy < 0.40 &&
        d.fill > 0.50 &&
        d.hollow < 0.16 &&
        d.cy >= 0.62 &&
        d.cy <= 0.76;
    return classic || onSurface;
  }

  static bool _looksLikeSkirt(ClothingDescriptor d) {
    if (_looksLikeShorts(d) || _looksLikeTrousers(d)) return false;
    if (_looksLikeClutch(d) || _looksLikeProductBagPanel(d)) return false;
    if (_looksLikeHandledBag(d) && d.flare < 1.08) return false;
    if (_looksLikeBackpack(d) && d.flare < 1.08) return false;
    return _skirtSilhouette(d);
  }

  /// Flared or mini lower panel, including a long skirt that starts below the shoulders.
  static bool _skirtSilhouette(ClothingDescriptor d) {
    if (d.blobs >= 2 || _looksLikeStiletto(d)) return false;
    if (_looksLikeHat(d) || _looksLikeCap(d) || _looksLikeTopDownCap(d)) {
      return false;
    }
    if (d.heightFrac < 0.26 || d.heightFrac > 0.94) return false;
    if (d.aspect < 0.48 || d.aspect > 1.55) return false;
    if (d.occupancy < 0.10 || d.occupancy > 0.78) return false;
    if (d.cy < 0.36 || d.cy > 0.72) return false;
    if (d.fill <= 0.22) return false;
    final hanging = d.topFrac > 0.15;
    final flared = d.flare >= 1.04 && d.lowerCenterFill > 0.36;
    final mini = d.heightFrac <= 0.52 &&
        d.aspect > 0.70 &&
        d.fill > 0.26 &&
        d.flare >= 1.04 &&
        d.upperMass < 0.50;
    final longSkirt = hanging &&
        d.heightFrac >= 0.55 &&
        d.aspect < 0.98 &&
        flared &&
        d.upperMass < 0.44;
    if (longSkirt) return true;
    if (d.heightFrac > 0.72 && !hanging) return false;
    return (flared || mini) && d.upperMass < 0.52;
  }

  static bool _bagLikeNotDress(ClothingDescriptor d) {
    return d.blobs <= 1 &&
        d.heightFrac < 0.62 &&
        d.occupancy < 0.48 &&
        d.aspect > 0.52 &&
        d.aspect < 1.35 &&
        d.flare < 1.12 &&
        d.cy > 0.36 &&
        d.cy < 0.64;
  }

  static bool _looksLikeCloseupShoe(ClothingDescriptor d) {
    if (_looksLikeHat(d) ||
        _looksLikeCap(d) ||
        _hatLikeNotShoe(d) ||
        _looksLikeJewelry(d) ||
        _looksLikeSunglasses(d) ||
        _looksLikeBag(d) ||
        _looksLikeSkirt(d)) {
      return false;
    }
    if (d.heightFrac > 0.76 && d.aspect < 0.88) return false;
    final wide = d.aspect > 1.18;
    final pair = d.blobs >= 2 && d.heightFrac < 0.55 && d.occupancy < 0.55;
    final side = wide &&
        d.heightFrac >= 0.16 &&
        d.heightFrac < 0.72 &&
        d.occupancy >= 0.10 &&
        d.occupancy < 0.74;
    return pair ||
        (side &&
            (d.hollow > 0.18 ||
                d.cy > 0.44 ||
                d.lShape ||
                d.heightFrac < 0.58));
  }

  static bool _looksLikeJeans(ClothingDescriptor d) {
    return d.denim && _looksLikeTrousers(d);
  }

  /// Two short leg tubes — shorts, including loose/Bermuda styles.
  static bool _looksLikeShorts(ClothingDescriptor d) {
    if (d.lShape || _looksLikeStiletto(d) || d.color == 'gold') return false;
    // A table-top cap is one filled oval, not two legs.
    if (d.blobs <= 1 &&
        d.heightFrac <= 0.48 &&
        d.aspect >= 0.82 &&
        d.aspect <= 1.58 &&
        d.upperMass >= 0.28) {
      return false;
    }
    if (d.heightFrac < 0.22 || d.heightFrac > 0.50) return false;
    if (d.aspect < 0.48 || d.aspect > 1.90) return false;
    if (d.occupancy < 0.10 || d.occupancy > 0.68) return false;
    if (d.cy > 0.62 && d.heightFrac < 0.40 && d.occupancy < 0.38) return false;
    if (d.topFrac < 0.08 && d.heightFrac > 0.46 && d.lowerCenterFill > 0.50) {
      return false;
    }
    final twoLegs = d.blobs == 2 &&
        d.occupancy >= 0.12 &&
        d.lowerCenterFill < 0.72;
    final crotchGap = d.blobs <= 2 &&
        d.lowerCenterFill < 0.34 &&
        d.cy > 0.40 &&
        d.heightFrac >= 0.26;
    return twoLegs || crotchGap;
  }

  /// Two leg tubes or a crotch gap — pants, including wide-leg / palazzo.
  static bool _looksLikeTrousers(ClothingDescriptor d) {
    if (d.lShape || _looksLikeStiletto(d) || d.color == 'gold') return false;
    if (d.heightFrac < 0.46 || d.heightFrac > 0.96) return false;
    if (d.aspect < 0.38 || d.aspect > 1.10) return false;
    if (d.occupancy < 0.12 || d.occupancy > 0.82) return false;
    if (d.topFrac < 0.07 && d.heightFrac > 0.80 && d.lowerCenterFill > 0.50) {
      return false;
    }
    final twoLegs = d.blobs == 2 &&
        d.heightFrac >= 0.52 &&
        d.occupancy >= 0.14 &&
        d.lowerCenterFill < 0.70;
    // Skirts/dresses fill the hem; a true crotch stays open in the lower center.
    final crotchGap = d.blobs <= 2 &&
        d.lowerCenterFill < 0.32 &&
        d.heightFrac > 0.50 &&
        d.cy > 0.44;
    final palazzo = d.blobs <= 2 &&
        d.topFrac > 0.14 &&
        d.heightFrac > 0.52 &&
        d.lowerCenterFill < 0.55 &&
        d.flare >= 1.04;
    // Legs laid close together look like one panel (no open crotch).
    final pressed = !d.lShape &&
        d.blobs <= 2 &&
        d.heightFrac >= 0.66 &&
        d.aspect >= 0.34 &&
        d.aspect <= 0.80 &&
        d.topFrac >= 0.06 &&
        d.cy > 0.48 &&
        d.flare < 1.10 &&
        d.occupancy < 0.42 &&
        d.upperMass > 0.18;
    return twoLegs || crotchGap || palazzo || pressed;
  }

  static bool _looksLikeFootwear(ClothingDescriptor d) {
    if (_accessoryGuess(d) != null) return false;
    if (_looksLikeBag(d) ||
        _looksLikeHandledBag(d) ||
        _looksLikeClutch(d) ||
        _looksLikeBackpack(d)) {
      return false;
    }
    if (_looksLikeCap(d) ||
        _looksLikeHat(d) ||
        _hatLikeNotShoe(d) ||
        _looksLikeTrousers(d) ||
        _looksLikeShorts(d) ||
        _looksLikeSkirt(d)) {
      return false;
    }
    if (_looksLikeCloseupShoe(d)) return true;
    if (d.blobs <= 1 &&
        !d.lShape &&
        d.heightFrac > 0.56 &&
        d.aspect < 0.95) {
      return false;
    }
    if (d.lShape && d.heightFrac > 0.22 && d.occupancy < 0.50) {
      if (_looksLikeStiletto(d)) return true;
      return false;
    }
    if (d.blobs >= 2 &&
        d.occupancy >= 0.08 &&
        d.occupancy < 0.52 &&
        d.heightFrac < 0.62 &&
        (d.aspect > 0.88 || d.cy > 0.54 || d.heightFrac < 0.48) &&
        !(d.color == 'gold' && d.occupancy < 0.20)) {
      return true;
    }
    if (d.cy > 0.56 &&
        d.heightFrac < 0.62 &&
        d.occupancy < 0.42 &&
        d.aspect > 0.80) {
      return true;
    }
    if (d.hollow > 0.30 &&
        d.heightFrac < 0.70 &&
        d.occupancy < 0.42 &&
        d.aspect > 0.85 &&
        d.color != 'gold') {
      return true;
    }
    if (d.aspect > 1.12 &&
        d.heightFrac >= 0.16 &&
        d.heightFrac < 0.64 &&
        d.occupancy >= 0.10 &&
        d.occupancy < 0.70) {
      return true;
    }
    if (d.heightFrac > 0.38 &&
        d.heightFrac < 0.76 &&
        d.occupancy < 0.38 &&
        d.lowerCenterFill < 0.40 &&
        d.blobs <= 2) {
      return true;
    }
    return false;
  }

  static bool _looksLikeDress(ClothingDescriptor d) {
    if (d.blobs >= 2 ||
        d.lShape ||
        _looksLikeHat(d) ||
        _looksLikeBag(d) ||
        _looksLikeTrousers(d) ||
        _looksLikeShorts(d) ||
        _looksLikeSkirt(d)) {
      return false;
    }
    // One-piece starts near the top of the frame (shoulders). A long skirt starts at the waist.
    if (d.topFrac > 0.16) return false;
    if (d.heightFrac < 0.72 && d.flare > 1.06) return false;
    if (d.heightFrac <= 0.46 || d.aspect >= 1.02 || d.occupancy <= 0.14) {
      return false;
    }
    if (d.cy >= 0.68) return false;
    if (d.lowerCenterFill < 0.42) return false;
    if (d.denim && d.flare < 1.10) return false;
    final flared = d.flare > 1.08;
    final column = d.heightFrac > 0.58 &&
        d.aspect < 0.86 &&
        d.lowerCenterFill > 0.42 &&
        d.blobs <= 1;
    return (flared || column) && d.upperMass > 0.16;
  }

  static bool _looksLikeHat(ClothingDescriptor d) {
    if (_explicitBagShape(d) || _looksLikeStiletto(d)) return false;
    if (_looksLikeTopDownCap(d)) return true;
    if (d.color == 'gold') return false;
    if (d.blobs >= 2) return false;
    if (d.topFrac > 0.18 && d.heightFrac > 0.52) return false;
    if (_looksLikeTrousers(d) || _looksLikeShorts(d)) return false;
    if (_thickSoleNotVisor(d)) return false;
    // Side-on shoe: wide block, no visor, mass sits mid/low.
    if (d.aspect > 1.40 && !d.lShape && d.cy > 0.48) return false;
    if (!d.lShape && d.upperMass < 0.32 && d.cy > 0.50) return false;
    if (d.aspect > 1.75 && d.cy > 0.58 && d.upperMass < 0.30) return false;
    if (d.occupancy < 0.05 || d.occupancy > 0.72) return false;
    if (d.heightFrac < 0.12 || d.heightFrac > 0.72) return false;
    if (d.aspect < 0.68 || d.aspect > 3.20) return false;
    if (d.cy > 0.64) return false;
    if (d.cy > 0.50 && d.flare > 1.10 && !d.lShape && d.fill > 0.70) {
      return false;
    }
    if (d.fill <= 0.20) return false;
    final brim = d.aspect > 1.22 || d.lShape;
    final shortCap = d.heightFrac < 0.56 && d.aspect >= 0.78 && d.aspect <= 1.75;
    final closeUpCap = d.heightFrac <= 0.72 &&
        d.occupancy < 0.68 &&
        (brim || d.lShape || shortCap);
    final crown = d.upperMass > 0.30 ||
        d.cy < 0.48 ||
        (d.lShape && d.upperMass > 0.26);
    return crown && closeUpCap;
  }

  /// Overhead / three-quarter baseball or newsboy cap on a table.
  static bool _looksLikeTopDownCap(ClothingDescriptor d) {
    if (d.blobs >= 2 || _looksLikeStiletto(d)) return false;
    if (d.heightFrac < 0.16 || d.heightFrac > 0.52) return false;
    if (d.aspect < 0.88 || d.aspect > 1.50) return false;
    if (d.occupancy < 0.06 || d.occupancy > 0.32) return false;
    if (d.fill <= 0.24 || d.hollow > 0.52) return false;
    if (d.cy < 0.26 || d.cy > 0.60) return false;
    if (d.flare >= 1.10) return false;
    // Tall filled panels are bags, not a flatter crown on a table.
    if (d.heightFrac >= 0.46 && d.aspect < 1.02) return false;
    if (d.heightFrac > 0.50 && d.topFrac > 0.16) return false;
    if (_looksLikeHandledBag(d)) return false;
    return d.upperMass >= 0.30;
  }

  /// Baseball cap / visor: L-shape from the brim, crown mass stays high.
  static bool _looksLikeCap(ClothingDescriptor d) {
    if (_explicitBagShape(d) || _looksLikeStiletto(d)) return false;
    if (_looksLikeTopDownCap(d)) return true;
    if (d.blobs >= 2 || d.color == 'gold' || _looksLikeStiletto(d)) {
      return false;
    }
    if (d.topFrac > 0.18 && d.heightFrac > 0.52) return false;
    if (_looksLikeTrousers(d) || _looksLikeShorts(d)) return false;
    if (_thickSoleNotVisor(d)) return false;
    if (d.aspect > 1.40 && !d.lShape && d.cy > 0.48) return false;
    if (d.cy > 0.50 && d.flare > 1.10 && !d.lShape && d.fill > 0.70) {
      return false;
    }
    final visor = d.lShape || (d.aspect > 1.22 && d.upperMass >= 0.30);
    final crownHigh = d.upperMass >= 0.30 || d.cy <= 0.52;
    return visor &&
        crownHigh &&
        d.heightFrac >= 0.16 &&
        d.heightFrac <= 0.72 &&
        d.occupancy >= 0.06 &&
        d.occupancy <= 0.64 &&
        d.cy <= 0.58 &&
        d.fill > 0.22;
  }

  /// Stiletto: thin vertical stem plus a sole sitting low in the frame.
  static bool _looksLikeStiletto(ClothingDescriptor d) {
    return d.lShape &&
        d.cy > 0.54 &&
        d.upperMass < 0.34 &&
        d.heightFrac > 0.36 &&
        d.aspect >= 0.55 &&
        d.aspect < 1.45 &&
        d.occupancy < 0.18 &&
        d.fill < 0.42;
  }

  /// Close-up shoe: bulky sole in the lower half, not a thin cap visor.
  static bool _thickSoleNotVisor(ClothingDescriptor d) {
    return d.cy > 0.50 &&
        d.lowerCenterFill > 0.50 &&
        d.flare > 1.06 &&
        d.occupancy > 0.12 &&
        d.aspect > 1.12 &&
        d.heightFrac < 0.48 &&
        d.upperMass < 0.32;
  }

  static bool _hatLikeNotShoe(ClothingDescriptor d) {
    if (d.blobs >= 2 || _looksLikeStiletto(d) || _thickSoleNotVisor(d)) {
      return false;
    }
    if (_looksLikeCap(d) || _looksLikeHat(d)) return true;
    if (d.upperMass > 0.40 && d.cy < 0.48 && d.blobs <= 1) return true;
    if (d.cy < 0.42 &&
        d.heightFrac < 0.50 &&
        d.occupancy < 0.45 &&
        d.blobs <= 1) {
      return true;
    }
    return false;
  }

  static String _footwearSub(
    ClothingDescriptor desc, {
    bool preferModel = false,
  }) {
    if (desc.lShape &&
        desc.heightFrac > (preferModel ? 0.38 : 0.26) &&
        desc.cy > 0.50 &&
        _looksLikeStiletto(desc) &&
        !_hatLikeNotShoe(desc)) {
      return 'heels';
    }
    if (!desc.lShape &&
        desc.heightFrac < 0.12 &&
        desc.aspect > 1.25 &&
        desc.fill > 0.28) {
      return 'flats';
    }
    if ({'white', 'grey', 'cream'}.contains(desc.color) && desc.blobs >= 2) {
      return 'sneakers';
    }
    final pred = OutfitPartModel.predictFootwear(desc.features);
    if (preferModel && pred.confidence >= 0.30) return pred.label;
    if (pred.confidence >= 0.32) return pred.label;
    if (desc.hollow > 0.24 &&
        desc.heightFrac >= 0.22 &&
        desc.heightFrac < 0.50 &&
        desc.fill > 0.34) {
      return 'sneakers';
    }
    if ((desc.color == 'beige' || desc.color == 'brown') &&
        desc.fill < 0.42 &&
        desc.heightFrac < 0.28) {
      return 'sandals';
    }
    return 'shoes';
  }

  static ({String sub, double confidence})? _geometricGuess(
    ClothingDescriptor desc,
    _FgStats fg,
  ) {
    final accessory = _accessoryGuess(desc);
    if (accessory != null) {
      return (sub: accessory, confidence: 0.86);
    }

    if (_looksLikeShorts(desc)) {
      return (sub: 'shorts', confidence: 0.88);
    }

    if (_looksLikeTrousers(desc)) {
      return (sub: desc.denim ? 'jeans' : 'trousers', confidence: 0.88);
    }

    if (_looksLikeSkirt(desc)) {
      return (sub: 'skirt', confidence: 0.88);
    }

    if (desc.lShape && desc.heightFrac > 0.26 && desc.occupancy < 0.46) {
      if (_looksLikeBag(desc)) {
        return (sub: 'bag', confidence: 0.90);
      }
      if (_looksLikeSkirt(desc)) {
        return (sub: 'skirt', confidence: 0.88);
      }
      if (_looksLikeCap(desc) || _looksLikeHat(desc) || _hatLikeNotShoe(desc)) {
        return (sub: 'hat', confidence: 0.90);
      }
      if (_looksLikeStiletto(desc)) {
        return (sub: 'heels', confidence: 0.88);
      }
    }

    if (desc.blobs >= 2 &&
        desc.occupancy >= 0.08 &&
        desc.occupancy < 0.52 &&
        desc.heightFrac >= 0.14 &&
        desc.heightFrac < 0.62 &&
        (desc.aspect > 0.88 || desc.cy > 0.54 || desc.heightFrac < 0.48)) {
      return (sub: _footwearSub(desc), confidence: 0.86);
    }

    if (_looksLikeDress(desc)) {
      return (sub: 'dress', confidence: 0.88);
    }

    if (desc.heightFrac > 0.52 &&
        desc.aspect < 0.92 &&
        desc.upperMass > 0.22 &&
        !_looksLikeFootwear(desc)) {
      if (desc.denim &&
          desc.flare < 1.14 &&
          (desc.color == 'blue' ||
              desc.blobs >= 2 ||
              desc.lowerCenterFill < 0.50)) {
        return (sub: 'jeans', confidence: 0.84);
      }
    }

    if (desc.denim &&
        desc.heightFrac > 0.42 &&
        desc.aspect < 1.10 &&
        (desc.color == 'blue' ||
            desc.blobs >= 2 ||
            desc.lowerCenterFill < 0.50)) {
      return (sub: 'jeans', confidence: 0.78);
    }

    return null;
  }

  static img.Image _keepAspect(img.Image src) {
    final long = max(src.width, src.height);
    final scale = _size / long;
    return img.copyResize(
      src,
      width: max(48, (src.width * scale).round()),
      height: max(48, (src.height * scale).round()),
    );
  }

  static _FgStats _foreground(img.Image image) {
    final w = image.width;
    final h = image.height;
    final corners = <List<int>>[];
    void corner(int x0, int y0, int x1, int y1) {
      for (var y = y0; y < y1; y += 2) {
        for (var x = x0; x < x1; x += 2) {
          final p = image.getPixel(x.clamp(0, w - 1), y.clamp(0, h - 1));
          corners.add([p.r.toInt(), p.g.toInt(), p.b.toInt()]);
        }
      }
    }

    final cw = max(6, w ~/ 16);
    final ch = max(6, h ~/ 16);
    corner(0, 0, cw, ch);
    corner(w - cw, 0, w, ch);
    corner(0, h - ch, cw, h);
    corner(w - cw, h - ch, w, h);
    final bg = _mean(corners.isEmpty ? [[240, 240, 240]] : corners);
    var bgSpread = 0.0;
    for (final s in corners) {
      bgSpread += _dist(
        [s[0].toDouble(), s[1].toDouble(), s[2].toDouble()],
        bg,
      );
    }
    bgSpread = corners.isEmpty ? 18 : bgSpread / corners.length;
    var threshold = max(26.0, bgSpread * 1.7 + 12);
    final centerSamples = <List<int>>[];
    for (var y = (h * 0.30).round(); y < (h * 0.70).round(); y += 3) {
      for (var x = (w * 0.32).round(); x < (w * 0.68).round(); x += 3) {
        final p = image.getPixel(x, y);
        centerSamples.add([p.r.toInt(), p.g.toInt(), p.b.toInt()]);
      }
    }
    if (centerSamples.isNotEmpty) {
      final centerGap = _dist(_mean(centerSamples), bg);
      if (centerGap > 8 && centerGap < threshold * 1.2) {
        threshold = max(10.0, centerGap * 0.55);
      }
    }

    var raw = _pixelsUnlikeBackground(image, bg, threshold);
    if (raw.length < 80) {
      raw = _pixelsUnlikeBackground(image, bg, 11);
    }

    if (raw.length < 80) {
      raw = [];
      final x0 = (w * 0.12).round();
      final x1 = w - x0;
      final y0 = (h * 0.08).round();
      final y1 = h - y0;
      for (var y = y0; y < y1; y++) {
        for (var x = x0; x < x1; x++) {
          final p = image.getPixel(x, y);
          raw.add(_Pix(x, y, p.r.toInt(), p.g.toInt(), p.b.toInt()));
        }
      }
    }

    if (raw.isEmpty) {
      final bgName = _nameFromRgb(bg[0].round(), bg[1].round(), bg[2].round());
      return _FgStats.empty(
        assumedFillColor: bgName,
        backgroundRgb: bg,
      );
    }

    final noSkin = raw.where((p) => !_isGarmentSkin(p.r, p.g, p.b)).toList();
    final skinN = raw.length - noSkin.length;
    final leftoverOcc = noSkin.length / (w * h);
    final cutSkin = noSkin.length >= 70 &&
        noSkin.length < raw.length * 0.72 &&
        leftoverOcc < 0.30;
    final used = cutSkin ? noSkin : raw;
    final colorPixels = noSkin.length >= 80 ? noSkin : used;
    final bgName = _nameFromRgb(bg[0].round(), bg[1].round(), bg[2].round());

    return _statsFromPixels(
      used,
      width: w,
      height: h,
      colorPixels: colorPixels,
      skinRatio: raw.isEmpty ? 0 : skinN / raw.length,
      backgroundRgb: bg,
      backgroundName: bgName,
    );
  }

  static List<_Pix> _pixelsUnlikeBackground(
    img.Image image,
    List<double> bg,
    double threshold,
  ) {
    final w = image.width;
    final h = image.height;
    final likeBg = List.generate(h, (_) => List.filled(w, false));
    for (var y = 0; y < h; y++) {
      for (var x = 0; x < w; x++) {
        final p = image.getPixel(x, y);
        likeBg[y][x] = _dist(
              [p.r.toDouble(), p.g.toDouble(), p.b.toDouble()],
              bg,
            ) <
            threshold;
      }
    }
    final flooded = List.generate(h, (_) => List.filled(w, false));
    final stack = <(int, int)>[];
    void seed(int x, int y) {
      if (x < 0 || y < 0 || x >= w || y >= h) return;
      if (flooded[y][x] || !likeBg[y][x]) return;
      flooded[y][x] = true;
      stack.add((x, y));
    }

    for (var x = 0; x < w; x++) {
      seed(x, 0);
      seed(x, h - 1);
    }
    for (var y = 0; y < h; y++) {
      seed(0, y);
      seed(w - 1, y);
    }
    while (stack.isNotEmpty) {
      final cur = stack.removeLast();
      seed(cur.$1 + 1, cur.$2);
      seed(cur.$1 - 1, cur.$2);
      seed(cur.$1, cur.$2 + 1);
      seed(cur.$1, cur.$2 - 1);
    }

    final raw = <_Pix>[];
    for (var y = 0; y < h; y++) {
      for (var x = 0; x < w; x++) {
        if (flooded[y][x]) continue;
        final p = image.getPixel(x, y);
        raw.add(_Pix(x, y, p.r.toInt(), p.g.toInt(), p.b.toInt()));
      }
    }
    return raw;
  }

  static _FgStats _statsFromPixels(
    List<_Pix> pixels, {
    required int width,
    required int height,
    required List<_Pix> colorPixels,
    required double skinRatio,
    required List<double> backgroundRgb,
    required String backgroundName,
  }) {
    var minX = width, minY = height, maxX = 0, maxY = 0;
    var sx = 0.0, sy = 0.0;
    final mask = List.generate(height, (_) => List.filled(width, false));
    for (final p in pixels) {
      if (p.x < minX) minX = p.x;
      if (p.y < minY) minY = p.y;
      if (p.x > maxX) maxX = p.x;
      if (p.y > maxY) maxY = p.y;
      sx += p.x;
      sy += p.y;
      mask[p.y][p.x] = true;
    }
    final bw = max(1, maxX - minX);
    final bh = max(1, maxY - minY);
    var edge = 0;
    for (final p in pixels) {
      final fringe = p.x == 0 ||
          p.y == 0 ||
          p.x == width - 1 ||
          p.y == height - 1 ||
          !mask[p.y][max(0, p.x - 1)] ||
          !mask[p.y][min(width - 1, p.x + 1)] ||
          !mask[max(0, p.y - 1)][p.x] ||
          !mask[min(height - 1, p.y + 1)][p.x];
      if (fringe) edge++;
    }
    final insetX = max(1, (bw * 0.28).round());
    final insetY = max(1, (bh * 0.28).round());
    final ix0 = minX + insetX;
    final iy0 = minY + insetY;
    final ix1 = maxX - insetX;
    final iy1 = maxY - insetY;
    var inner = 0;
    var innerArea = 0;
    if (ix1 > ix0 && iy1 > iy0) {
      for (var y = iy0; y <= iy1; y++) {
        for (var x = ix0; x <= ix1; x++) {
          innerArea++;
          if (mask[y][x]) inner++;
        }
      }
    }
    final innerFill = innerArea == 0 ? 1.0 : inner / innerArea;
    var top = 0, bot = 0, upper = 0;
    final topXs = <int>{};
    final botXs = <int>{};
    var lowerCenter = 0;
    var lowerCenterArea = 0;
    final midL = minX + (bw * 0.35).round();
    final midR = minX + (bw * 0.65).round();
    final lowY = minY + (bh * 0.50).round();
    for (var y = lowY; y <= maxY; y++) {
      for (var x = midL; x <= midR; x++) {
        lowerCenterArea++;
        if (mask[y][x]) lowerCenter++;
      }
    }
    for (final p in pixels) {
      if (p.y < minY + bh * 0.45) {
        top++;
      } else {
        bot++;
      }
      if (p.y < minY + bh * 0.40) {
        upper++;
        topXs.add(p.x);
      }
      if (p.y > minY + bh * 0.68) {
        botXs.add(p.x);
      }
    }
    final q = [0, 0, 0, 0];
    final midX = (minX + maxX) / 2;
    final midY = (minY + maxY) / 2;
    for (final p in pixels) {
      q[(p.y > midY ? 2 : 0) + (p.x > midX ? 1 : 0)]++;
    }
    final n = pixels.length;
    final emptyQ = q.where((c) => c < n * 0.12).length;
    final blobs = _blobStats(mask);
    final grid9 = List<double>.filled(9, 0);
    final gridN = List<int>.filled(9, 0);
    final bands4 = List<double>.filled(4, 0);
    final bandN = List<int>.filled(4, 0);
    for (var y = minY; y <= maxY; y++) {
      final gy = ((y - minY) * 3 / bh).floor().clamp(0, 2);
      final band = ((y - minY) * 4 / bh).floor().clamp(0, 3);
      for (var x = minX; x <= maxX; x++) {
        final gx = ((x - minX) * 3 / bw).floor().clamp(0, 2);
        final gi = gy * 3 + gx;
        gridN[gi]++;
        bandN[band]++;
        if (mask[y][x]) {
          grid9[gi]++;
          bands4[band]++;
        }
      }
    }
    for (var i = 0; i < 9; i++) {
      grid9[i] = gridN[i] == 0 ? 0 : grid9[i] / gridN[i];
    }
    for (var i = 0; i < 4; i++) {
      bands4[i] = bandN[i] == 0 ? 0 : bands4[i] / bandN[i];
    }
    final hues6 = List<double>.filled(6, 0);
    if (colorPixels.isNotEmpty) {
      for (final p in colorPixels) {
        final hsv = _hsv(p.r, p.g, p.b);
        if (hsv.$2 < 0.10) continue;
        hues6[(hsv.$1 / 60).floor().clamp(0, 5)]++;
      }
      final hueTot = hues6.fold<double>(0, (a, b) => a + b);
      if (hueTot > 0) {
        for (var i = 0; i < 6; i++) {
          hues6[i] /= hueTot;
        }
      }
    }
    return _FgStats(
      occupancy: pixels.length / (width * height),
      aspect: bw / bh,
      fill: pixels.length / (bw * bh),
      cx: (sx / pixels.length) / width,
      cy: (sy / pixels.length) / height,
      heightFrac: bh / height,
      topFrac: minY / height,
      lShape: emptyQ >= 1 && q.any((c) => c > n * 0.25),
      flare: topXs.isEmpty ? 1 : botXs.length / topXs.length,
      upperMass: pixels.isEmpty ? 0 : upper / pixels.length,
      lowerCenterFill:
          lowerCenterArea == 0 ? 1 : lowerCenter / lowerCenterArea,
      edgeRatio: edge / pixels.length,
      hollow: (1 - innerFill).clamp(0.0, 1.0),
      blobs: blobs.count,
      largestBlob: blobs.largest,
      skinRatio: skinRatio,
      topHeavy: top > bot,
      colorPixels: _garmentColorSamples(
        colorPixels,
        minX: minX,
        minY: minY,
        maxX: maxX,
        maxY: maxY,
        backgroundRgb: backgroundRgb,
      ),
      assumedFillColor: null,
      backgroundName: backgroundName,
      backgroundRgb: backgroundRgb,
      grid9: grid9,
      bands4: bands4,
      hues6: hues6,
    );
  }

  static ({int count, int largest}) _blobStats(List<List<bool>> mask) {
    const step = 3;
    final mh = mask.length;
    final mw = mask[0].length;
    final h = max(1, mh ~/ step);
    final w = max(1, mw ~/ step);
    final small = List.generate(h, (_) => List.filled(w, false));
    for (var y = 0; y < h; y++) {
      for (var x = 0; x < w; x++) {
        final iy = min(mh - 1, y * step);
        final ix = min(mw - 1, x * step);
        small[y][x] = mask[iy][ix];
      }
    }
    final seen = List.generate(h, (_) => List.filled(w, false));
    var count = 0;
    var largest = 0;
    for (var y = 0; y < h; y++) {
      for (var x = 0; x < w; x++) {
        if (!small[y][x] || seen[y][x]) continue;
        var size = 0;
        final stack = <(int, int)>[(x, y)];
        seen[y][x] = true;
        while (stack.isNotEmpty) {
          final cur = stack.removeLast();
          size++;
          const dirs = [(1, 0), (-1, 0), (0, 1), (0, -1)];
          for (final d in dirs) {
            final nx = cur.$1 + d.$1;
            final ny = cur.$2 + d.$2;
            if (nx < 0 || ny < 0 || nx >= w || ny >= h) continue;
            if (!small[ny][nx] || seen[ny][nx]) continue;
            seen[ny][nx] = true;
            stack.add((nx, ny));
          }
        }
        if (size >= 8) {
          count++;
          if (size > largest) largest = size;
        }
      }
    }
    return (count: max(1, count), largest: largest);
  }

  static const _studioNeutrals = {'white', 'cream', 'grey', 'beige'};

  static List<List<int>> _garmentColorSamples(
    List<_Pix> pixels, {
    required int minX,
    required int minY,
    required int maxX,
    required int maxY,
    required List<double> backgroundRgb,
  }) {
    final bw = max(1, maxX - minX);
    final bh = max(1, maxY - minY);
    final insetX = max(1, (bw * 0.16).round());
    final insetY = max(1, (bh * 0.16).round());
    final interior = <List<int>>[];
    final all = <List<int>>[];
    for (final p in pixels) {
      all.add([p.r, p.g, p.b]);
      if (p.x < minX + insetX || p.x > maxX - insetX) continue;
      if (p.y < minY + insetY || p.y > maxY - insetY) continue;
      interior.add([p.r, p.g, p.b]);
    }
    var sampled = interior.length >= 40 ? interior : all;
    final unlikeBg = [
      for (final p in sampled)
        if (_dist(
              [p[0].toDouble(), p[1].toDouble(), p[2].toDouble()],
              backgroundRgb,
            ) >
            26)
          p,
    ];
    if (unlikeBg.length >= max(30, (sampled.length * 0.10).round())) {
      sampled = unlikeBg;
    }
    return sampled;
  }

  static ({String primary, String? secondary}) _colorFromPixels(
    List<List<int>> pixels, {
    String? backgroundName,
    List<double>? backgroundRgb,
  }) {
    if (pixels.isEmpty) {
      return (primary: backgroundName ?? 'black', secondary: null);
    }
    var sampled = pixels;
    if (backgroundRgb != null) {
      final unlikeBg = [
        for (final p in pixels)
          if (_dist(
                [p[0].toDouble(), p[1].toDouble(), p[2].toDouble()],
                backgroundRgb,
              ) >
              28)
            p,
      ];
      if (unlikeBg.length >= max(30, (pixels.length * 0.10).round())) {
        sampled = unlikeBg;
      }
    }
    final counts = <String, int>{};
    for (final p in sampled) {
      final name = _nameFromRgb(p[0], p[1], p[2]);
      counts[name] = (counts[name] ?? 0) + 1;
    }
    void merge(String from, String into) {
      if (!counts.containsKey(from)) return;
      counts[into] = (counts[into] ?? 0) + counts[from]!;
      counts.remove(from);
    }

    final n = sampled.length;
    final gold = counts['gold'] ?? 0;
    final yellow = counts['yellow'] ?? 0;
    final brown = counts['brown'] ?? 0;
    if (gold + yellow > brown * 0.7 && gold + yellow > n * 0.12) {
      merge('yellow', 'gold');
      merge('brown', 'gold');
    }
    final blue = counts['blue'] ?? 0;
    final navy = counts['navy'] ?? 0;
    final black = counts['black'] ?? 0;
    if (blue + navy > n * 0.22 && black < (blue + navy) * 1.15) {
      if (navy >= blue) {
        merge('black', 'navy');
        merge('blue', 'navy');
      } else {
        merge('black', 'blue');
        merge('navy', 'blue');
      }
    }
    final ranked = counts.entries.toList()
      ..sort((a, b) => b.value.compareTo(a.value));
    if (ranked.isEmpty) {
      return (primary: backgroundName ?? 'black', secondary: null);
    }
    var primary = ranked.first.key;
    if (backgroundName != null && ranked.length > 1) {
      final matchesBg = primary == backgroundName;
      final whiteBleed = {'white', 'cream'}.contains(primary) &&
          {'white', 'cream', 'grey'}.contains(backgroundName);
      if (matchesBg || whiteBleed) {
        for (final entry in ranked.skip(1)) {
          if (entry.key == backgroundName) continue;
          final chromatic = !_studioNeutrals.contains(entry.key);
          if (chromatic && entry.value > n * 0.08) {
            primary = entry.key;
            break;
          }
          if (entry.value > n * 0.18) {
            primary = entry.key;
            break;
          }
        }
      }
    }
    String? secondary;
    for (final entry in ranked) {
      if (entry.key == primary) continue;
      if (entry.key == backgroundName) continue;
      if (entry.value > n * 0.18) {
        secondary = entry.key;
        break;
      }
    }
    return (
      primary: primary,
      secondary: secondary == primary ? null : secondary,
    );
  }

  static String _nameFromRgb(int r, int g, int b) {
    final hsv = _hsv(r, g, b);
    final h = hsv.$1;
    final s = hsv.$2;
    final v = hsv.$3;
    if (v < 0.13) return 'black';
    if (s < 0.08 && v > 0.93) return 'white';
    if (s < 0.10 && v > 0.86) return 'cream';
    if (s < 0.11 && v > 0.38 && v <= 0.86) return 'grey';
    if (s < 0.14 && v <= 0.38) return 'black';
    if (v < 0.32 && h >= 195 && h <= 265) return 'navy';
    if (s < 0.26 && v > 0.60 && h >= 20 && h <= 55) return 'beige';
    if (h >= 34 && h <= 52 && s >= 0.28 && v >= 0.40 && v <= 0.90) {
      return 'gold';
    }
    if (h <= 12 || h >= 345) {
      if (v < 0.40) return 'maroon';
      if (s < 0.42 && v > 0.72) return 'pink';
      return 'red';
    }
    if (h < 28) return v > 0.72 ? 'orange' : 'brown';
    if (h < 48) return s > 0.58 && v > 0.62 ? 'orange' : 'brown';
    if (h < 70) return s > 0.48 ? 'yellow' : 'olive';
    if (h < 160) return h < 90 && s < 0.4 ? 'olive' : 'green';
    if (h < 195) return 'teal';
    if (h < 255) return v < 0.36 ? 'navy' : 'blue';
    if (h < 295) return 'purple';
    if (h < 345) return v > 0.55 ? 'pink' : 'maroon';
    return _nearest([r.toDouble(), g.toDouble(), b.toDouble()]);
  }

  static (double, double, double) _hsv(int r, int g, int b) {
    final rf = r / 255, gf = g / 255, bf = b / 255;
    final maxc = max(rf, max(gf, bf));
    final minc = min(rf, min(gf, bf));
    final d = maxc - minc;
    final v = maxc;
    final s = maxc == 0 ? 0.0 : d / maxc;
    var h = 0.0;
    if (d > 0) {
      if (maxc == rf) {
        h = ((gf - bf) / d) % 6;
      } else if (maxc == gf) {
        h = (bf - rf) / d + 2;
      } else {
        h = (rf - gf) / d + 4;
      }
      h *= 60;
      if (h < 0) h += 360;
    }
    return (h, s, v);
  }

  static ({ClothingCategory category, String subcategory, double confidence})
      _classifyItem(_FgStats fg, ClothingDescriptor desc) {
    final color = desc.color;
    if (fg.assumedFillColor != null && _isBodyGarment(desc)) {
      return (
        category: ClothingCategory.upperwear,
        subcategory: 't-shirt',
        confidence: 0.46,
      );
    }
    final occ = fg.occupancy;
    final ar = fg.aspect;
    final fill = fg.fill;
    final cy = fg.cy;
    final blobs = fg.blobs;
    final largest = fg.largestBlob;
    final goldish = color == 'gold';
    final metallic = {'gold', 'grey', 'white', 'cream', 'black'}.contains(color);
    final denim = color == 'blue' || color == 'navy';
    final hFrac = fg.heightFrac;
    final flare = fg.flare;
    final upperMass = fg.upperMass;

    if (ar > 2.2 && hFrac < 0.18 && occ < 0.26 && blobs <= 1) {
      return (
        category: ClothingCategory.accessories,
        subcategory: 'belt',
        confidence: 0.78,
      );
    }

    if ((occ < 0.12 && hFrac < 0.34 && !fg.lShape && blobs <= 1) ||
        (goldish && !fg.lShape && occ < 0.22 && hFrac < 0.42)) {
      if (metallic && !goldish && fill > 0.40 && ar > 0.7 && ar < 1.5) {
        return (
          category: ClothingCategory.accessories,
          subcategory: 'watch',
          confidence: 0.72,
        );
      }
      return (
        category: ClothingCategory.accessories,
        subcategory: 'jewelry',
        confidence: 0.76,
      );
    }

    if (_looksLikeHat(desc) || _looksLikeCap(desc)) {
      return (
        category: ClothingCategory.accessories,
        subcategory: 'hat',
        confidence: 0.84,
      );
    }

    if (_looksLikeShorts(desc)) {
      return (
        category: ClothingCategory.lowerwear,
        subcategory: 'shorts',
        confidence: 0.86,
      );
    }

    if (_looksLikeTrousers(desc)) {
      return (
        category: ClothingCategory.lowerwear,
        subcategory: desc.denim ? 'jeans' : 'trousers',
        confidence: 0.86,
      );
    }

    if (_looksLikeSkirt(desc)) {
      return (
        category: ClothingCategory.lowerwear,
        subcategory: 'skirt',
        confidence: 0.84,
      );
    }

    if (_looksLikeHandledBag(desc) ||
        _looksLikeBackpack(desc) ||
        _looksLikeClutch(desc) ||
        _looksLikeBag(desc)) {
      return (
        category: ClothingCategory.accessories,
        subcategory: 'bag',
        confidence: 0.86,
      );
    }

    if (_hatFromModel(desc)) {
      return (
        category: ClothingCategory.accessories,
        subcategory: 'hat',
        confidence: 0.80,
      );
    }

    if (fg.lShape && hFrac > 0.22 && occ < 0.42) {
      if (desc.upperMass > 0.30 && desc.cy < 0.54) {
        return (
          category: ClothingCategory.accessories,
          subcategory: 'hat',
          confidence: 0.82,
        );
      }
      if (_looksLikeStiletto(desc)) {
        return (
          category: ClothingCategory.footwear,
          subcategory: 'heels',
          confidence: 0.82,
        );
      }
    }
    if (_looksLikeStiletto(desc) &&
        hFrac > 0.32 &&
        occ < 0.30 &&
        ar < 1.30 &&
        fill < 0.72) {
      return (
        category: ClothingCategory.footwear,
        subcategory: 'heels',
        confidence: 0.76,
      );
    }
    String footSub() {
      if (color == 'white' || color == 'grey') return 'sneakers';
      if (hFrac < 0.24 && ar > 1.25) return 'flats';
      return 'shoes';
    }

    if (blobs >= 2 && occ >= 0.10 && occ < 0.48 && largest >= 22 && hFrac < 0.62) {
      return (
        category: ClothingCategory.footwear,
        subcategory: footSub(),
        confidence: 0.76,
      );
    }
    if (occ >= 0.12 && occ < 0.45 && ar > 1.18 && ar < 3.0 && fill > 0.28 && hFrac < 0.50) {
      return (
        category: ClothingCategory.footwear,
        subcategory: footSub(),
        confidence: 0.70,
      );
    }

    if (blobs >= 2 &&
        occ < 0.52 &&
        hFrac < 0.62 &&
        (ar > 0.88 || cy > 0.54 || hFrac < 0.48)) {
      return (
        category: ClothingCategory.footwear,
        subcategory: footSub(),
        confidence: 0.80,
      );
    }

    final onePiece = hFrac > 0.62 &&
        ar < 0.95 &&
        occ > 0.14 &&
        upperMass > 0.16 &&
        blobs <= 1 &&
        !fg.lShape &&
        fg.topFrac <= 0.16 &&
        !_looksLikeSkirt(desc) &&
        (flare > 1.08 || (hFrac > 0.66 && ar < 0.80));
    if (onePiece) {
      return (
        category: ClothingCategory.dress,
        subcategory: 'dress',
        confidence: flare > 1.14 ? 0.84 : 0.78,
      );
    }

    if (denim && occ > 0.18 && ar < 1.15) {
      return (
        category: ClothingCategory.lowerwear,
        subcategory: 'jeans',
        confidence: 0.72,
      );
    }
    if (!denim && occ > 0.22 && ar < 0.86 && hFrac < 0.52 && cy > 0.52) {
      return (
        category: ClothingCategory.lowerwear,
        subcategory: 'shorts',
        confidence: 0.62,
      );
    }

    if (occ >= 0.11 && occ < 0.46 && ar > 0.55 && ar < 1.75 && fill > 0.30) {
      if (flare > 1.06 && hFrac >= 0.28 && hFrac <= 0.68 && blobs <= 1) {
        return (
          category: ClothingCategory.lowerwear,
          subcategory: 'skirt',
          confidence: 0.72,
        );
      }
      return (
        category: ClothingCategory.accessories,
        subcategory: 'bag',
        confidence: 0.64,
      );
    }
    if (occ > 0.30 && ar > 0.62 && ar < 1.50 && hFrac > 0.48 && _isBodyGarment(desc)) {
      final sub = switch (color) {
        'black' || 'navy' || 'grey' when occ > 0.50 && ar < 1.15 => 'hoodie',
        'black' || 'navy' || 'grey' => 'jacket',
        'white' || 'cream' || 'blue' => 'shirt',
        _ => 't-shirt',
      };
      return (
        category: ClothingCategory.upperwear,
        subcategory: sub,
        confidence: 0.62,
      );
    }
    return (
      category: ClothingCategory.accessories,
      subcategory: ClothingCatalog.unknownType,
      confidence: 0.22,
    );
  }

  static double? _sessionIta;

  static SkinToneAnalysis analyzeSkinTone(
    Uint8List bytes, {
    SkinTone? previous,
  }) {
    final decoded = img.decodeImage(bytes);
    if (decoded == null) {
      return const SkinToneAnalysis(
        skinTone: SkinTone.medium,
        usedFallback: true,
        message: 'Could not read the photo. Select your skin tone manually.',
      );
    }
    final resized = img.copyResize(decoded, width: 160, height: 160);
    final itas = <double>[];
    final x0 = (resized.width * 0.28).round();
    final x1 = (resized.width * 0.72).round();
    final y0 = (resized.height * 0.22).round();
    final y1 = (resized.height * 0.68).round();
    for (var y = y0; y < y1; y += 1) {
      for (var x = x0; x < x1; x += 1) {
        final p = resized.getPixel(x, y);
        final r = p.r.toInt();
        final g = p.g.toInt();
        final b = p.b.toInt();
        if (!_looksLikeSkin(r, g, b)) continue;
        itas.add(_itaFromRgb(r, g, b));
      }
    }
    if (itas.length < 30) {
      for (var y = 48; y < 112; y++) {
        for (var x = 48; x < 112; x++) {
          final p = resized.getPixel(x, y);
          itas.add(_itaFromRgb(p.r.toInt(), p.g.toInt(), p.b.toInt()));
        }
      }
    }
    itas.sort();
    var ita = itas.isEmpty ? 28.0 : itas[itas.length ~/ 2];
    if (_sessionIta != null) {
      ita = _sessionIta! * 0.65 + ita * 0.35;
    }
    _sessionIta = ita;
    var tone = _toneFromIta(ita);
    if (previous != null && _adjacent(previous, tone)) {
      tone = previous;
    }
    return SkinToneAnalysis(
      skinTone: tone,
      ita: ita,
      usedFallback: true,
      message:
          'Suggested ${tone.label}. Lighting can change a photo, so confirm the tone if it looks off.',
    );
  }

  static SkinTone _toneFromIta(double ita) {
    if (ita > 55) return SkinTone.veryLight;
    if (ita > 41) return SkinTone.light;
    if (ita > 28) return SkinTone.medium;
    if (ita > 10) return SkinTone.tan;
    if (ita > -30) return SkinTone.brown;
    return SkinTone.deep;
  }

  static bool _adjacent(SkinTone a, SkinTone b) {
    return (a.index - b.index).abs() == 1;
  }

  static double _itaFromRgb(int r, int g, int b) {
    final lab = _rgbToLab(r, g, b);
    final denom = lab[2] == 0 ? 0.0001 : lab[2];
    return atan((lab[0] - 50) / denom) * 180 / pi;
  }

  static List<double> _rgbToLab(int r, int g, int b) {
    double linear(int c) {
      final v = c / 255;
      return v > 0.04045 ? pow((v + 0.055) / 1.055, 2.4).toDouble() : v / 12.92;
    }

    final rl = linear(r);
    final gl = linear(g);
    final bl = linear(b);
    final x = (rl * 0.4124 + gl * 0.3576 + bl * 0.1805) / 0.95047;
    final y = rl * 0.2126 + gl * 0.7152 + bl * 0.0722;
    final z = (rl * 0.0193 + gl * 0.1192 + bl * 0.9505) / 1.08883;
    double f(double t) =>
        t > 0.008856 ? pow(t, 1 / 3).toDouble() : (7.787 * t) + 16 / 116;
    final fy = f(y);
    return [116 * fy - 16, 500 * (f(x) - fy), 200 * (fy - f(z))];
  }

  static bool _looksLikeSkin(int r, int g, int b) {
    final y = 0.299 * r + 0.587 * g + 0.114 * b;
    final cb = 128 - 0.168736 * r - 0.331264 * g + 0.5 * b;
    final cr = 128 + 0.5 * r - 0.418688 * g - 0.081312 * b;
    return r > 60 &&
        g > 30 &&
        b > 15 &&
        r > g &&
        r > b &&
        (r - g) > 10 &&
        y > 40 &&
        y < 240 &&
        cb > 77 &&
        cb < 140 &&
        cr > 125 &&
        cr < 180;
  }

  static bool _isGarmentSkin(int r, int g, int b) {
    if (!_looksLikeSkin(r, g, b)) return false;
    final hsv = _hsv(r, g, b);
    if (hsv.$3 < 0.26) return false;
    if (hsv.$2 > 0.50 && hsv.$1 >= 14 && hsv.$1 <= 50) return false;
    return true;
  }

  static List<double> _mean(List<List<int>> samples) {
    var r = 0.0, g = 0.0, b = 0.0;
    for (final s in samples) {
      r += s[0];
      g += s[1];
      b += s[2];
    }
    final n = samples.length;
    return [r / n, g / n, b / n];
  }

  static String _nearest(List<double> rgb) {
    var best = ClothingCatalog.colors.first;
    var bestDist = double.infinity;
    for (final entry in _named.entries) {
      final d = _dist(rgb, [
        entry.value[0].toDouble(),
        entry.value[1].toDouble(),
        entry.value[2].toDouble(),
      ]);
      if (d < bestDist) {
        bestDist = d;
        best = entry.key;
      }
    }
    return best;
  }

  static double _dist(List<double> a, List<double> b) {
    return sqrt(
      pow(a[0] - b[0], 2) + pow(a[1] - b[1], 2) + pow(a[2] - b[2], 2),
    );
  }
}

class _Pix {
  const _Pix(this.x, this.y, this.r, this.g, this.b);
  final int x, y, r, g, b;
}

class _FgStats {
  const _FgStats({
    required this.occupancy,
    required this.aspect,
    required this.fill,
    required this.cx,
    required this.cy,
    required this.heightFrac,
    required this.topFrac,
    required this.lShape,
    required this.flare,
    required this.upperMass,
    required this.lowerCenterFill,
    required this.edgeRatio,
    required this.hollow,
    required this.blobs,
    required this.largestBlob,
    required this.skinRatio,
    required this.topHeavy,
    required this.colorPixels,
    required this.assumedFillColor,
    required this.backgroundName,
    required this.backgroundRgb,
    required this.grid9,
    required this.bands4,
    required this.hues6,
  });

  factory _FgStats.empty({
    required String assumedFillColor,
    List<double>? backgroundRgb,
  }) {
    final bg = backgroundRgb ?? [245.0, 245.0, 245.0];
    return _FgStats(
      occupancy: 0.55,
      aspect: 1,
      fill: 0.55,
      cx: 0.5,
      cy: 0.5,
      heightFrac: 0.5,
      topFrac: 0.12,
      lShape: false,
      flare: 1,
      upperMass: 0.4,
      lowerCenterFill: 0.5,
      edgeRatio: 0.2,
      hollow: 0,
      blobs: 1,
      largestBlob: 0,
      skinRatio: 0,
      topHeavy: false,
      colorPixels: [
        [245, 245, 245]
      ],
      assumedFillColor: assumedFillColor,
      backgroundName: assumedFillColor,
      backgroundRgb: bg,
      grid9: List<double>.filled(9, 0.12),
      bands4: List<double>.filled(4, 0.25),
      hues6: List<double>.filled(6, 0),
    );
  }

  final double occupancy;
  final double aspect;
  final double fill;
  final double cx;
  final double cy;
  final double heightFrac;
  final double topFrac;
  final bool lShape;
  final double flare;
  final double upperMass;
  final double lowerCenterFill;
  final double edgeRatio;
  final double hollow;
  final int blobs;
  final int largestBlob;
  final double skinRatio;
  final bool topHeavy;
  final List<List<int>> colorPixels;
  final String? assumedFillColor;
  final String? backgroundName;
  final List<double> backgroundRgb;
  final List<double> grid9;
  final List<double> bands4;
  final List<double> hues6;
}

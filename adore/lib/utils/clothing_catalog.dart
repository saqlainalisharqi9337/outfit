import 'enums.dart';

class ClothingCatalog {
  static const List<String> colors = [
    'black',
    'white',
    'grey',
    'red',
    'blue',
    'green',
    'yellow',
    'orange',
    'brown',
    'beige',
    'pink',
    'purple',
    'navy',
    'maroon',
    'cream',
    'olive',
    'gold',
    'teal',
  ];

  static const Map<String, String> colorAliases = {
    'gray': 'grey',
    'dark_red': 'maroon',
    'dark_green': 'olive',
    'light_blue': 'blue',
    'silver': 'grey',
  };

  static String? catalogColor(String? raw) {
    if (raw == null || raw.trim().isEmpty) return null;
    final key = raw.trim().toLowerCase().replaceAll(' ', '_');
    final mapped = colorAliases[key] ?? key;
    return colors.contains(mapped) ? mapped : null;
  }

  static const Map<ClothingCategory, List<String>> subcategories = {
    ClothingCategory.upperwear: [
      't-shirt',
      'shirt',
      'top',
      'kurta',
      'blouse',
      'sweater',
      'hoodie',
      'jacket',
      'coat',
      'blazer',
      'cardigan',
      'kameez',
      'abaya',
      'modest top',
    ],
    ClothingCategory.lowerwear: [
      'jeans',
      'trousers',
      'shalwar',
      'skirt',
      'shorts',
      'chinos',
      'palazzo',
      'leggings',
    ],
    ClothingCategory.footwear: [
      'flats',
      'heels',
      'shoes',
      'sneakers',
      'sandals',
      'boots',
      'khussa',
      'loafers',
    ],
    ClothingCategory.accessories: [
      'bag',
      'belt',
      'watch',
      'scarf',
      'dupatta',
      'hat',
      'hijab',
      'jewelry',
      'sunglasses',
    ],
    ClothingCategory.dress: [
      'dress',
      'modest dress',
      'gown',
      'jumpsuit',
      'kaftan',
    ],
  };

  static const String unknownType = 'unknown';

  static String displayNameFor(String subcategory) {
    return switch (subcategory) {
      'dress' => 'Dress',
      'gown' || 'modest dress' => 'Long Dress',
      'skirt' || 'miniskirt' => 'Skirt',
      'trousers' || 'pants' => 'Trousers',
      'jeans' => 'Jeans',
      'shorts' => 'Shorts',
      'shalwar' || 'salwar' => 'Shalwar',
      'leggings' || 'jeggings' => 'Leggings',
      'top' || 'modest top' => 'Top',
      't-shirt' || 'tshirt' => 'T-shirt',
      'bag' ||
      'purse' ||
      'handbag' ||
      'backpack' ||
      'tote' ||
      'clutch' ||
      'shoulder bag' ||
      'crossbody' ||
      'sling bag' ||
      'messenger' ||
      'satchel' ||
      'bucket bag' ||
      'duffel' => 'Bag',
      'jewelry' => 'Jewellery',
      'hat' || 'cap' => 'Hat',
      'heels' => 'Heels',
      'sneakers' => 'Sneakers',
      'flats' => 'Flats',
      'boots' => 'Boots',
      'sandals' => 'Sandals',
      'loafers' => 'Loafers',
      'shoes' => 'Shoes',
      'shirt' => 'Shirt',
      'jacket' || 'coat' => 'Jacket',
      unknownType => 'Unknown/Uncertain',
      _ => subcategory,
    };
  }

  static const Set<String> jewelryLabels = {
    'jewelry',
    'jewellery',
    'necklace',
    'bracelet',
    'ring',
    'earring',
    'earrings',
    'pendant',
    'bangle',
    'anklet',
    'brooch',
  };

  static const Set<String> bagLabels = {
    'bag',
    'purse',
    'handbag',
    'backpack',
    'tote',
    'clutch',
    'wallet',
    'shoulder bag',
    'crossbody',
    'sling bag',
    'messenger',
    'satchel',
    'bucket bag',
    'duffel',
  };

  static const Set<String> hatLabels = {
    'hat',
    'cap',
    'beanie',
    'fedora',
    'beret',
    'headwear',
  };

  static const Set<String> skirtLabels = {
    'skirt',
    'miniskirt',
    'mini skirt',
    'overskirt',
    'hoopskirt',
  };

  static const Set<String> dressLabels = {
    'dress',
    'gown',
    'one-piece',
    'onepiece',
    'modest dress',
    'kaftan',
    'jumpsuit',
  };

  static const Set<String> hatNever = {
    'shirt',
    't-shirt',
    'jeans',
    'trousers',
    'shorts',
    'skirt',
    'jacket',
    'coat',
    'hoodie',
    'sweater',
    'heels',
    'shoes',
    'sneakers',
    'flats',
    'boots',
    'sandals',
    'loafers',
  };

  static const Set<String> dressNever = {
    'jeans',
    'trousers',
    'shorts',
    'skirt',
    'shirt',
    't-shirt',
    'hoodie',
    'blouse',
    'top',
    'heels',
    'shoes',
    'sneakers',
    'flats',
    'boots',
    'sandals',
    'loafers',
    'hat',
    'cap',
  };

  static String familyOf(String subcategory) {
    final sub = subcategory.toLowerCase();
    const footwear = {
      'shoes',
      'sneakers',
      'sandals',
      'boots',
      'heels',
      'flats',
      'loafers',
      'khussa',
    };
    const jewelry = {'jewelry', 'watch', 'sunglasses'};
    const dresses = {'dress', 'modest dress', 'gown', 'jumpsuit', 'kaftan'};
    const lower = {
      'jeans',
      'trousers',
      'shalwar',
      'skirt',
      'shorts',
      'chinos',
      'palazzo',
      'leggings',
    };
    if (footwear.contains(sub)) return 'footwear';
    if (jewelry.contains(sub)) return 'jewelry';
    if (dresses.contains(sub)) return 'dress';
    if (lower.contains(sub)) return 'lowerwear';
    if ((subcategories[ClothingCategory.upperwear] ?? const []).contains(sub)) {
      return 'upperwear';
    }
    return 'accessory';
  }

  static (ClothingCategory, String) normalizeDetection({
    required ClothingCategory category,
    required String subcategory,
  }) {
    final sub = subcategory.toLowerCase().trim();
    if (sub == unknownType || sub == 'uncertain') {
      return (category, unknownType);
    }
    const aliases = <String, (ClothingCategory, String)>{
      'accessory': (ClothingCategory.accessories, 'jewelry'),
      'jewelry': (ClothingCategory.accessories, 'jewelry'),
      'watch': (ClothingCategory.accessories, 'watch'),
      'digital watch': (ClothingCategory.accessories, 'watch'),
      'analog clock': (ClothingCategory.accessories, 'watch'),
      'stopwatch': (ClothingCategory.accessories, 'watch'),
      'necklace': (ClothingCategory.accessories, 'jewelry'),
      'pendant': (ClothingCategory.accessories, 'jewelry'),
      'bracelet': (ClothingCategory.accessories, 'jewelry'),
      'earring': (ClothingCategory.accessories, 'jewelry'),
      'earrings': (ClothingCategory.accessories, 'jewelry'),
      'ring': (ClothingCategory.accessories, 'jewelry'),
      'bangle': (ClothingCategory.accessories, 'jewelry'),
      'anklet': (ClothingCategory.accessories, 'jewelry'),
      'brooch': (ClothingCategory.accessories, 'jewelry'),
      'hoop': (ClothingCategory.accessories, 'jewelry'),
      'cuff': (ClothingCategory.accessories, 'jewelry'),
      'sunglasses': (ClothingCategory.accessories, 'sunglasses'),
      'glasses': (ClothingCategory.accessories, 'sunglasses'),
      'shades': (ClothingCategory.accessories, 'sunglasses'),
      'aviator': (ClothingCategory.accessories, 'sunglasses'),
      'belt': (ClothingCategory.accessories, 'belt'),
      'seat belt': (ClothingCategory.accessories, 'belt'),
      'buckle': (ClothingCategory.accessories, 'belt'),
      'scarf': (ClothingCategory.accessories, 'scarf'),
      'stole': (ClothingCategory.accessories, 'dupatta'),
      'dupatta': (ClothingCategory.accessories, 'dupatta'),
      'hijab': (ClothingCategory.accessories, 'hijab'),
      'hat': (ClothingCategory.accessories, 'hat'),
      'cap': (ClothingCategory.accessories, 'hat'),
      'beanie': (ClothingCategory.accessories, 'hat'),
      'fedora': (ClothingCategory.accessories, 'hat'),
      'beret': (ClothingCategory.accessories, 'hat'),
      'headwear': (ClothingCategory.accessories, 'hat'),
      'bag': (ClothingCategory.accessories, 'bag'),
      'purse': (ClothingCategory.accessories, 'bag'),
      'handbag': (ClothingCategory.accessories, 'bag'),
      'backpack': (ClothingCategory.accessories, 'bag'),
      'tote': (ClothingCategory.accessories, 'bag'),
      'clutch': (ClothingCategory.accessories, 'bag'),
      'wallet': (ClothingCategory.accessories, 'bag'),
      'shoulder bag': (ClothingCategory.accessories, 'bag'),
      'crossbody': (ClothingCategory.accessories, 'bag'),
      'sling bag': (ClothingCategory.accessories, 'bag'),
      'sling': (ClothingCategory.accessories, 'bag'),
      'messenger': (ClothingCategory.accessories, 'bag'),
      'satchel': (ClothingCategory.accessories, 'bag'),
      'bucket bag': (ClothingCategory.accessories, 'bag'),
      'duffel': (ClothingCategory.accessories, 'bag'),
      'laptop bag': (ClothingCategory.accessories, 'bag'),
      'travel bag': (ClothingCategory.accessories, 'bag'),
      'waist bag': (ClothingCategory.accessories, 'bag'),
      'belt bag': (ClothingCategory.accessories, 'bag'),
      'sneaker': (ClothingCategory.footwear, 'sneakers'),
      'sneakers': (ClothingCategory.footwear, 'sneakers'),
      'running shoe': (ClothingCategory.footwear, 'sneakers'),
      'trainer': (ClothingCategory.footwear, 'sneakers'),
      'flat': (ClothingCategory.footwear, 'flats'),
      'flats': (ClothingCategory.footwear, 'flats'),
      'ballet': (ClothingCategory.footwear, 'flats'),
      'ballerina': (ClothingCategory.footwear, 'flats'),
      'mule': (ClothingCategory.footwear, 'flats'),
      'shoe': (ClothingCategory.footwear, 'shoes'),
      'shoes': (ClothingCategory.footwear, 'shoes'),
      'loafer': (ClothingCategory.footwear, 'loafers'),
      'oxford': (ClothingCategory.footwear, 'loafers'),
      'boot': (ClothingCategory.footwear, 'boots'),
      'boots': (ClothingCategory.footwear, 'boots'),
      'sandal': (ClothingCategory.footwear, 'sandals'),
      'sandals': (ClothingCategory.footwear, 'sandals'),
      'heel': (ClothingCategory.footwear, 'heels'),
      'heels': (ClothingCategory.footwear, 'heels'),
      'stiletto': (ClothingCategory.footwear, 'heels'),
      'pump': (ClothingCategory.footwear, 'heels'),
      'wedge': (ClothingCategory.footwear, 'heels'),
      'jean': (ClothingCategory.lowerwear, 'jeans'),
      'jeans': (ClothingCategory.lowerwear, 'jeans'),
      'denim': (ClothingCategory.lowerwear, 'jeans'),
      'trouser': (ClothingCategory.lowerwear, 'trousers'),
      'trousers': (ClothingCategory.lowerwear, 'trousers'),
      'pant': (ClothingCategory.lowerwear, 'trousers'),
      'pants': (ClothingCategory.lowerwear, 'trousers'),
      'palazzo': (ClothingCategory.lowerwear, 'trousers'),
      'chino': (ClothingCategory.lowerwear, 'trousers'),
      'chinos': (ClothingCategory.lowerwear, 'trousers'),
      'jogger': (ClothingCategory.lowerwear, 'trousers'),
      'joggers': (ClothingCategory.lowerwear, 'trousers'),
      'culottes': (ClothingCategory.lowerwear, 'trousers'),
      'shalwar': (ClothingCategory.lowerwear, 'shalwar'),
      'salwar': (ClothingCategory.lowerwear, 'shalwar'),
      'patiala': (ClothingCategory.lowerwear, 'shalwar'),
      'churidar': (ClothingCategory.lowerwear, 'shalwar'),
      'leggings': (ClothingCategory.lowerwear, 'leggings'),
      'legging': (ClothingCategory.lowerwear, 'leggings'),
      'jeggings': (ClothingCategory.lowerwear, 'leggings'),
      'tights': (ClothingCategory.lowerwear, 'leggings'),
      'shorts': (ClothingCategory.lowerwear, 'shorts'),
      'skirt': (ClothingCategory.lowerwear, 'skirt'),
      'miniskirt': (ClothingCategory.lowerwear, 'skirt'),
      'mini skirt': (ClothingCategory.lowerwear, 'skirt'),
      'hoopskirt': (ClothingCategory.lowerwear, 'skirt'),
      'overskirt': (ClothingCategory.lowerwear, 'skirt'),
      'short': (ClothingCategory.lowerwear, 'shorts'),
      'dress': (ClothingCategory.dress, 'dress'),
      'one-piece': (ClothingCategory.dress, 'dress'),
      'onepiece': (ClothingCategory.dress, 'dress'),
      'one piece': (ClothingCategory.dress, 'dress'),
      'gown': (ClothingCategory.dress, 'gown'),
      'jumpsuit': (ClothingCategory.dress, 'jumpsuit'),
      'hoodie': (ClothingCategory.upperwear, 'hoodie'),
      'sweater': (ClothingCategory.upperwear, 'sweater'),
      'jumper': (ClothingCategory.upperwear, 'sweater'),
      'pullover': (ClothingCategory.upperwear, 'sweater'),
      'sweatshirt': (ClothingCategory.upperwear, 'hoodie'),
      't-shirt': (ClothingCategory.upperwear, 't-shirt'),
      'tshirt': (ClothingCategory.upperwear, 't-shirt'),
      'tee': (ClothingCategory.upperwear, 't-shirt'),
      'jersey': (ClothingCategory.upperwear, 't-shirt'),
      'top': (ClothingCategory.upperwear, 'top'),
      'modest top': (ClothingCategory.upperwear, 'top'),
      'shirt': (ClothingCategory.upperwear, 'shirt'),
      'blouse': (ClothingCategory.upperwear, 'blouse'),
      'jacket': (ClothingCategory.upperwear, 'jacket'),
      'coat': (ClothingCategory.upperwear, 'coat'),
      'blazer': (ClothingCategory.upperwear, 'blazer'),
      'cardigan': (ClothingCategory.upperwear, 'cardigan'),
      'kurta': (ClothingCategory.upperwear, 'kurta'),
      'kameez': (ClothingCategory.upperwear, 'kameez'),
      'abaya': (ClothingCategory.upperwear, 'abaya'),
    };
    if (aliases.containsKey(sub)) return aliases[sub]!;
    final prefixHits = aliases.entries
        .where(
          (e) =>
              e.key.length >= 4 &&
              e.key != 'shirt' &&
              (sub.startsWith(e.key) ||
                  (sub.length >= 5 && e.key.startsWith(sub))),
        )
        .toList()
      ..sort((a, b) => b.key.length.compareTo(a.key.length));
    if (prefixHits.isNotEmpty) return prefixHits.first.value;
    for (final entry in subcategories.entries) {
      if (entry.value.contains(sub)) return (entry.key, sub);
    }
    return (category, unknownType);
  }

  /// Below this, an on-device label is a guess rather than an anchor.
  static const double anchorConfidence = 0.55;

  /// Central family veto for confident on-device anchors.
  ///
  /// Hat and bag are the two silhouettes every downstream head confuses: a cap
  /// reads as a skirt hem, a tote reads as a skirt panel, and a shoe crop reads
  /// as either. Deciding this once here is what stops each new fix from having
  /// to restate the rule in its own branch and contradict a neighbouring one.
  ///
  /// Only a source that can see the whole garment may replace an anchor, which
  /// is why the silhouette head keeps its dress override.
  static bool _vetoedByLocalAnchor({
    required String local,
    required String ml,
    required String mlSource,
    required double localConfidence,
  }) {
    if (localConfidence < anchorConfidence) return false;
    if (hatLabels.contains(local)) {
      if ({'shirt', 't-shirt', 'jacket'}.contains(ml) &&
          (mlSource == 'shirt_gate' ||
              mlSource == 'tshirt_gate' ||
              mlSource == 'jacket_gate' ||
              mlSource == 'upperwear')) {
        return false;
      }
      return !(hatLabels.contains(ml) ||
          (dressLabels.contains(ml) && mlSource == 'silhouette'));
    }
    if (bagLabels.contains(local)) {
      return !bagLabels.contains(ml);
    }
    return false;
  }

  /// Merge on-device and ML labels with hard family vetoes.
  /// A cap/hat never becomes a shirt; a dress never becomes jeans.
  static ({
    ClothingCategory category,
    String subcategory,
    double confidence,
    bool usedFallback,
    String message,
  }) resolvePrediction({
    required ClothingCategory localCategory,
    required String localSubcategory,
    required double localConfidence,
    ClothingCategory? mlCategory,
    String? mlSubcategory,
    double mlConfidence = 0,
    String mlSource = 'none',
    bool mlUncertain = true,
    String? mlMessage,
    String? extraItemsMessage,
  }) {
    final local = normalizeDetection(
      category: localCategory,
      subcategory: localSubcategory,
    );
    final hasMl = mlSubcategory != null && mlSubcategory.trim().isNotEmpty;
    final rawMl = hasMl
        ? normalizeDetection(
            category: mlCategory ?? local.$1,
            subcategory: mlSubcategory,
          )
        : null;
    // A prediction rejected by the central family veto is treated as no
    // prediction at all, so no branch below can resurrect it.
    final ml = rawMl != null &&
            _vetoedByLocalAnchor(
              local: local.$2,
              ml: rawMl.$2,
              mlSource: mlSource,
              localConfidence: localConfidence,
            )
        ? null
        : rawMl;

    var category = local.$1;
    var subcategory = local.$2;
    var confidence = localConfidence;
    var usedFallback = localConfidence < 0.55 || subcategory == unknownType;
    var message = 'Detected $subcategory.';

    const pantsLabels = {'trousers', 'jeans', 'shorts'};
    const footwearLocal = {
      'shoes',
      'heels',
      'sneakers',
      'flats',
      'boots',
      'sandals',
      'loafers',
    };
    const upperwearFromSpecialist = {
      'shirt',
      't-shirt',
      'hoodie',
      'jacket',
      'top',
      'blouse',
      'coat',
      'dress',
      'gown',
    };
    // The 6-class upperwear head must beat jacket/t-shirt binary gates in
    // merge, otherwise a hoodie or gown is shown as a shirt/jacket.
    if (ml != null &&
        !mlUncertain &&
        mlConfidence >= 0.32 &&
        mlSource == 'upperwear' &&
        upperwearFromSpecialist.contains(ml.$2) &&
        !pantsLabels.contains(local.$2) &&
        !skirtLabels.contains(local.$2) &&
        !bagLabels.contains(local.$2) &&
        !footwearLocal.contains(local.$2)) {
      if (dressLabels.contains(ml.$2)) {
        category = ClothingCategory.dress;
        subcategory = ml.$2 == 'gown' ? 'gown' : 'dress';
      } else {
        category = ClothingCategory.upperwear;
        subcategory = ml.$2;
      }
      confidence = mlConfidence;
      usedFallback = false;
      message = mlMessage ?? 'Detected ${ml.$2}.';
    } else if (ml != null &&
        !mlUncertain &&
        mlConfidence >= 0.28 &&
        mlSource == 'jacket_gate' &&
        ml.$2 == 'jacket' &&
        !pantsLabels.contains(local.$2) &&
        !skirtLabels.contains(local.$2) &&
        !bagLabels.contains(local.$2)) {
      category = ClothingCategory.upperwear;
      subcategory = 'jacket';
      confidence = mlConfidence;
      usedFallback = false;
      message = mlMessage ?? 'Detected jacket.';
    } else if (ml != null &&
        !mlUncertain &&
        mlConfidence >= 0.28 &&
        mlSource == 'tshirt_gate' &&
        ml.$2 == 't-shirt' &&
        !pantsLabels.contains(local.$2) &&
        !skirtLabels.contains(local.$2) &&
        !bagLabels.contains(local.$2)) {
      category = ClothingCategory.upperwear;
      subcategory = 't-shirt';
      confidence = mlConfidence;
      usedFallback = false;
      message = mlMessage ?? 'Detected t-shirt.';
    } else if (ml != null &&
        !mlUncertain &&
        mlConfidence >= 0.28 &&
        mlSource == 'shoes_gate' &&
        ml.$2 == 'shoes' &&
        !pantsLabels.contains(local.$2) &&
        !skirtLabels.contains(local.$2) &&
        !bagLabels.contains(local.$2) &&
        local.$2 != 'jacket') {
      category = ClothingCategory.footwear;
      subcategory = 'shoes';
      confidence = mlConfidence;
      usedFallback = false;
      message = mlMessage ?? 'Detected shoes.';
    } else if (ml != null &&
        !mlUncertain &&
        mlConfidence >= 0.28 &&
        mlSource == 'sneakers_gate' &&
        ml.$2 == 'sneakers' &&
        !pantsLabels.contains(local.$2) &&
        !skirtLabels.contains(local.$2) &&
        !bagLabels.contains(local.$2) &&
        local.$2 != 'jacket') {
      category = ClothingCategory.footwear;
      subcategory = 'sneakers';
      confidence = mlConfidence;
      usedFallback = false;
      message = mlMessage ?? 'Detected sneakers.';
    } else if (ml != null &&
        !mlUncertain &&
        mlConfidence >= 0.28 &&
        mlSource == 'heels_gate' &&
        ml.$2 == 'heels' &&
        !pantsLabels.contains(local.$2) &&
        !skirtLabels.contains(local.$2) &&
        !bagLabels.contains(local.$2) &&
        local.$2 != 'jacket') {
      category = ClothingCategory.footwear;
      subcategory = 'heels';
      confidence = mlConfidence;
      usedFallback = false;
      message = mlMessage ?? 'Detected heels.';
    } else if (ml != null &&
        !mlUncertain &&
        mlConfidence >= 0.28 &&
        mlSource == 'flats_gate' &&
        ml.$2 == 'flats' &&
        !pantsLabels.contains(local.$2) &&
        !skirtLabels.contains(local.$2) &&
        !{
          'shirt',
          't-shirt',
          'hoodie',
          'jacket',
          'coat',
          'sweater',
        }.contains(local.$2)) {
      category = ClothingCategory.footwear;
      subcategory = 'flats';
      confidence = mlConfidence;
      usedFallback = false;
      message = mlMessage ?? 'Detected flats.';
    } else if (ml != null &&
        !mlUncertain &&
        mlConfidence >= 0.28 &&
        (mlSource == 'shirt_gate' || mlSource == 'upperwear') &&
        {
          'shirt',
          't-shirt',
          'hoodie',
          'jacket',
          'top',
          'blouse',
          'coat',
        }.contains(ml.$2) &&
        !pantsLabels.contains(local.$2) &&
        !skirtLabels.contains(local.$2) &&
        !bagLabels.contains(local.$2) &&
        !{
          'shoes',
          'heels',
          'sneakers',
          'flats',
          'boots',
          'sandals',
          'loafers',
        }.contains(local.$2)) {
      category = ClothingCategory.upperwear;
      subcategory = ml.$2;
      confidence = mlConfidence;
      usedFallback = false;
      message = mlMessage ?? 'Detected ${ml.$2}.';
    } else if (pantsLabels.contains(local.$2) &&
        ml != null &&
        dressLabels.contains(ml.$2)) {
      category = ClothingCategory.lowerwear;
      subcategory = local.$2;
      confidence = localConfidence < 0.80 ? 0.80 : localConfidence;
      usedFallback = false;
      message = 'Two-leg pants kept instead of a one-piece guess.';
    } else if (ml != null &&
        !mlUncertain &&
        mlConfidence >= 0.38 &&
        mlSource == 'upperwear' &&
        dressLabels.contains(ml.$2) &&
        !pantsLabels.contains(local.$2) &&
        !skirtLabels.contains(local.$2) &&
        !bagLabels.contains(local.$2) &&
        !hatLabels.contains(local.$2)) {
      category = ClothingCategory.dress;
      subcategory = ml.$2 == 'gown' ? 'gown' : 'dress';
      confidence = mlConfidence;
      usedFallback = false;
      message = mlMessage ?? 'Detected ${ml.$2}.';
    } else if (mlSource == 'accessory' &&
        ml != null &&
        !mlUncertain &&
        mlConfidence >= 0.30 &&
        {
          'heels',
          'shoes',
          'sneakers',
          'flats',
          'boots',
          'sandals',
          'loafers',
        }.contains(ml.$2) &&
        !dressLabels.contains(local.$2)) {
      category = ClothingCategory.footwear;
      subcategory = ml.$2;
      confidence = mlConfidence;
      usedFallback = false;
      message = mlMessage ?? 'Detected ${ml.$2}.';
    } else if (ml != null &&
        !mlUncertain &&
        mlConfidence >= 0.40 &&
        pantsLabels.contains(ml.$2) &&
        dressLabels.contains(local.$2) &&
        (mlSource == 'lowerwear' ||
            mlSource == 'silhouette' ||
            mlSource == 'imagenet')) {
      category = ClothingCategory.lowerwear;
      subcategory = local.$2 == 'jeans' && ml.$2 == 'trousers' ? 'jeans' : ml.$2;
      confidence = mlConfidence;
      usedFallback = false;
      message = mlMessage ?? 'Detected $subcategory.';
    } else if (mlSource == 'silhouette' &&
        ml != null &&
        !mlUncertain &&
        mlConfidence >= 0.40 &&
        {'dress', 'skirt', 'trousers', 'jeans'}.contains(ml.$2) &&
        !bagLabels.contains(local.$2) &&
        !(hatLabels.contains(local.$2) && ml.$2 != 'dress') &&
        !(pantsLabels.contains(local.$2) && dressLabels.contains(ml.$2))) {
      category = ml.$1;
      subcategory = ml.$2;
      confidence = mlConfidence;
      usedFallback = false;
      message = mlMessage ?? 'Detected ${ml.$2}.';
    } else if ((mlSource == 'lowerwear' || mlSource == 'lowerwear5') &&
        ml != null &&
        !mlUncertain &&
        mlConfidence >= 0.40 &&
        {
          'trousers',
          'jeans',
          'shorts',
          'skirt',
          'shalwar',
          'leggings',
          'palazzo',
        }.contains(ml.$2) &&
        !hatLabels.contains(local.$2) &&
        !bagLabels.contains(local.$2) &&
        !(dressLabels.contains(local.$2) && ml.$2 == 'skirt')) {
      category = ml.$1;
      subcategory = local.$2 == 'jeans' && ml.$2 == 'trousers' ? 'jeans' : ml.$2;
      confidence = mlConfidence;
      usedFallback = false;
      message = mlMessage ?? 'Detected $subcategory.';
    } else if (mlSource == 'lowerwear' &&
        ml != null &&
        pantsLabels.contains(ml.$2) &&
        hatLabels.contains(local.$2) &&
        localConfidence >= anchorConfidence) {
      category = ClothingCategory.accessories;
      subcategory = 'hat';
      confidence = localConfidence < 0.80 ? 0.80 : localConfidence;
      usedFallback = false;
      message = 'Cap/hat kept instead of a shorts collision.';
    } else if (ml != null &&
        bagLabels.contains(ml.$2) &&
        !mlUncertain &&
        ml.$2 != unknownType &&
        (mlSource == 'accessory' ||
            (mlSource == 'imagenet' && mlConfidence >= 0.18)) &&
        !dressLabels.contains(local.$2) &&
        !hatLabels.contains(local.$2) &&
        !pantsLabels.contains(local.$2)) {
      category = ClothingCategory.accessories;
      subcategory = 'bag';
      confidence = mlConfidence < 0.80 ? 0.80 : mlConfidence;
      usedFallback = false;
      message = mlMessage ?? 'Detected bag.';
    } else if (pantsLabels.contains(local.$2) &&
        ml != null &&
        bagLabels.contains(ml.$2)) {
      category = ClothingCategory.lowerwear;
      subcategory = local.$2;
      confidence = localConfidence < 0.80 ? 0.80 : localConfidence;
      usedFallback = false;
      message = 'Trousers/pants kept instead of a bag collision.';
    } else if (hatLabels.contains(local.$2) &&
        ml != null &&
        pantsLabels.contains(ml.$2) &&
        localConfidence >= anchorConfidence) {
      category = ClothingCategory.accessories;
      subcategory = 'hat';
      confidence = localConfidence < 0.80 ? 0.80 : localConfidence;
      usedFallback = false;
      message = 'Cap/hat kept instead of a shorts/trousers collision.';
    } else if (skirtLabels.contains(local.$2) &&
        ml != null &&
        (hatNever.contains(ml.$2) ||
            dressLabels.contains(ml.$2) ||
            (hatLabels.contains(ml.$2) && mlSource == 'imagenet')) &&
        !bagLabels.contains(ml.$2)) {
      category = ClothingCategory.lowerwear;
      subcategory = 'skirt';
      confidence = localConfidence < 0.80 ? 0.80 : localConfidence;
      usedFallback = false;
      message = 'Skirt shape overrode a heel or accessory guess.';
    } else if (ml != null &&
        skirtLabels.contains(ml.$2) &&
        {
          'heels',
          'shoes',
          'sneakers',
          'flats',
          'boots',
          'sandals',
          'loafers',
        }.contains(local.$2) &&
        (mlSource == 'lowerwear' ||
            mlSource == 'silhouette' ||
            mlConfidence >= 0.25)) {
      category = ClothingCategory.lowerwear;
      subcategory = 'skirt';
      confidence = mlConfidence < 0.80 ? 0.80 : mlConfidence;
      usedFallback = false;
      message = mlMessage ?? 'Detected skirt.';
    } else if (hatLabels.contains(local.$2) &&
        ml != null &&
        (hatNever.contains(ml.$2) ||
            skirtLabels.contains(ml.$2) ||
            bagLabels.contains(ml.$2)) &&
        !dressLabels.contains(ml.$2) &&
        !(pantsLabels.contains(ml.$2) &&
            localConfidence < anchorConfidence &&
            (mlSource == 'lowerwear' ||
                mlSource == 'silhouette' ||
                mlSource == 'imagenet'))) {
      category = ClothingCategory.accessories;
      subcategory = 'hat';
      confidence = localConfidence < 0.80 ? 0.80 : localConfidence;
      usedFallback = false;
      message = 'Cap/hat shape overrode a clothing-body or heel guess.';
    } else if (ml != null &&
        pantsLabels.contains(ml.$2) &&
        hatLabels.contains(local.$2) &&
        localConfidence < anchorConfidence &&
        (mlSource == 'lowerwear' ||
            mlSource == 'silhouette' ||
            mlSource == 'imagenet') &&
        !mlUncertain &&
        mlConfidence >= 0.40) {
      category = ClothingCategory.lowerwear;
      subcategory = ml.$2;
      confidence = mlConfidence;
      usedFallback = false;
      message = mlMessage ?? 'Detected $subcategory.';
    } else if (ml != null &&
        hatLabels.contains(ml.$2) &&
        ({
          'heels',
          'shoes',
          'sneakers',
          'flats',
          'boots',
          'sandals',
          'loafers',
        }.contains(local.$2) ||
            skirtLabels.contains(local.$2)) &&
        local.$2 != 'sneakers' &&
        local.$2 != 'shoes' &&
        mlSource != 'sneakers_gate' &&
        mlSource != 'shoes_gate' &&
        !dressLabels.contains(local.$2) &&
        !{
          'shirt',
          't-shirt',
          'hoodie',
          'jacket',
          'coat',
          'sweater',
          'jeans',
          'trousers',
          'shorts',
        }.contains(local.$2)) {
      // ML hat may correct footwear/skirt collisions — never a full shirt
      // or trousers panel (ImageNet cowboy_hat on hanging garments).
      category = ClothingCategory.accessories;
      subcategory = 'hat';
      confidence = mlConfidence < 0.80 ? 0.80 : mlConfidence;
      usedFallback = false;
      message = mlMessage ?? 'Detected hat.';
    } else if ({
          'shirt',
          't-shirt',
          'hoodie',
          'jacket',
          'coat',
          'sweater',
        }.contains(local.$2) &&
        ml != null &&
        hatLabels.contains(ml.$2)) {
      category = ClothingCategory.upperwear;
      subcategory = local.$2;
      confidence = localConfidence < 0.80 ? 0.80 : localConfidence;
      usedFallback = false;
      message = 'Shirt/upperwear kept instead of a hat collision.';
    } else if (pantsLabels.contains(local.$2) &&
        ml != null &&
        hatLabels.contains(ml.$2)) {
      category = ClothingCategory.lowerwear;
      subcategory = local.$2;
      confidence = localConfidence < 0.80 ? 0.80 : localConfidence;
      usedFallback = false;
      message = 'Trousers/pants kept instead of a hat collision.';
    } else if (ml != null &&
        {
          'shirt',
          't-shirt',
          'hoodie',
          'jacket',
          'coat',
          'sweater',
        }.contains(ml.$2) &&
        hatLabels.contains(local.$2) &&
        localConfidence < anchorConfidence &&
        !mlUncertain &&
        mlConfidence >= 0.40) {
      category = ClothingCategory.upperwear;
      subcategory = ml.$2;
      confidence = mlConfidence;
      usedFallback = false;
      message = mlMessage ?? 'Detected ${ml.$2}.';
    } else if (bagLabels.contains(local.$2) &&
        ml != null &&
        (hatNever.contains(ml.$2) ||
            jewelryLabels.contains(ml.$2) ||
            hatLabels.contains(ml.$2) ||
            skirtLabels.contains(ml.$2) ||
            ml.$2 == 'belt') &&
        !dressLabels.contains(ml.$2)) {
      category = ClothingCategory.accessories;
      subcategory = 'bag';
      confidence = localConfidence < 0.80 ? 0.80 : localConfidence;
      usedFallback = false;
      message = 'Bag shape overrode a heel or jewellery guess.';
    } else if (ml != null &&
        bagLabels.contains(ml.$2) &&
        (hatNever.contains(local.$2) || jewelryLabels.contains(local.$2)) &&
        !skirtLabels.contains(local.$2) &&
        !dressLabels.contains(local.$2)) {
      category = ClothingCategory.accessories;
      subcategory = 'bag';
      confidence = mlConfidence < 0.80 ? 0.80 : mlConfidence;
      usedFallback = false;
      message = mlMessage ?? 'Detected bag.';
    } else if (mlSource == 'accessory' &&
        ml != null &&
        !mlUncertain &&
        mlConfidence >= 0.40 &&
        (bagLabels.contains(ml.$2) ||
            {
              'shoes',
              'heels',
              'sneakers',
              'flats',
              'boots',
              'sandals',
              'loafers',
            }.contains(ml.$2)) &&
        !dressLabels.contains(local.$2) &&
        !(hatLabels.contains(local.$2) && !bagLabels.contains(ml.$2)) &&
        !bagLabels.contains(local.$2)) {
      category = ml.$1;
      subcategory = ml.$2;
      confidence = mlConfidence;
      usedFallback = false;
      message = mlMessage ?? 'Detected ${ml.$2}.';
    } else if (dressLabels.contains(local.$2) &&
        ml != null &&
        dressNever.contains(ml.$2) &&
        mlSource != 'silhouette' &&
        mlSource != 'lowerwear' &&
        mlSource != 'shirt_gate' &&
        mlSource != 'upperwear' &&
        mlSource != 'heels_gate' &&
        mlSource != 'sneakers_gate' &&
        mlSource != 'shoes_gate' &&
        !pantsLabels.contains(ml.$2) &&
        !{'shirt', 't-shirt'}.contains(ml.$2)) {
      category = ClothingCategory.dress;
      subcategory = 'dress';
      confidence = localConfidence < 0.80 ? 0.80 : localConfidence;
      usedFallback = false;
      message = 'Dress shape overrode a pants, skirt, or shoe guess.';
    } else if (ml != null &&
        dressLabels.contains(ml.$2) &&
        dressNever.contains(local.$2) &&
        !{'trousers', 'jeans', 'shorts'}.contains(local.$2) &&
        local.$2 != 'heels' &&
        local.$2 != 'sneakers' &&
        local.$2 != 'shoes' &&
        mlSource != 'heels_gate' &&
        mlSource != 'sneakers_gate' &&
        mlSource != 'shoes_gate') {
      category = ClothingCategory.dress;
      subcategory = 'dress';
      confidence = mlConfidence < 0.80 ? 0.80 : mlConfidence;
      usedFallback = false;
      message = mlMessage ?? 'Detected dress.';
    } else if (local.$2 == 'shorts' &&
        ml != null &&
        ml.$2 == 'trousers' &&
        mlSource != 'lowerwear' &&
        mlSource != 'silhouette') {
      category = ClothingCategory.lowerwear;
      subcategory = 'shorts';
      confidence = localConfidence < 0.78 ? 0.78 : localConfidence;
      usedFallback = false;
      message = 'Two short legs kept as shorts.';
    } else if (local.$2 == 'jeans' && ml != null && ml.$2 == 'trousers') {
      category = ClothingCategory.lowerwear;
      subcategory = 'jeans';
      confidence = localConfidence < 0.78 ? 0.78 : localConfidence;
      usedFallback = false;
      message = 'Denim lowerwear kept as jeans.';
    } else {
      final mlIsAccessory = ml != null &&
          (subcategories[ClothingCategory.accessories] ?? const []).contains(
            ml.$2,
          );
      final localIsGarment = dressLabels.contains(local.$2) ||
          skirtLabels.contains(local.$2) ||
          {
            'jeans',
            'trousers',
            'shorts',
            'shirt',
            't-shirt',
            'hoodie',
            'jacket',
            'coat',
            'sweater',
          }.contains(local.$2);
      final trustMl = ml != null &&
          !mlUncertain &&
          ml.$2 != unknownType &&
          !(mlSource == 'imagenet' &&
              bagLabels.contains(ml.$2) &&
              localIsGarment) &&
          ((mlSource == 'finetuned' && mlConfidence >= 0.40) ||
              (mlSource == 'tshirt_gate' &&
                  ml.$2 == 't-shirt' &&
                  mlConfidence >= 0.28) ||
              (mlSource == 'shirt_gate' &&
                  {'shirt', 't-shirt'}.contains(ml.$2) &&
                  mlConfidence >= 0.28) ||
              (mlSource == 'jacket_gate' &&
                  ml.$2 == 'jacket' &&
                  mlConfidence >= 0.28) ||
              (mlSource == 'flats_gate' &&
                  ml.$2 == 'flats' &&
                  mlConfidence >= 0.28) ||
              (mlSource == 'heels_gate' &&
                  ml.$2 == 'heels' &&
                  mlConfidence >= 0.28) ||
              (mlSource == 'sneakers_gate' &&
                  ml.$2 == 'sneakers' &&
                  mlConfidence >= 0.28) ||
              (mlSource == 'shoes_gate' &&
                  ml.$2 == 'shoes' &&
                  mlConfidence >= 0.28) ||
              (mlSource == 'silhouette' &&
                  {'dress', 'skirt', 'trousers', 'jeans'}.contains(ml.$2) &&
                  mlConfidence >= 0.40 &&
                  !hatLabels.contains(local.$2) &&
                  !bagLabels.contains(local.$2) &&
                  !(dressLabels.contains(ml.$2) &&
                      {'trousers', 'jeans', 'shorts'}.contains(local.$2))) ||
              (mlSource == 'lowerwear' &&
                  {'trousers', 'jeans', 'shorts', 'skirt'}.contains(ml.$2) &&
                  mlConfidence >= 0.40 &&
                  !hatLabels.contains(local.$2) &&
                  !bagLabels.contains(local.$2) &&
                  !(dressLabels.contains(local.$2) && ml.$2 == 'skirt')) ||
              (mlSource == 'accessory' &&
                  (bagLabels.contains(ml.$2) ||
                      {
                        'shoes',
                        'heels',
                        'sneakers',
                        'flats',
                        'boots',
                        'sandals',
                        'loafers',
                      }.contains(ml.$2)) &&
                  mlConfidence >= 0.40) ||
              (mlSource == 'imagenet' &&
                  mlIsAccessory &&
                  mlConfidence >= 0.18 &&
                  !localIsGarment) ||
              mlConfidence >= 0.62 &&
              !(mlSource == 'imagenet' &&
                  dressLabels.contains(ml.$2) &&
                  pantsLabels.contains(local.$2)) &&
              !(hatLabels.contains(ml.$2) && localIsGarment));
      if (trustMl) {
        category = ml.$1;
        subcategory = ml.$2;
        confidence = mlConfidence;
        usedFallback = false;
        message = mlMessage ?? 'Detected ${ml.$2}.';
      } else if (subcategory == unknownType || localConfidence < 0.42) {
        if (ml != null &&
            !mlUncertain &&
            ml.$2 != unknownType &&
            mlConfidence >= 0.40) {
          category = ml.$1;
          subcategory = ml.$2;
          confidence = mlConfidence;
          usedFallback = false;
          message = mlMessage ?? 'Detected ${ml.$2}.';
        } else {
          category = local.$1;
          subcategory = unknownType;
          confidence = localConfidence < mlConfidence ? mlConfidence : localConfidence;
          usedFallback = true;
          message = 'Uncertain. Please select the type.';
        }
      } else {
        message = 'Detected $subcategory.';
      }
    }

    if (subcategory != unknownType &&
        ml != null &&
        ml.$2 != subcategory &&
        (mlMessage ?? '').toLowerCase().contains(ml.$2) &&
        !(mlMessage ?? '').toLowerCase().contains(subcategory)) {
      message = 'Detected $subcategory.';
    }
    if (extraItemsMessage != null && extraItemsMessage.isNotEmpty) {
      message = '$message $extraItemsMessage';
    }
    return (
      category: category,
      subcategory: subcategory,
      confidence: confidence,
      usedFallback: usedFallback,
      message: message,
    );
  }

  static const List<String> styles = [
    'casual',
    'formal',
    'traditional',
    'streetwear',
    'minimal',
    'modest',
    'sporty',
    'ethnic',
    'smart',
  ];

  static const List<String> materials = [
    'cotton',
    'linen',
    'wool',
    'denim',
    'silk',
    'polyester',
    'leather',
    'knit',
    'chiffon',
    'unknown',
  ];

  static const List<String> patterns = [
    'solid',
    'striped',
    'checked',
    'floral',
    'printed',
    'multicolor',
    'gradient',
    'patterned',
    'polka dot',
    'graphic',
    'embroidered',
    'other',
  ];

  static String patternLabel(String pattern) => switch (pattern) {
        'solid' => 'Solid',
        'striped' => 'Striped',
        'checked' => 'Checked',
        'floral' => 'Floral',
        'printed' => 'Printed',
        'multicolor' => 'Multicolor',
        'gradient' => 'Gradient',
        'patterned' => 'Patterned',
        'polka dot' => 'Polka dot',
        'graphic' => 'Graphic',
        'embroidered' => 'Embroidered',
        'other' => 'Other',
        _ => pattern,
      };

  /// Default preferred subcategories by culture. Users can override.
  static List<String> preferredSubcategoriesFor(Culture culture) {
    return switch (culture) {
      Culture.pakistani => [
          'kurta',
          'kameez',
          'shalwar',
          'trousers',
          'modest dress',
          'dupatta',
          'khussa',
          'modest top',
          'shirt',
          'jacket',
          'coat',
          'scarf',
        ],
      Culture.indian => [
          'kurta',
          'kameez',
          'shalwar',
          'dupatta',
          'modest dress',
          'trousers',
          'shirt',
          'sandals',
        ],
      Culture.western => [
          't-shirt',
          'jeans',
          'jacket',
          'dress',
          'shirt',
          'skirt',
          'sneakers',
          'hoodie',
        ],
      Culture.middleEastern => [
          'abaya',
          'kaftan',
          'modest dress',
          'trousers',
          'shirt',
          'hijab',
          'scarf',
          'modest top',
        ],
      Culture.eastAsian => [
          'shirt',
          'trousers',
          'dress',
          'jacket',
          'sneakers',
          'blouse',
        ],
      Culture.african => [
          'kaftan',
          'dress',
          'shirt',
          'trousers',
          'modest dress',
          'sandals',
        ],
      Culture.other => subcategories.values.expand((e) => e).toList(),
    };
  }

  static List<String> modestExcludedSubcategories() => [
        'shorts',
        'skirt',
        'heels',
        'dress',
      ];

  static const typicallyFeminine = {
    'dress',
    'modest dress',
    'gown',
    'blouse',
    'skirt',
    'mini skirt',
    'miniskirt',
    'heels',
    'pumps',
    'stilettos',
    'jewelry',
    'jewellery',
    'hijab',
    'kaftan',
    'abaya',
    'palazzo',
    'leggings',
    'dupatta',
    'kameez',
    'crop top',
    'maxi',
    'romper',
    'jumpsuit',
    'flats',
    'modest top',
    'top',
    'tunic',
    'camisole',
    'sandals',
    'lehenga',
    'saree',
    'sari',
    'purse',
    'handbag',
    'clutch',
    'earrings',
    'earring',
    'necklace',
    'bangle',
    'anklet',
    'bracelet',
    'pendant',
    'brooch',
  };

  static const typicallyFeminineBags = {
    'bag',
    'purse',
    'handbag',
    'clutch',
    'tote',
    'shoulder bag',
    'crossbody',
    'sling bag',
    'sling',
    'bucket bag',
    'satchel',
  };

  static const typicallyMasculine = {
    'necktie',
    'tie',
    'bowtie',
    'bow tie',
    'cufflinks',
    'suspenders',
  };

  static const maleSafeBags = {
    'backpack',
    'messenger',
    'duffel',
    'laptop bag',
    'briefcase',
    'travel bag',
    'waist bag',
  };

  static bool mismatchesGender({
    required Gender? gender,
    required String subcategory,
    required ClothingCategory category,
    Culture? culture,
  }) {
    if (gender == null ||
        gender == Gender.nonBinary ||
        gender == Gender.preferNotToSay) {
      return false;
    }
    final sub = subcategory.toLowerCase().trim();
    if (gender == Gender.male) {
      if (category == ClothingCategory.dress) return true;
      if (typicallyFeminine.contains(sub)) return true;
      if (jewelryLabels.contains(sub)) return true;
      if (typicallyFeminineBags.contains(sub)) return true;
      if (bagLabels.contains(sub) && !maleSafeBags.contains(sub)) {
        return true;
      }
      if (sub.contains('dress') ||
          sub.contains('skirt') ||
          sub.contains('heel') ||
          sub.contains('blouse') ||
          sub.contains('gown') ||
          sub.contains('dupatta') ||
          sub.contains('kameez') ||
          sub.contains('saree') ||
          sub.contains('lehenga') ||
          sub.contains('sandal') ||
          sub.contains('purse') ||
          sub.contains('clutch') ||
          sub.contains('handbag')) {
        return true;
      }
      final southAsian =
          culture == Culture.pakistani || culture == Culture.indian;
      if (!southAsian && (sub == 'shalwar' || sub == 'khussa')) {
        return true;
      }
      return false;
    }
    if (gender == Gender.female) {
      if (typicallyMasculine.contains(sub)) return true;
      return false;
    }
    return false;
  }

  static String preferredOuterSubcategory({
    required Occasion occasion,
    required WeatherBand band,
  }) {
    if (band == WeatherBand.veryCold) return 'coat';
    if (band == WeatherBand.hot) return 'shirt';
    if (occasion == Occasion.office ||
        occasion == Occasion.formalEvent ||
        occasion == Occasion.wedding) {
      return 'blazer';
    }
    return 'jacket';
  }

  /// How well two garment colors sit together. Neutrals mix with anything.
  static double colorHarmonyScore(String a, String b) {
    final x = a.toLowerCase().trim();
    final y = b.toLowerCase().trim();
    if (x.isEmpty || y.isEmpty) return 0.7;
    if (x == y) return 1.0;
    const neutrals = {
      'black',
      'white',
      'grey',
      'gray',
      'navy',
      'beige',
      'cream',
      'brown',
      'khaki',
      'olive',
      'tan',
    };
    if (neutrals.contains(x) || neutrals.contains(y)) return 0.90;
    const friends = {
      'blue': {'navy', 'white', 'grey', 'khaki', 'brown'},
      'navy': {'white', 'grey', 'beige', 'brown', 'olive'},
      'olive': {'navy', 'brown', 'beige', 'cream', 'black'},
      'maroon': {'navy', 'grey', 'cream', 'black', 'beige'},
      'red': {'navy', 'black', 'grey', 'white'},
      'green': {'navy', 'beige', 'brown', 'white'},
    };
    if (friends[x]?.contains(y) == true || friends[y]?.contains(x) == true) {
      return 0.86;
    }
    return 0.52;
  }

  /// Piece is a poor match for this temperature / rain (hard drop).
  static bool mismatchesWeather({
    required String subcategory,
    required ClothingCategory category,
    required WeatherBand band,
    required bool rainy,
    List<WeatherBand> suitability = const [],
  }) {
    final sub = subcategory.toLowerCase().trim();
    if (rainy &&
        category == ClothingCategory.footwear &&
        {'sandals', 'heels', 'flats', 'pumps'}.contains(sub)) {
      return true;
    }
    if (band == WeatherBand.veryCold &&
        {'shorts', 'sandals', 'skirt', 'crop top', 'heels'}.contains(sub)) {
      return true;
    }
    if (band == WeatherBand.cold && {'shorts', 'sandals'}.contains(sub)) {
      return true;
    }
    if (band == WeatherBand.hot) {
      if (isOuterwear(sub) ||
          {
            'coat',
            'boots',
            'sweater',
            'hoodie',
            'jacket',
            'blazer',
            'cardigan',
            'scarf',
            'sweatshirt',
            'fleece',
          }.any((w) => sub.contains(w))) {
        return true;
      }
    }
    if (suitability.isNotEmpty && !suitability.contains(band)) {
      if (band == WeatherBand.veryCold &&
          suitability.contains(WeatherBand.cold)) {
        return false;
      }
      if (band == WeatherBand.cold &&
          (suitability.contains(WeatherBand.veryCold) ||
              suitability.contains(WeatherBand.mild))) {
        return false;
      }
      if (band == WeatherBand.mild &&
          (suitability.contains(WeatherBand.hot) ||
              suitability.contains(WeatherBand.cold))) {
        return false;
      }
      return true;
    }
    final inferred = weatherBandsForSubcategory(sub);
    return !inferred.contains(band) &&
        !(band == WeatherBand.cold && inferred.contains(WeatherBand.veryCold)) &&
        !(band == WeatherBand.veryCold && inferred.contains(WeatherBand.cold));
  }

  /// Piece clashes with the event type (hard drop).
  static bool mismatchesOccasion({
    required String subcategory,
    required Formality formality,
    required Occasion occasion,
  }) {
    final sub = subcategory.toLowerCase().trim();
    final beachy = {'shorts', 'sandals', 'crop top'}.contains(sub);
    return switch (occasion) {
      Occasion.office =>
        beachy ||
            sub == 'hoodie' ||
            sub == 't-shirt' ||
            formality == Formality.athletic,
      Occasion.formalEvent || Occasion.wedding =>
        beachy ||
            sub == 'hoodie' ||
            {'t-shirt', 'sneakers', 'jeans'}.contains(sub) ||
            formality == Formality.athletic,
      Occasion.religiousEvent =>
        {'shorts', 'crop top', 'heels', 'mini skirt'}.contains(sub),
      Occasion.sports || Occasion.outdoorActivity =>
        {'heels', 'gown', 'dress', 'blazer', 'dupatta'}.contains(sub) ||
            formality == Formality.formal,
      Occasion.university => sub == 'gown',
      _ => false,
    };
  }

  static ClothingCategory categoryOf(String subcategory) {
    final sub = subcategory.toLowerCase().trim();
    for (final entry in subcategories.entries) {
      if (entry.value.contains(sub)) return entry.key;
    }
    if (dressLabels.contains(sub) || sub.contains('dress') || sub.contains('gown')) {
      return ClothingCategory.dress;
    }
    if (skirtLabels.contains(sub)) return ClothingCategory.lowerwear;
    return ClothingCategory.upperwear;
  }

  static bool isFeminineForMale(
    String subcategory, [
    ClothingCategory? category,
    Culture? culture,
  ]) {
    return mismatchesGender(
      gender: Gender.male,
      subcategory: subcategory,
      category: category ?? categoryOf(subcategory),
      culture: culture,
    );
  }

  static List<String> genderSafePreferred({
    required Gender? gender,
    required Iterable<String> subcategories,
    Culture? culture,
  }) {
    if (gender != Gender.male) return subcategories.toList();
    return subcategories
        .where((s) => !isFeminineForMale(s, null, culture))
        .toList();
  }

  static String preferredFillSubcategory({
    required ClothingCategory category,
    required Gender? gender,
    required Occasion occasion,
    required WeatherBand band,
  }) {
    final formal = occasion == Occasion.office ||
        occasion == Occasion.formalEvent ||
        occasion == Occasion.wedding;
    if (gender == Gender.male) {
      return switch (category) {
        ClothingCategory.upperwear => formal
            ? 'shirt'
            : band == WeatherBand.hot
                ? 't-shirt'
                : (band == WeatherBand.veryCold || band == WeatherBand.cold)
                    ? 'sweater'
                    : 'shirt',
        ClothingCategory.lowerwear => formal ? 'trousers' : 'jeans',
        ClothingCategory.footwear => formal
            ? 'loafers'
            : (band == WeatherBand.veryCold || band == WeatherBand.cold)
                ? 'boots'
                : 'sneakers',
        ClothingCategory.accessories => 'watch',
        ClothingCategory.dress => 'shirt',
      };
    }
    return switch (category) {
      ClothingCategory.upperwear => formal ? 'blouse' : 'kameez',
      ClothingCategory.lowerwear => formal ? 'trousers' : 'shalwar',
      ClothingCategory.footwear => formal
          ? 'heels'
          : (band == WeatherBand.veryCold || band == WeatherBand.cold)
              ? 'boots'
              : 'sandals',
      ClothingCategory.accessories => 'dupatta',
      ClothingCategory.dress => 'dress',
    };
  }

  static List<String> preferredSubcategoriesForGender(Gender? gender) {
    return switch (gender) {
      Gender.male => [
          'shirt',
          't-shirt',
          'kurta',
          'trousers',
          'jeans',
          'chinos',
          'sneakers',
          'shoes',
          'loafers',
          'jacket',
          'coat',
          'hoodie',
        ],
      Gender.female => [
          'kameez',
          'shalwar',
          'kurta',
          'blouse',
          'dress',
          'modest dress',
          'dupatta',
          'sandals',
          'heels',
          'skirt',
          'modest top',
        ],
      _ => const [],
    };
  }

  static double genderScore({
    required Gender? gender,
    required String subcategory,
    required ClothingCategory category,
    Culture? culture,
  }) {
    if (mismatchesGender(
      gender: gender,
      subcategory: subcategory,
      category: category,
      culture: culture,
    )) {
      return 0.05;
    }
    final preferred = preferredSubcategoriesForGender(gender)
        .map((e) => e.toLowerCase())
        .toSet();
    if (preferred.contains(subcategory.toLowerCase())) return 1.0;
    return 0.75;
  }

  static const Map<SkinTone, Map<String, double>> skinToneColorScores = {
    SkinTone.veryLight: {
      'navy': 0.95,
      'black': 0.78,
      'blue': 0.9,
      'pink': 0.88,
      'purple': 0.86,
      'grey': 0.84,
      'white': 0.8,
      'maroon': 0.82,
      'teal': 0.85,
      'beige': 0.7,
      'yellow': 0.62,
      'orange': 0.55,
      'red': 0.72,
      'green': 0.74,
      'brown': 0.68,
      'cream': 0.8,
      'olive': 0.66,
      'gold': 0.7,
    },
    SkinTone.light: {
      'navy': 0.92,
      'blue': 0.9,
      'teal': 0.88,
      'pink': 0.86,
      'white': 0.84,
      'grey': 0.82,
      'maroon': 0.8,
      'black': 0.78,
      'green': 0.76,
      'beige': 0.74,
      'purple': 0.8,
      'red': 0.7,
      'cream': 0.82,
      'brown': 0.7,
      'gold': 0.72,
      'yellow': 0.64,
      'orange': 0.6,
      'olive': 0.68,
    },
    SkinTone.medium: {
      'white': 0.9,
      'navy': 0.88,
      'red': 0.86,
      'green': 0.84,
      'gold': 0.88,
      'maroon': 0.85,
      'blue': 0.82,
      'cream': 0.84,
      'teal': 0.8,
      'black': 0.78,
      'purple': 0.76,
      'beige': 0.8,
      'orange': 0.74,
      'brown': 0.78,
      'olive': 0.8,
      'yellow': 0.72,
      'grey': 0.74,
      'pink': 0.7,
    },
    SkinTone.tan: {
      'white': 0.92,
      'cream': 0.9,
      'gold': 0.9,
      'orange': 0.86,
      'green': 0.84,
      'navy': 0.82,
      'brown': 0.84,
      'maroon': 0.8,
      'teal': 0.8,
      'red': 0.78,
      'olive': 0.86,
      'yellow': 0.8,
      'blue': 0.76,
      'beige': 0.82,
      'black': 0.74,
      'purple': 0.7,
      'grey': 0.68,
      'pink': 0.66,
    },
    SkinTone.brown: {
      'gold': 0.94,
      'white': 0.92,
      'cream': 0.9,
      'orange': 0.88,
      'yellow': 0.86,
      'green': 0.84,
      'red': 0.82,
      'navy': 0.8,
      'maroon': 0.84,
      'teal': 0.8,
      'olive': 0.82,
      'brown': 0.7,
      'blue': 0.76,
      'beige': 0.74,
      'purple': 0.72,
      'black': 0.78,
      'grey': 0.66,
      'pink': 0.64,
    },
    SkinTone.deep: {
      'white': 0.96,
      'gold': 0.94,
      'cream': 0.9,
      'yellow': 0.88,
      'orange': 0.86,
      'red': 0.84,
      'green': 0.82,
      'teal': 0.84,
      'navy': 0.8,
      'maroon': 0.82,
      'purple': 0.8,
      'blue': 0.78,
      'pink': 0.76,
      'olive': 0.74,
      'beige': 0.68,
      'grey': 0.64,
      'brown': 0.6,
      'black': 0.7,
    },
  };

  static double colorScoreForSkin(SkinTone tone, String color) {
    final map = skinToneColorScores[tone] ?? const {};
    return map[color.toLowerCase()] ?? 0.65;
  }

  static bool isOuterwear(String subcategory) {
    final s = subcategory.toLowerCase().trim();
    if (s.contains('jacket') ||
        s.contains('blazer') ||
        s.contains('coat') ||
        s.contains('cardigan') ||
        s.contains('hoodie') ||
        s.contains('sweater') ||
        s.contains('sweatshirt') ||
        s.contains('windbreaker') ||
        s.contains('fleece') ||
        s.contains('parka') ||
        s.contains('overcoat') ||
        s.contains('shacket') ||
        s.contains('waistcoat') ||
        s.contains('vest')) {
      return true;
    }
    const outer = {
      'jacket',
      'blazer',
      'coat',
      'cardigan',
      'hoodie',
      'sweater',
      'sweatshirt',
      'windbreaker',
      'fleece',
    };
    return outer.contains(s);
  }

  static bool isBaseUpper(String subcategory) {
    return !isOuterwear(subcategory);
  }

  static List<WeatherBand> weatherBandsForSubcategory(String subcategory) {
    final s = subcategory.toLowerCase().trim();
    if (s.contains('coat') ||
        s.contains('boots') ||
        s.contains('sweater') ||
        s.contains('hoodie') ||
        s.contains('scarf') ||
        s.contains('gloves') ||
        s.contains('beanie') ||
        s.contains('fleece') ||
        s.contains('sweatshirt')) {
      return [WeatherBand.veryCold, WeatherBand.cold];
    }
    if (s.contains('jacket') ||
        s.contains('blazer') ||
        s.contains('cardigan') ||
        s.contains('windbreaker') ||
        s.contains('shacket')) {
      return [WeatherBand.veryCold, WeatherBand.cold, WeatherBand.mild];
    }
    if (s.contains('short') ||
        s.contains('sandal') ||
        s.contains('t-shirt') ||
        s.contains('tshirt') ||
        s.contains('tank') ||
        s.contains('crop top') ||
        s.contains('polo')) {
      return [WeatherBand.mild, WeatherBand.hot];
    }
    if (s.contains('kurta') ||
        s.contains('kameez') ||
        s.contains('shirt') ||
        s.contains('blouse') ||
        s.contains('modest top') ||
        s.contains('trousers') ||
        s.contains('pants') ||
        s.contains('jeans') ||
        s.contains('chinos') ||
        s.contains('sneakers') ||
        s.contains('shoes') ||
        s.contains('loafers')) {
      return [WeatherBand.mild, WeatherBand.hot, WeatherBand.cold];
    }
    return [WeatherBand.mild, WeatherBand.hot];
  }

  static List<Season> seasonsForSubcategory(String subcategory) {
    final bands = weatherBandsForSubcategory(subcategory);
    final seasons = <Season>{};
    if (bands.contains(WeatherBand.hot) || bands.contains(WeatherBand.mild)) {
      seasons.addAll([Season.spring, Season.summer]);
    }
    if (bands.contains(WeatherBand.cold) ||
        bands.contains(WeatherBand.veryCold)) {
      seasons.addAll([Season.autumn, Season.winter]);
    }
    if (seasons.isEmpty) return Season.values;
    return seasons.toList();
  }

  static Formality formalityForSubcategory(String subcategory) {
    final s = subcategory.toLowerCase();
    if (['gown', 'blazer', 'heels', 'dress'].contains(s)) {
      return Formality.formal;
    }
    if (['sneakers', 'hoodie', 'shorts', 't-shirt'].contains(s)) {
      return Formality.casual;
    }
    if (['abaya', 'hijab', 'modest dress', 'kaftan'].contains(s)) {
      return Formality.religious;
    }
    if (['shirt', 'trousers', 'chinos', 'loafers', 'kurta'].contains(s)) {
      return Formality.smartCasual;
    }
    return Formality.casual;
  }

  static List<Occasion> occasionsForSubcategory(String subcategory) {
    return switch (formalityForSubcategory(subcategory)) {
      Formality.formal => [
          Occasion.formalEvent,
          Occasion.wedding,
          Occasion.office,
          Occasion.party,
          Occasion.date,
        ],
      Formality.smartCasual => [
          Occasion.office,
          Occasion.university,
          Occasion.casualDayOut,
          Occasion.travel,
          Occasion.date,
          Occasion.party,
        ],
      Formality.athletic => [
          Occasion.sports,
          Occasion.outdoorActivity,
          Occasion.travel,
        ],
      Formality.religious => [
          Occasion.religiousEvent,
          Occasion.casualDayOut,
          Occasion.university,
        ],
      Formality.casual => [
          Occasion.casualDayOut,
          Occasion.university,
          Occasion.travel,
          Occasion.outdoorActivity,
          Occasion.party,
        ],
    };
  }

  static WeatherBand bandFromTemperature(double celsius) {
    if (celsius <= 10) return WeatherBand.veryCold;
    if (celsius <= 18) return WeatherBand.cold;
    if (celsius <= 23) return WeatherBand.mild;
    return WeatherBand.hot;
  }

  static Season seasonFromDate(DateTime date, {required bool southernHemisphere}) {
    final month = date.month;
    if (southernHemisphere) {
      if (month >= 3 && month <= 5) return Season.autumn;
      if (month >= 6 && month <= 8) return Season.winter;
      if (month >= 9 && month <= 11) return Season.spring;
      return Season.summer;
    }
    if (month >= 3 && month <= 5) return Season.spring;
    if (month >= 6 && month <= 8) return Season.summer;
    if (month >= 9 && month <= 11) return Season.autumn;
    return Season.winter;
  }

  static double occasionScore(Formality formality, Occasion occasion) {
    return switch (occasion) {
      Occasion.office => switch (formality) {
          Formality.smartCasual => 0.95,
          Formality.formal => 0.9,
          Formality.casual => 0.45,
          Formality.athletic => 0.2,
          Formality.religious => 0.55,
        },
      Occasion.university => switch (formality) {
          Formality.casual => 0.92,
          Formality.smartCasual => 0.88,
          Formality.athletic => 0.7,
          Formality.formal => 0.4,
          Formality.religious => 0.75,
        },
      Occasion.formalEvent || Occasion.wedding => switch (formality) {
          Formality.formal => 0.98,
          Formality.smartCasual => 0.7,
          Formality.religious => 0.85,
          Formality.casual => 0.25,
          Formality.athletic => 0.1,
        },
      Occasion.religiousEvent => switch (formality) {
          Formality.religious => 0.98,
          Formality.smartCasual => 0.8,
          Formality.formal => 0.75,
          Formality.casual => 0.45,
          Formality.athletic => 0.15,
        },
      Occasion.sports || Occasion.outdoorActivity => switch (formality) {
          Formality.athletic => 0.98,
          Formality.casual => 0.75,
          Formality.smartCasual => 0.4,
          Formality.formal => 0.1,
          Formality.religious => 0.35,
        },
      Occasion.party || Occasion.date => switch (formality) {
          Formality.smartCasual => 0.9,
          Formality.formal => 0.84,
          Formality.casual => 0.7,
          Formality.religious => 0.6,
          Formality.athletic => 0.2,
        },
      _ => switch (formality) {
          Formality.casual => 0.9,
          Formality.smartCasual => 0.82,
          Formality.religious => 0.75,
          Formality.athletic => 0.55,
          Formality.formal => 0.5,
        },
    };
  }

  /// Silhouette compatibility. Neutral 0.72 when the user has not set a type.
  static double bodyTypeScore({
    required BodyType? bodyType,
    required String subcategory,
    required ClothingCategory category,
    Gender? gender,
  }) {
    if (bodyType == null) return 0.72;
    if (category == ClothingCategory.footwear ||
        category == ClothingCategory.accessories) {
      return 0.80;
    }
    final sub = subcategory.toLowerCase().trim();
    if (gender == Gender.male &&
        mismatchesGender(
          gender: Gender.male,
          subcategory: sub,
          category: category,
        )) {
      return 0.05;
    }
    const fitted = {
      'dress',
      'gown',
      'modest dress',
      'kurta',
      'kameez',
      'shirt',
      'blouse',
      'jeans',
      'trousers',
    };
    const structuredUpper = {
      'jacket',
      'blazer',
      'coat',
      'cardigan',
      'shirt',
      'blouse',
      'modest top',
    };
    const aLineLower = {
      'skirt',
      'palazzo',
      'wide trousers',
      'trousers',
      'shalwar',
    };
    const bulkyUpper = {'hoodie', 'sweater', 'jacket', 'coat'};
    const clingy = {'t-shirt', 'crop top', 'shorts', 'leggings'};
    const maleStructured = {'shirt', 'jacket', 'blazer', 'coat', 'kurta'};
    const maleLower = {'trousers', 'chinos', 'jeans', 'shalwar'};
    if (gender == Gender.male) {
      return switch (bodyType) {
        BodyType.rectangle => maleStructured.contains(sub) || maleLower.contains(sub)
            ? 0.92
            : clingy.contains(sub)
                ? 0.62
                : 0.78,
        BodyType.pear =>
          maleStructured.contains(sub) || sub == 'jacket' || sub == 'blazer'
              ? 0.94
              : (sub == 'shorts' || sub == 'leggings')
                  ? 0.52
                  : 0.74,
        BodyType.invertedTriangle => maleLower.contains(sub)
            ? 0.93
            : {'hoodie', 'sweater', 'jacket', 'coat'}.contains(sub)
                ? 0.58
                : 0.74,
        BodyType.hourglass =>
          sub == 'shirt' || maleLower.contains(sub) || sub == 'kurta'
              ? 0.95
              : bulkyUpper.contains(sub)
                  ? 0.58
                  : 0.76,
        BodyType.apple =>
          maleStructured.contains(sub) || maleLower.contains(sub)
              ? 0.93
              : clingy.contains(sub)
                  ? 0.48
                  : 0.73,
      };
    }
    return switch (bodyType) {
      BodyType.rectangle => structuredUpper.contains(sub) ||
              sub.contains('dress') ||
              sub == 'trousers' ||
              sub == 'jeans'
          ? 0.92
          : clingy.contains(sub)
              ? 0.62
              : 0.78,
      BodyType.pear => structuredUpper.contains(sub) || aLineLower.contains(sub)
          ? 0.94
          : (sub == 'shorts' || sub == 'leggings' || sub == 'skinny')
              ? 0.52
              : 0.74,
      BodyType.invertedTriangle => aLineLower.contains(sub) ||
              sub == 'skirt' ||
              sub == 'palazzo' ||
              sub == 'dress'
          ? 0.93
          : bulkyUpper.contains(sub)
              ? 0.55
              : 0.74,
      BodyType.hourglass => fitted.contains(sub) ||
              sub.contains('dress') ||
              sub == 'skirt'
          ? 0.95
          : bulkyUpper.contains(sub)
              ? 0.58
              : 0.76,
      BodyType.apple => sub.contains('dress') ||
              sub == 'kurta' ||
              sub == 'modest top' ||
              structuredUpper.contains(sub) ||
              sub == 'trousers'
          ? 0.93
          : clingy.contains(sub)
              ? 0.48
              : 0.73,
    };
  }
}

class RecommendationWeights {
  const RecommendationWeights({
    this.weather = 0.32,
    this.culture = 0.12,
    this.occasion = 0.22,
    this.color = 0.10,
    this.preference = 0.08,
    this.wardrobe = 0.08,
    this.bodyType = 0.08,
  });

  final double weather;
  final double culture;
  final double occasion;
  final double color;
  final double preference;
  final double wardrobe;
  final double bodyType;

  double get sum =>
      weather + culture + occasion + color + preference + wardrobe + bodyType;

  factory RecommendationWeights.fromJson(Map<String, dynamic> json) {
    return RecommendationWeights(
      weather: (json['weather'] as num?)?.toDouble() ?? 0.32,
      culture: (json['culture'] as num?)?.toDouble() ?? 0.12,
      occasion: (json['occasion'] as num?)?.toDouble() ?? 0.22,
      color: (json['color'] as num?)?.toDouble() ?? 0.10,
      preference: (json['preference'] as num?)?.toDouble() ?? 0.08,
      wardrobe: (json['wardrobe'] as num?)?.toDouble() ?? 0.08,
      bodyType: (json['bodyType'] as num?)?.toDouble() ??
          (json['body_type'] as num?)?.toDouble() ??
          0.08,
    );
  }

  Map<String, dynamic> toJson() => {
        'weather': weather,
        'culture': culture,
        'occasion': occasion,
        'color': color,
        'preference': preference,
        'wardrobe': wardrobe,
        'bodyType': bodyType,
      };
}

import 'dart:convert';
import 'dart:math';

import 'package:flutter/services.dart';

import '../models/outfit_model.dart';
import '../models/product_model.dart';
import '../models/user_model.dart';
import '../models/wardrobe_item.dart';
import '../models/weather_model.dart';
import '../utils/clothing_catalog.dart';
import '../utils/constants.dart';
import '../utils/enums.dart';

/// Rule-based + scoring recommendation engine.
/// Image ML is separate; this service ranks complete outfits.
class RecommendationService {
  RecommendationService({RecommendationWeights? weights}) : _weights = weights;

  RecommendationWeights? _weights;

  Future<RecommendationWeights> weights() async {
    if (_weights != null) return _weights!;
    final raw =
        await rootBundle.loadString('assets/data/recommendation_weights.json');
    _weights = RecommendationWeights.fromJson(
      jsonDecode(raw) as Map<String, dynamic>,
    );
    return _weights!;
  }

  Future<RecommendationResult> recommend({
    required UserModel user,
    required List<WardrobeItem> wardrobe,
    required WeatherModel weather,
    required Occasion occasion,
    List<OutfitFeedback> feedback = const [],
    List<TrendModel> trends = const [],
    List<ProductModel> products = const [],
    int rotation = 0,
    Set<String> excludeIds = const {},
    WeatherBand? weatherBandOverride,
    bool? rainyOverride,
    bool? modestOverride,
    List<String> extraFavoriteColors = const [],
    String? styleHint,
    bool wantsOuterwear = false,
    List<String> garmentHints = const [],
  }) async {
    final w = await weights();
    final effectiveTemp = weather.feelsLike > weather.temperature
        ? weather.feelsLike
        : weather.temperature;
    final band = weatherBandOverride ??
        ClothingCatalog.bandFromTemperature(effectiveTemp);
    final rainy = rainyOverride ?? weather.isRainy;
    var scoringUser = user;
    if (modestOverride != null) {
      scoringUser = user.copyWith(
        preferences: user.preferences.copyWith(
          modestPreference: modestOverride,
        ),
      );
    }
    if (extraFavoriteColors.isNotEmpty) {
      scoringUser = scoringUser.copyWith(
        preferences: scoringUser.preferences.copyWith(
          favoriteColors: {
            ...scoringUser.preferences.favoriteColors,
            ...extraFavoriteColors,
          }.toList(),
        ),
      );
    }
    final southern = weather.latitude < 0;
    final calendarSeason = ClothingCatalog.seasonFromDate(
      DateTime.now(),
      southernHemisphere: southern,
    );
    // Actual weather outranks calendar season.
    final season = _seasonFromBand(band, calendarSeason);
    final preferred = {
      ...scoringUser.effectivePreferredSubcategories().map((e) => e.toLowerCase()),
      ...ClothingCatalog.preferredSubcategoriesForGender(scoringUser.gender)
          .map((e) => e.toLowerCase()),
      ...garmentHints.map((e) => e.toLowerCase()),
    };
    final excludedTypes = {
      ...scoringUser.preferences.excludedItemTypes.map((e) => e.toLowerCase()),
      if (scoringUser.preferences.modestPreference)
        ...ClothingCatalog.modestExcludedSubcategories(),
    };
    final excludedStyles =
        scoringUser.preferences.excludedStyles.map((e) => e.toLowerCase()).toSet();

    final filtered = wardrobe.where((item) {
      return !_isHardFiltered(
        item: item,
        user: scoringUser,
        band: band,
        rainy: rainy,
        excludedTypes: excludedTypes,
        excludedStyles: excludedStyles,
        occasion: occasion,
        allowHotOuterwear: wantsOuterwear,
      );
    }).toList();

    if (wardrobe.isEmpty || filtered.isEmpty) {
      return RecommendationResult(
        outfits: [
          _shopFallbackOutfit(
            user: user,
            weather: weather,
            occasion: occasion,
            band: band,
            products: products,
            w: w,
          ),
        ],
        occasion: occasion,
        generatedAt: DateTime.now(),
        emptyWardrobe: true,
      );
    }

    final uppers = filtered
        .where((i) => i.category == ClothingCategory.upperwear)
        .toList();
    final baseUppers = uppers
        .where((i) => ClothingCatalog.isBaseUpper(i.subcategory))
        .toList();
    final outers = uppers
        .where((i) => ClothingCatalog.isOuterwear(i.subcategory))
        .toList();
    final shirtLike = (band == WeatherBand.hot || (!wantsOuterwear && band == WeatherBand.mild))
        ? baseUppers
        : (baseUppers.isNotEmpty ? baseUppers : uppers);
    final lowers = filtered
        .where((i) => i.category == ClothingCategory.lowerwear)
        .toList();
    final shoes = filtered
        .where((i) => i.category == ClothingCategory.footwear)
        .toList();
    final accessories = filtered
        .where((i) => i.category == ClothingCategory.accessories)
        .toList();
    final dresses =
        filtered.where((i) => i.category == ClothingCategory.dress).toList();

    final candidates = <OutfitRecommendation>[];

    void consider({
      WardrobeItem? upper,
      WardrobeItem? outer,
      WardrobeItem? lower,
      WardrobeItem? dress,
      WardrobeItem? shoe,
      WardrobeItem? accessory,
      bool requireOuter = false,
    }) {
      final slots = <OutfitSlot>[
        if (dress != null)
          OutfitSlot(category: ClothingCategory.dress, item: dress)
        else ...[
          OutfitSlot(
            category: ClothingCategory.upperwear,
            item: upper,
            missingSuggestion: upper == null
                ? _missing(
                    ClothingCategory.upperwear,
                    user,
                    band,
                    occasion,
                    products,
                    rainy: rainy,
                    preferredSubcategory:
                        garmentHints.contains('shirt') ? 'shirt' : null,
                  )
                : null,
          ),
          if (outer != null ||
              requireOuter ||
              (wantsOuterwear && dress == null))
            OutfitSlot(
              category: ClothingCategory.upperwear,
              item: outer,
              missingSuggestion: outer == null
                  ? _missing(
                      ClothingCategory.upperwear,
                      user,
                      band,
                      occasion,
                      products,
                      rainy: rainy,
                      preferredSubcategory:
                          ClothingCatalog.preferredOuterSubcategory(
                        occasion: occasion,
                        band: band,
                      ),
                      paletteColors: [
                        if (upper != null) upper.color,
                        if (lower != null) lower.color,
                        if (shoe != null) shoe.color,
                      ],
                    )
                  : null,
            ),
          OutfitSlot(
            category: ClothingCategory.lowerwear,
            item: lower,
            missingSuggestion: lower == null
                ? _missing(
                    ClothingCategory.lowerwear,
                    user,
                    band,
                    occasion,
                    products,
                    rainy: rainy,
                  )
                : null,
          ),
        ],
        OutfitSlot(
          category: ClothingCategory.footwear,
          item: shoe,
          missingSuggestion: shoe == null
              ? _missing(
                  ClothingCategory.footwear,
                  user,
                  band,
                  occasion,
                  products,
                  rainy: rainy,
                )
              : null,
        ),
        if (accessory != null)
          OutfitSlot(
            category: ClothingCategory.accessories,
            item: accessory,
          )
        else if (user.gender != Gender.male &&
            (user.culture == Culture.pakistani ||
                user.culture == Culture.indian ||
                user.preferences.modestPreference))
          OutfitSlot(
            category: ClothingCategory.accessories,
            missingSuggestion: _missing(
              ClothingCategory.accessories,
              user,
              band,
              occasion,
              products,
              rainy: rainy,
              preferredSubcategory: 'dupatta',
            ),
          ),
      ];

      final items = slots.map((s) => s.item).whereType<WardrobeItem>().toList();
      if (items.isEmpty) return;

      final breakdown = _score(
        items: items,
        user: scoringUser,
        weather: weather,
        occasion: occasion,
        band: band,
        rainy: rainy,
        season: season,
        preferred: preferred,
        feedback: feedback,
        trends: trends,
        weights: w,
        slots: slots,
        wantsOuterwear: wantsOuterwear,
        styleHint: styleHint,
      );
      candidates.add(
        OutfitRecommendation(
          id: items.map((e) => e.itemId).join('-'),
          title: _titleFor(candidates.length, breakdown.percent),
          slots: slots,
          breakdown: breakdown,
          explanations: _explanations(
            user: scoringUser,
            weather: weather,
            occasion: occasion,
            items: items,
            slots: slots,
            season: season,
            band: band,
          ),
          fromWardrobe: slots.every((s) =>
              s.category == ClothingCategory.accessories ||
              s.filledFromWardrobe),
        ),
      );
    }

    final rng = Random(rotation == 0 ? 7 : rotation);
    final coldLayer = band == WeatherBand.cold || band == WeatherBand.veryCold;
    final shouldLayer = wantsOuterwear || coldLayer;
    final topUppers = _topN(
      shirtLike,
      min(8, shirtLike.length),
      scoringUser,
      weather,
      occasion,
      band,
      preferred,
    );
    final topOuters = _topN(
      outers,
      min(4, outers.length),
      scoringUser,
      weather,
      occasion,
      band,
      preferred,
    );
    final topLowers = _topN(
      lowers,
      min(8, lowers.length),
      scoringUser,
      weather,
      occasion,
      band,
      preferred,
    );
    final topShoes = _topN(
      shoes,
      min(6, shoes.length),
      scoringUser,
      weather,
      occasion,
      band,
      preferred,
    );
    final topDresses = _topN(
      dresses,
      min(6, dresses.length),
      scoringUser,
      weather,
      occasion,
      band,
      preferred,
    );
    final topAcc = _topN(
      accessories,
      min(4, accessories.length),
      scoringUser,
      weather,
      occasion,
      band,
      preferred,
    );

    var produced = 0;
    if (user.gender == Gender.female || user.gender == Gender.nonBinary) {
      for (final dress in [...topDresses, if (topDresses.isEmpty) null]) {
        for (final shoe in [...topShoes, if (topShoes.isEmpty) null]) {
          for (final acc in [...topAcc, null]) {
            if (dress == null && topDresses.isEmpty) continue;
            if (dress != null) {
              consider(dress: dress, shoe: shoe, accessory: acc);
              produced++;
              if (produced >= AppConstants.maxOutfitCombinations) break;
            }
          }
        }
      }
    }
    for (final upper in [...topUppers, if (topUppers.isEmpty) null]) {
      for (final lower in [...topLowers, if (topLowers.isEmpty) null]) {
        for (final shoe in [...topShoes, if (topShoes.isEmpty) null]) {
          final accPool = topAcc
              .where(
                (a) => !ClothingCatalog.mismatchesGender(
                  gender: scoringUser.gender,
                  subcategory: a.subcategory,
                  category: a.category,
                  culture: scoringUser.culture,
                ),
              )
              .toList();
          final acc =
              accPool.isEmpty ? null : accPool[rng.nextInt(accPool.length)];
          final upperIsOuter = upper != null &&
              ClothingCatalog.isOuterwear(upper.subcategory);
          if (shouldLayer && !upperIsOuter) {
            final outerChoices = _matchingOuters(
              outers: topOuters,
              upper: upper,
              lower: lower,
              shoe: shoe,
              user: scoringUser,
              weather: weather,
              occasion: occasion,
              band: band,
              preferred: preferred,
            );
            final choices = outerChoices.isEmpty
                ? <WardrobeItem?>[null]
                : outerChoices.cast<WardrobeItem?>();
            for (final outer in choices) {
              consider(
                upper: upper,
                outer: outer,
                lower: lower,
                shoe: shoe,
                accessory: acc,
                requireOuter: true,
              );
              produced++;
              if (produced >= AppConstants.maxOutfitCombinations) break;
            }
            if (!coldLayer && !wantsOuterwear) {
              consider(upper: upper, lower: lower, shoe: shoe, accessory: acc);
              produced++;
            }
          } else {
            consider(upper: upper, lower: lower, shoe: shoe, accessory: acc);
            produced++;
          }
          if (produced >= AppConstants.maxOutfitCombinations) break;
        }
      }
    }

    candidates.sort(
      (a, b) => b.breakdown.finalScore.compareTo(a.breakdown.finalScore),
    );
    final unique = <String, OutfitRecommendation>{};
    for (final c in candidates) {
      unique.putIfAbsent(c.id, () => c);
    }
    var pool = unique.values.toList();
    if (excludeIds.isNotEmpty) {
      final fresh = pool.where((o) => !excludeIds.contains(o.id)).toList();
      if (fresh.length >= AppConstants.rankedOutfitCount) {
        pool = fresh;
      } else if (fresh.isNotEmpty) {
        pool = [
          ...fresh,
          ...pool.where((o) => excludeIds.contains(o.id)),
        ];
      }
    }
    pool.sort((a, b) => b.breakdown.finalScore.compareTo(a.breakdown.finalScore));
    pool = pool
        .map((o) => _stripGenderMismatches(o, scoringUser))
        .whereType<OutfitRecommendation>()
        .toList();
    var ranked = _diversePick(pool, AppConstants.rankedOutfitCount);
    for (var i = 0; i < ranked.length; i++) {
      ranked[i] = OutfitRecommendation(
        id: ranked[i].id,
        title: _titleFor(i, ranked[i].breakdown.percent),
        slots: ranked[i].slots,
        breakdown: ranked[i].breakdown,
        explanations: ranked[i].explanations,
        fromWardrobe: ranked[i].fromWardrobe,
      );
    }

    if (ranked.isEmpty) {
      ranked = [
        _shopFallbackOutfit(
          user: user,
          weather: weather,
          occasion: occasion,
          band: band,
          products: products,
          w: w,
        ),
      ];
    }

    return RecommendationResult(
      outfits: ranked,
      occasion: occasion,
      generatedAt: DateTime.now(),
      emptyWardrobe: false,
    );
  }

  List<OutfitRecommendation> _diversePick(
    List<OutfitRecommendation> pool,
    int count,
  ) {
    if (pool.length <= count) return [...pool];
    final leftover = [...pool];
    final picked = <OutfitRecommendation>[leftover.removeAt(0)];
    while (picked.length < count && leftover.isNotEmpty) {
      leftover.sort((a, b) {
        final da = _novelty(a, picked);
        final db = _novelty(b, picked);
        final byNovelty = db.compareTo(da);
        if (byNovelty != 0) return byNovelty;
        return b.breakdown.finalScore.compareTo(a.breakdown.finalScore);
      });
      picked.add(leftover.removeAt(0));
    }
    return picked;
  }

  double _novelty(
    OutfitRecommendation next,
    List<OutfitRecommendation> picked,
  ) {
    final nextIds = next.id.split('-').toSet();
    var overlap = 0.0;
    for (final existing in picked) {
      final ids = existing.id.split('-').toSet();
      overlap += nextIds.intersection(ids).length / max(1, nextIds.length);
    }
    return next.breakdown.finalScore - (overlap / picked.length);
  }

  bool _isHardFiltered({
    required WardrobeItem item,
    required UserModel user,
    required WeatherBand band,
    required bool rainy,
    required Set<String> excludedTypes,
    required Set<String> excludedStyles,
    required Occasion occasion,
    bool allowHotOuterwear = false,
  }) {
    if (ClothingCatalog.mismatchesGender(
      gender: user.gender,
      subcategory: item.subcategory,
      category: item.category,
      culture: user.culture,
    )) {
      return true;
    }
    final sub = item.subcategory.toLowerCase();
    if (excludedTypes.contains(sub) || excludedTypes.contains(item.category.name)) {
      return true;
    }
    if (excludedStyles.contains(item.style.toLowerCase())) return true;

    if (ClothingCatalog.mismatchesOccasion(
      subcategory: item.subcategory,
      formality: item.formality,
      occasion: occasion,
    )) {
      return true;
    }
    if (ClothingCatalog.mismatchesWeather(
      subcategory: item.subcategory,
      category: item.category,
      band: band,
      rainy: rainy,
      suitability: item.weatherSuitability,
    )) {
      return true;
    }
    final isOuter = ClothingCatalog.isOuterwear(sub);
    final isCold = band == WeatherBand.cold || band == WeatherBand.veryCold;
    if (!allowHotOuterwear && !isCold && isOuter) {
      return true;
    }
    return false;
  }

  List<WardrobeItem> _topN(
    List<WardrobeItem> items,
    int n,
    UserModel user,
    WeatherModel weather,
    Occasion occasion,
    WeatherBand band,
    Set<String> preferred,
  ) {
    final scored = [...items]..sort((a, b) {
        return _itemSoftScore(b, user, weather, occasion, band, preferred)
            .compareTo(
          _itemSoftScore(a, user, weather, occasion, band, preferred),
        );
      });
    return scored.take(n).toList();
  }

  double _itemSoftScore(
    WardrobeItem item,
    UserModel user,
    WeatherModel weather,
    Occasion occasion,
    WeatherBand band,
    Set<String> preferred,
  ) {
    final weatherScore = _weatherScore(item, band, weather.isRainy);
    final cultureScore = _cultureScore(item, user, preferred);
    final occasionScore = _occasionFit(item, occasion);
    final colorScore = user.skinTone == null
        ? 0.7
        : ClothingCatalog.colorScoreForSkin(user.skinTone!, item.color);
    final prefScore = user.preferences.favoriteColors.contains(item.color)
        ? 0.95
        : (preferred.contains(item.subcategory.toLowerCase()) ? 0.8 : 0.6);
    final genderScore = ClothingCatalog.genderScore(
      gender: user.gender,
      subcategory: item.subcategory,
      category: item.category,
      culture: user.culture,
    );
    final bodyScore = ClothingCatalog.bodyTypeScore(
      bodyType: user.bodyType,
      subcategory: item.subcategory,
      category: item.category,
      gender: user.gender,
    );
    return weatherScore * 0.30 +
        cultureScore * 0.14 +
        occasionScore * 0.22 +
        colorScore * 0.08 +
        prefScore * 0.08 +
        genderScore * 0.10 +
        bodyScore * 0.08;
  }

  ScoreBreakdown _score({
    required List<WardrobeItem> items,
    required UserModel user,
    required WeatherModel weather,
    required Occasion occasion,
    required WeatherBand band,
    required bool rainy,
    required Season season,
    required Set<String> preferred,
    required List<OutfitFeedback> feedback,
    required List<TrendModel> trends,
    required RecommendationWeights weights,
    required List<OutfitSlot> slots,
    bool wantsOuterwear = false,
    String? styleHint,
  }) {
    double avg(double Function(WardrobeItem) fn) =>
        items.map(fn).reduce((a, b) => a + b) / items.length;

    final weatherScore = avg((i) => _weatherScore(i, band, rainy));
    final cultureScore = avg((i) => _cultureScore(i, user, preferred));
    final occasionScore = avg((i) => _occasionFit(i, occasion));
    final colorScore = avg((i) {
      final skin = user.skinTone == null
          ? 0.7
          : ClothingCatalog.colorScoreForSkin(user.skinTone!, i.color);
      final fav = user.preferences.favoriteColors.contains(i.color) ? 0.15 : 0;
      return (skin + fav).clamp(0.0, 1.0);
    });
    final prefScore = _preferenceScore(items, user, preferred, feedback, styleHint);
    final bodyTypeScore = avg(
      (i) =>         ClothingCatalog.bodyTypeScore(
          bodyType: user.bodyType,
          subcategory: i.subcategory,
          category: i.category,
          gender: user.gender,
        ),
    );
    final wardrobeScore = slots
            .where((s) =>
                s.category != ClothingCategory.accessories ||
                s.filledFromWardrobe)
            .where((s) => s.filledFromWardrobe)
            .length /
        max(1, slots.where((s) => s.category != ClothingCategory.accessories || s.missingSuggestion != null || s.filledFromWardrobe).length);

    final hasBase = items.any(
      (i) =>
          i.category == ClothingCategory.upperwear &&
          ClothingCatalog.isBaseUpper(i.subcategory),
    );
    final hasOuter = items.any((i) => ClothingCatalog.isOuterwear(i.subcategory));
    final cold = band == WeatherBand.cold || band == WeatherBand.veryCold;
    final layerBonus = hasBase && hasOuter
        ? (cold || wantsOuterwear
            ? 0.12
            : band != WeatherBand.hot
                ? 0.07
                : 0.03)
        : (cold && hasBase && !hasOuter ? -0.16 : 0.0);

    // Trends are a small bonus only — never a hard override.
    final trendBonus = _trendBonus(items, trends, user) * 0.04;
    final personalization = _feedbackBoost(items, feedback) * 0.05;

    final finalScore = (weatherScore * weights.weather +
            cultureScore * weights.culture +
            occasionScore * weights.occasion +
            colorScore * weights.color +
            prefScore * weights.preference +
            wardrobeScore * weights.wardrobe +
            bodyTypeScore * weights.bodyType +
            trendBonus +
            personalization +
            layerBonus)
        .clamp(0.0, 1.0);

    return ScoreBreakdown(
      weather: weatherScore,
      culture: cultureScore,
      occasion: occasionScore,
      color: colorScore,
      preference: prefScore,
      wardrobe: wardrobeScore,
      bodyType: bodyTypeScore,
      finalScore: finalScore,
    );
  }

  double _occasionFit(WardrobeItem item, Occasion occasion) {
    var score = ClothingCatalog.occasionScore(item.formality, occasion);
    if (item.occasions.contains(occasion)) {
      score = max(score, 0.92);
    }
    return score;
  }

  double _weatherScore(WardrobeItem item, WeatherBand band, bool rainy) {
    final sub = item.subcategory.toLowerCase();
    final isOuter = ClothingCatalog.isOuterwear(sub);
    if (isOuter) {
      if (band == WeatherBand.hot) return 0.0;
      if (band == WeatherBand.mild) return 0.35;
      if (band == WeatherBand.cold) return 0.95;
      if (band == WeatherBand.veryCold) return 0.90;
    }
    if (band == WeatherBand.hot) {
      if (['t-shirt', 'tshirt', 'shorts', 'polo', 'sandals', 'crop top'].any((e) => sub.contains(e))) {
        return 1.0;
      }
      if (['shirt', 'kurta', 'kameez', 'chinos', 'trousers', 'jeans', 'sneakers'].any((e) => sub.contains(e))) {
        return 0.90;
      }
    }
    if (item.weatherSuitability.isEmpty) {
      final inferred = ClothingCatalog.weatherBandsForSubcategory(item.subcategory);
      if (inferred.contains(band)) return 0.85;
      if (band == WeatherBand.veryCold &&
          inferred.contains(WeatherBand.cold)) {
        return 0.65;
      }
      return 0.12;
    }
    if (item.weatherSuitability.contains(band)) return 1.0;
    if (band == WeatherBand.veryCold &&
        item.weatherSuitability.contains(WeatherBand.cold)) {
      return 0.7;
    }
    if (rainy &&
        ['sandals', 'shorts'].contains(item.subcategory.toLowerCase())) {
      return 0.1;
    }
    return 0.18;
  }

  double _cultureScore(
    WardrobeItem item,
    UserModel user,
    Set<String> preferred,
  ) {
    if (user.culture == null) return 0.7;
    if (item.cultureCompatibility.contains(user.culture!.name)) return 0.95;
    if (preferred.contains(item.subcategory.toLowerCase())) return 0.9;
    if (user.preferences.modestPreference &&
        ClothingCatalog.modestExcludedSubcategories()
            .contains(item.subcategory.toLowerCase())) {
      return 0.1;
    }
    return 0.55;
  }

  double _preferenceScore(
    List<WardrobeItem> items,
    UserModel user,
    Set<String> preferred,
    List<OutfitFeedback> feedback,
    String? styleHint,
  ) {
    var score = 0.6;
    final colors = items.map((e) => e.color).toSet();
    for (final c in colors) {
      if (user.preferences.favoriteColors.contains(c)) score += 0.08;
    }
    for (final item in items) {
      if (preferred.contains(item.subcategory.toLowerCase())) score += 0.05;
      if (styleHint != null &&
          item.style.toLowerCase().contains(styleHint.toLowerCase())) {
        score += 0.04;
      }
    }
    return score.clamp(0.0, 1.0);
  }

  double _feedbackBoost(List<WardrobeItem> items, List<OutfitFeedback> feedback) {
    if (feedback.isEmpty) return 0;
    final likedColors = <String>{};
    final dislikedColors = <String>{};
    for (final f in feedback) {
      if (f.type == FeedbackType.like || f.type == FeedbackType.save) {
        likedColors.addAll(f.colors);
      }
      if (f.type == FeedbackType.dislike) {
        dislikedColors.addAll(f.colors);
      }
    }
    var boost = 0.0;
    for (final item in items) {
      if (likedColors.contains(item.color)) boost += 0.2;
      if (dislikedColors.contains(item.color)) boost -= 0.25;
    }
    return boost.clamp(-0.4, 0.6);
  }

  double _trendBonus(
    List<WardrobeItem> items,
    List<TrendModel> trends,
    UserModel user,
  ) {
    if (trends.isEmpty) return 0;
    final types = items.map((e) => e.subcategory.toLowerCase()).toSet();
    final colors = items.map((e) => e.color.toLowerCase()).toSet();
    var hits = 0;
    for (final trend in trends.take(8)) {
      if (trend.itemTypes.any((t) => types.contains(t.toLowerCase()))) hits++;
      if (trend.colors.any((c) => colors.contains(c.toLowerCase()))) hits++;
    }
    return (hits / 8).clamp(0.0, 1.0);
  }

  List<String> _explanations({
    required UserModel user,
    required WeatherModel weather,
    required Occasion occasion,
    required List<WardrobeItem> items,
    required List<OutfitSlot> slots,
    required Season season,
    required WeatherBand band,
  }) {
    final lines = <String>[
      'Temperature is ${weather.temperature.round()}°C (${weather.condition.toLowerCase()}) in ${weather.city}.',
      'Weather band is ${band.label}; calendar season is ${season.label} but temperature is prioritized.',
      'Suitable for ${occasion.label}.',
    ];
    if (user.gender != null && user.gender != Gender.preferNotToSay) {
      lines.add('Styled for a ${user.gender!.label.toLowerCase()} wardrobe.');
    }
    if (user.culture != null) {
      lines.add('Matches your selected ${user.culture!.label} clothing preference.');
    }
    if (user.skinTone != null) {
      lines.add(
        'Colors complement your selected ${user.skinTone!.label} skin tone (ranked, not blocked).',
      );
    }
    if (user.preferences.modestPreference) {
      lines.add('Respects your modest / conservative clothing preference.');
    }
    if (user.bodyType != null) {
      lines.add(
        'Silhouettes ranked for your ${user.bodyType!.label} body type.',
      );
    }
    final layered = items.any((i) => ClothingCatalog.isBaseUpper(i.subcategory) &&
            i.category == ClothingCategory.upperwear) &&
        items.any((i) => ClothingCatalog.isOuterwear(i.subcategory));
    if (layered) {
      lines.add(
        'Shirt or top is layered with a jacket or blazer for this temperature.',
      );
    }
    final missing = slots
        .map((s) => s.missingSuggestion)
        .whereType<MissingItemSuggestion>()
        .toList();
    if (missing.isEmpty) {
      lines.add('All major items are available in your wardrobe.');
    } else {
      for (final m in missing) {
        lines.add('Your wardrobe does not contain a suitable ${m.subcategory}.');
      }
    }
    return lines;
  }

  MissingItemSuggestion _missing(
    ClothingCategory category,
    UserModel user,
    WeatherBand band,
    Occasion occasion,
    List<ProductModel> products, {
    required bool rainy,
    String? preferredSubcategory,
    List<String> paletteColors = const [],
  }) {
    final preferred = preferredSubcategory ??
        ClothingCatalog.preferredFillSubcategory(
          category: category,
          gender: user.gender,
          occasion: occasion,
          band: band,
        );
    final color = paletteColors.isNotEmpty
        ? paletteColors.first
        : user.preferences.favoriteColors.isNotEmpty
            ? user.preferences.favoriteColors.first
            : 'black';
    final gendered = products.where((p) {
      if (ClothingCatalog.mismatchesGender(
        gender: user.gender,
        subcategory: p.subcategory,
        category: p.category,
        culture: user.culture,
      )) {
        return false;
      }
      final name = p.name.toLowerCase();
      if (user.gender == Gender.male &&
          (name.contains('women') ||
              name.contains('ladies') ||
              name.contains('girl') ||
              name.contains('female') ||
              name.contains('gown'))) {
        return false;
      }
      if (ClothingCatalog.mismatchesOccasion(
        subcategory: p.subcategory,
        formality: ClothingCatalog.formalityForSubcategory(p.subcategory),
        occasion: occasion,
      )) {
        return false;
      }
      if (ClothingCatalog.mismatchesWeather(
        subcategory: p.subcategory,
        category: p.category,
        band: band,
        rainy: rainy,
      )) {
        return false;
      }
      return true;
    }).toList();

    ProductModel? match;
    final sameType = gendered
        .where((p) =>
            p.category == category &&
            p.subcategory.toLowerCase() == preferred.toLowerCase())
        .toList();
    final sameCat =
        gendered.where((p) => p.category == category).toList();
    final pool = sameType.isNotEmpty ? sameType : sameCat;

    double score(ProductModel p) {
      var s = 0.0;
      if (p.subcategory.toLowerCase() == preferred.toLowerCase()) s += 0.45;
      if (p.weatherBands.contains(band.name)) s += 0.2;
      if (user.culture != null &&
          (p.cultureTags.contains(user.culture!.name) ||
              p.cultureTags.contains('all'))) {
        s += 0.15;
      }
      if (paletteColors.isNotEmpty) {
        final harmony = paletteColors
                .map((c) => ClothingCatalog.colorHarmonyScore(p.color, c))
                .fold<double>(0, (a, b) => a + b) /
            paletteColors.length;
        s += 0.25 * harmony;
      }
      if (user.skinTone != null) {
        s += 0.1 * ClothingCatalog.colorScoreForSkin(user.skinTone!, p.color);
      }
      return s;
    }

    if (pool.isNotEmpty) {
      pool.sort((a, b) => score(b).compareTo(score(a)));
      match = pool.first;
    }
    return MissingItemSuggestion(
      title: match?.name ??
          '${color[0].toUpperCase()}${color.substring(1)} $preferred',
      reason:
          'Suitable for ${band.label.toLowerCase()} weather and your ${occasion.label} plans.',
      category: category,
      subcategory: match?.subcategory ?? preferred,
      color: match?.color ?? color,
      matchedProduct: match,
    );
  }

  List<WardrobeItem> _matchingOuters({
    required List<WardrobeItem> outers,
    required WardrobeItem? upper,
    required WardrobeItem? lower,
    required WardrobeItem? shoe,
    required UserModel user,
    required WeatherModel weather,
    required Occasion occasion,
    required WeatherBand band,
    required Set<String> preferred,
  }) {
    if (outers.isEmpty) return [];
    final want = ClothingCatalog.preferredOuterSubcategory(
      occasion: occasion,
      band: band,
    );
    final palette = [
      if (upper != null) upper.color,
      if (lower != null) lower.color,
      if (shoe != null) shoe.color,
    ];
    final scored = [...outers]..sort((a, b) {
        double rank(WardrobeItem item) {
          var s = _itemSoftScore(
            item,
            user,
            weather,
            occasion,
            band,
            preferred,
          );
          if (item.subcategory.toLowerCase() == want) s += 0.14;
          if (palette.isNotEmpty) {
            final harmony = palette
                    .map((c) => ClothingCatalog.colorHarmonyScore(item.color, c))
                    .fold<double>(0, (x, y) => x + y) /
                palette.length;
            s += 0.22 * harmony;
          }
          if (user.skinTone != null) {
            s += 0.08 *
                ClothingCatalog.colorScoreForSkin(user.skinTone!, item.color);
          }
          return s;
        }

        return rank(b).compareTo(rank(a));
      });
    return scored.take(3).toList();
  }

  OutfitRecommendation? _stripGenderMismatches(
    OutfitRecommendation outfit,
    UserModel user,
  ) {
    if (user.gender != Gender.male) return outfit;
    final slots = outfit.slots.where((s) {
      final item = s.item;
      if (item != null) {
        return !ClothingCatalog.mismatchesGender(
          gender: user.gender,
          subcategory: item.subcategory,
          category: item.category,
          culture: user.culture,
        );
      }
      final missing = s.missingSuggestion;
      if (missing == null) return true;
      return !ClothingCatalog.mismatchesGender(
        gender: user.gender,
        subcategory: missing.subcategory,
        category: missing.category,
        culture: user.culture,
      );
    }).toList();
    final hasCore = slots.any(
      (s) =>
          s.category == ClothingCategory.upperwear ||
          s.category == ClothingCategory.dress,
    );
    if (!hasCore) return null;
    return OutfitRecommendation(
      id: outfit.id,
      title: outfit.title,
      slots: slots,
      breakdown: outfit.breakdown,
      explanations: outfit.explanations,
      fromWardrobe: outfit.fromWardrobe,
    );
  }

  OutfitRecommendation _shopFallbackOutfit({
    required UserModel user,
    required WeatherModel weather,
    required Occasion occasion,
    required WeatherBand band,
    required List<ProductModel> products,
    required RecommendationWeights w,
  }) {
    final cold = band == WeatherBand.cold || band == WeatherBand.veryCold;
    final slots = <OutfitSlot>[
      OutfitSlot(
        category: ClothingCategory.upperwear,
        missingSuggestion: _missing(
          ClothingCategory.upperwear,
          user,
          band,
          occasion,
          products,
          rainy: weather.isRainy,
        ),
      ),
      if (cold)
        OutfitSlot(
          category: ClothingCategory.upperwear,
          missingSuggestion: _missing(
            ClothingCategory.upperwear,
            user,
            band,
            occasion,
            products,
            rainy: weather.isRainy,
            preferredSubcategory: ClothingCatalog.preferredOuterSubcategory(
              occasion: occasion,
              band: band,
            ),
          ),
        ),
      OutfitSlot(
        category: ClothingCategory.lowerwear,
        missingSuggestion: _missing(
          ClothingCategory.lowerwear,
          user,
          band,
          occasion,
          products,
          rainy: weather.isRainy,
        ),
      ),
      OutfitSlot(
        category: ClothingCategory.footwear,
        missingSuggestion: _missing(
          ClothingCategory.footwear,
          user,
          band,
          occasion,
          products,
          rainy: weather.isRainy,
        ),
      ),
    ];
    return OutfitRecommendation(
      id: 'shop-fallback',
      title: 'New clothing recommendations',
      slots: slots,
      breakdown: ScoreBreakdown(
        weather: 0.8,
        culture: 0.7,
        occasion: 0.7,
        color: 0.7,
        preference: 0.6,
        wardrobe: 0,
        bodyType: 0.72,
        finalScore: 0.55,
      ),
      explanations: [
        'Your wardrobe cannot form a complete outfit yet.',
        'Temperature is ${weather.temperature.round()}°C and ${weather.condition.toLowerCase()}.',
        'Shop items below are chosen for ${occasion.label} and your profile.',
      ],
      fromWardrobe: false,
    );
  }

  Season _seasonFromBand(WeatherBand band, Season calendar) {
    return switch (band) {
      WeatherBand.veryCold || WeatherBand.cold => Season.winter,
      WeatherBand.hot => Season.summer,
      WeatherBand.mild => calendar,
    };
  }

  String _titleFor(int index, int percent) {
    return switch (index) {
      0 => 'Best match  $percent%',
      1 => 'Alternative  $percent%',
      2 => 'Casual option  $percent%',
      _ => 'Look ${index + 1}  $percent%',
    };
  }
}

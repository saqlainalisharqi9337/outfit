import 'package:adore/models/user_model.dart';
import 'package:adore/models/wardrobe_item.dart';
import 'package:adore/models/weather_model.dart';
import 'package:adore/services/recommendation_service.dart';
import 'package:adore/utils/clothing_catalog.dart';
import 'package:adore/utils/enums.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('catalog hard filters', () {
    test('male profile rejects dresses, heels and blouses', () {
      expect(
        ClothingCatalog.mismatchesGender(
          gender: Gender.male,
          subcategory: 'dress',
          category: ClothingCategory.dress,
        ),
        isTrue,
      );
      expect(
        ClothingCatalog.mismatchesGender(
          gender: Gender.male,
          subcategory: 'heels',
          category: ClothingCategory.footwear,
        ),
        isTrue,
      );
      expect(
        ClothingCatalog.mismatchesGender(
          gender: Gender.male,
          subcategory: 'blouse',
          category: ClothingCategory.upperwear,
        ),
        isTrue,
      );
      expect(
        ClothingCatalog.mismatchesGender(
          gender: Gender.male,
          subcategory: 'dupatta',
          category: ClothingCategory.accessories,
        ),
        isTrue,
      );
      expect(
        ClothingCatalog.mismatchesGender(
          gender: Gender.male,
          subcategory: 'sandals',
          category: ClothingCategory.footwear,
        ),
        isTrue,
      );
      expect(
        ClothingCatalog.mismatchesGender(
          gender: Gender.male,
          subcategory: 'bag',
          category: ClothingCategory.accessories,
        ),
        isTrue,
      );
      expect(
        ClothingCatalog.mismatchesGender(
          gender: Gender.male,
          subcategory: 'watch',
          category: ClothingCategory.accessories,
        ),
        isFalse,
      );
      expect(
        ClothingCatalog.mismatchesGender(
          gender: Gender.male,
          subcategory: 'backpack',
          category: ClothingCategory.accessories,
        ),
        isFalse,
      );
      expect(
        ClothingCatalog.mismatchesGender(
          gender: Gender.female,
          subcategory: 'necktie',
          category: ClothingCategory.accessories,
        ),
        isTrue,
      );
      expect(
        ClothingCatalog.mismatchesGender(
          gender: Gender.female,
          subcategory: 'blouse',
          category: ClothingCategory.upperwear,
        ),
        isFalse,
      );
      expect(
        ClothingCatalog.mismatchesGender(
          gender: Gender.male,
          subcategory: 'earrings',
          category: ClothingCategory.accessories,
        ),
        isTrue,
      );
      expect(
        ClothingCatalog.mismatchesGender(
          gender: Gender.male,
          subcategory: 'shalwar',
          category: ClothingCategory.lowerwear,
          culture: Culture.western,
        ),
        isTrue,
      );
      expect(
        ClothingCatalog.mismatchesGender(
          gender: Gender.male,
          subcategory: 'shirt',
          category: ClothingCategory.upperwear,
        ),
        isFalse,
      );
    });

    test('shorts mismatch very cold weather', () {
      expect(
        ClothingCatalog.mismatchesWeather(
          subcategory: 'shorts',
          category: ClothingCategory.lowerwear,
          band: WeatherBand.veryCold,
          rainy: false,
        ),
        isTrue,
      );
    });

    test('office rejects shorts and hoodies', () {
      expect(
        ClothingCatalog.mismatchesOccasion(
          subcategory: 'shorts',
          formality: Formality.casual,
          occasion: Occasion.office,
        ),
        isTrue,
      );
      expect(
        ClothingCatalog.mismatchesOccasion(
          subcategory: 'hoodie',
          formality: Formality.casual,
          occasion: Occasion.office,
        ),
        isTrue,
      );
      expect(
        ClothingCatalog.mismatchesOccasion(
          subcategory: 'shirt',
          formality: Formality.smartCasual,
          occasion: Occasion.office,
        ),
        isFalse,
      );
    });

    test('male fill defaults are never feminine', () {
      expect(
        ClothingCatalog.preferredFillSubcategory(
          category: ClothingCategory.footwear,
          gender: Gender.male,
          occasion: Occasion.casualDayOut,
          band: WeatherBand.mild,
        ),
        'sneakers',
      );
      expect(
        ClothingCatalog.preferredFillSubcategory(
          category: ClothingCategory.accessories,
          gender: Gender.male,
          occasion: Occasion.casualDayOut,
          band: WeatherBand.mild,
        ),
        isNot('dupatta'),
      );
    });
  });

  group('recommendation ranking', () {
    final service = RecommendationService(weights: const RecommendationWeights());

    WardrobeItem item({
      required String id,
      required ClothingCategory category,
      required String subcategory,
      Formality? formality,
    }) {
      return WardrobeItem.inferred(
        itemId: id,
        userId: 'u1',
        imageUrl: '',
        category: category,
        subcategory: subcategory,
        color: 'navy',
      ).copyWith(formality: formality);
    }

    WeatherModel weather(double c) => WeatherModel(
          temperature: c,
          feelsLike: c,
          condition: 'Clear',
          weatherCode: 0,
          city: 'Lahore',
          country: 'Pakistan',
          latitude: 31.5,
          longitude: 74.3,
          fetchedAt: DateTime(2026, 6, 1),
        );

    const male = UserModel(
      id: 'u1',
      name: 'Ali',
      email: 'ali@test.com',
      gender: Gender.male,
      culture: Culture.pakistani,
      bodyType: BodyType.rectangle,
    );

    final mixedWardrobe = [
      item(
        id: 'dress',
        category: ClothingCategory.dress,
        subcategory: 'dress',
        formality: Formality.formal,
      ),
      item(
        id: 'heels',
        category: ClothingCategory.footwear,
        subcategory: 'heels',
        formality: Formality.formal,
      ),
      item(
        id: 'blouse',
        category: ClothingCategory.upperwear,
        subcategory: 'blouse',
      ),
      item(
        id: 'shirt',
        category: ClothingCategory.upperwear,
        subcategory: 'shirt',
        formality: Formality.smartCasual,
      ),
      item(
        id: 'trousers',
        category: ClothingCategory.lowerwear,
        subcategory: 'trousers',
        formality: Formality.smartCasual,
      ),
      item(
        id: 'shorts',
        category: ClothingCategory.lowerwear,
        subcategory: 'shorts',
      ),
      item(
        id: 'sneakers',
        category: ClothingCategory.footwear,
        subcategory: 'sneakers',
      ),
      item(
        id: 'coat',
        category: ClothingCategory.upperwear,
        subcategory: 'coat',
      ),
      item(
        id: 'jacket',
        category: ClothingCategory.upperwear,
        subcategory: 'jacket',
      ),
      item(
        id: 'dupatta',
        category: ClothingCategory.accessories,
        subcategory: 'dupatta',
      ),
      item(
        id: 'sandals',
        category: ClothingCategory.footwear,
        subcategory: 'sandals',
      ),
      item(
        id: 'bag',
        category: ClothingCategory.accessories,
        subcategory: 'bag',
      ),
      item(
        id: 'watch',
        category: ClothingCategory.accessories,
        subcategory: 'watch',
      ),
    ];

    test('male outfits never include female garments', () async {
      final result = await service.recommend(
        user: male,
        wardrobe: mixedWardrobe,
        weather: weather(24),
        occasion: Occasion.casualDayOut,
      );
      final subs = result.outfits
          .expand((o) => o.slots)
          .map((s) => s.item?.subcategory)
          .whereType<String>()
          .toSet();
      expect(subs, isNot(contains('dress')));
      expect(subs, isNot(contains('heels')));
      expect(subs, isNot(contains('blouse')));
      expect(subs, isNot(contains('dupatta')));
      expect(subs, isNot(contains('sandals')));
      expect(subs, isNot(contains('bag')));
      expect(subs, contains('shirt'));
    });

    test('cold weather layers a matching jacket', () async {
      final result = await service.recommend(
        user: male,
        wardrobe: mixedWardrobe,
        weather: weather(6),
        occasion: Occasion.casualDayOut,
      );
      expect(result.outfits, isNotEmpty);
      for (final outfit in result.outfits) {
        final subs = outfit.slots
            .map((s) => s.item?.subcategory ?? s.missingSuggestion?.subcategory)
            .whereType<String>()
            .toSet();
        expect(
          subs.any((s) => {'jacket', 'coat', 'blazer', 'cardigan'}.contains(s)),
          isTrue,
          reason: 'cold outfit missing outerwear: $subs',
        );
        expect(subs, isNot(contains('dress')));
        expect(subs, isNot(contains('dupatta')));
        expect(subs, isNot(contains('heels')));
      }
    });

    test('office outfits drop shorts even if they are in the wardrobe', () async {
      final result = await service.recommend(
        user: male,
        wardrobe: mixedWardrobe,
        weather: weather(24),
        occasion: Occasion.office,
      );
      final subs = result.outfits
          .expand((o) => o.slots)
          .map((s) => s.item?.subcategory)
          .whereType<String>()
          .toSet();
      expect(subs, isNot(contains('shorts')));
      expect(subs, contains('trousers'));
    });

    test('hot weather drops coats and jackets', () async {
      final result = await service.recommend(
        user: male,
        wardrobe: mixedWardrobe,
        weather: weather(34),
        occasion: Occasion.casualDayOut,
      );
      final subs = result.outfits
          .expand((o) => o.slots)
          .map((s) => s.item?.subcategory)
          .whereType<String>()
          .toSet();
      expect(subs, isNot(contains('coat')));
      expect(subs, isNot(contains('jacket')));
    });

    test('casual day out in warm weather (24C) drops jackets and coats', () async {
      final result = await service.recommend(
        user: male,
        wardrobe: mixedWardrobe,
        weather: weather(24),
        occasion: Occasion.casualDayOut,
      );
      final subs = result.outfits
          .expand((o) => o.slots)
          .map((s) => s.item?.subcategory)
          .whereType<String>()
          .toSet();
      expect(subs, isNot(contains('coat')));
      expect(subs, isNot(contains('jacket')));
      expect(subs, contains('shirt'));
    });

    test('wedding in warm weather (24C) drops jackets and coats', () async {
      final result = await service.recommend(
        user: male,
        wardrobe: mixedWardrobe,
        weather: weather(24),
        occasion: Occasion.wedding,
      );
      final subs = result.outfits
          .expand((o) => o.slots)
          .map((s) => s.item?.subcategory)
          .whereType<String>()
          .toSet();
      expect(subs, isNot(contains('coat')));
      expect(subs, isNot(contains('jacket')));
      expect(subs, contains('shirt'));
    });

    test('formal in warm weather (24C) drops jackets and coats', () async {
      final result = await service.recommend(
        user: male,
        wardrobe: mixedWardrobe,
        weather: weather(24),
        occasion: Occasion.formalEvent,
      );
      final subs = result.outfits
          .expand((o) => o.slots)
          .map((s) => s.item?.subcategory)
          .whereType<String>()
          .toSet();
      expect(subs, isNot(contains('coat')));
      expect(subs, isNot(contains('jacket')));
      expect(subs, contains('shirt'));
    });
  });
}

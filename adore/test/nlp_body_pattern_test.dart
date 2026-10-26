import 'package:adore/models/user_model.dart';
import 'package:adore/models/wardrobe_item.dart';
import 'package:adore/services/nlp_request_parser.dart';
import 'package:adore/utils/clothing_catalog.dart';
import 'package:adore/utils/enums.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('body type scoring', () {
    test('unset body type is a neutral score', () {
      expect(
        ClothingCatalog.bodyTypeScore(
          bodyType: null,
          subcategory: 'dress',
          category: ClothingCategory.dress,
        ),
        0.72,
      );
    });

    test('pear scores structured tops above clingy shorts', () {
      final jacket = ClothingCatalog.bodyTypeScore(
        bodyType: BodyType.pear,
        subcategory: 'jacket',
        category: ClothingCategory.upperwear,
      );
      final shorts = ClothingCatalog.bodyTypeScore(
        bodyType: BodyType.pear,
        subcategory: 'shorts',
        category: ClothingCategory.lowerwear,
      );
      expect(jacket, greaterThan(shorts));
    });

    test('apple scores structured layers above clingy t-shirts', () {
      final jacket = ClothingCatalog.bodyTypeScore(
        bodyType: BodyType.apple,
        subcategory: 'jacket',
        category: ClothingCategory.upperwear,
      );
      final tee = ClothingCatalog.bodyTypeScore(
        bodyType: BodyType.apple,
        subcategory: 't-shirt',
        category: ClothingCategory.upperwear,
      );
      expect(jacket, greaterThan(tee));
    });

    test('hourglass prefers a fitted dress over a bulky hoodie', () {
      final dress = ClothingCatalog.bodyTypeScore(
        bodyType: BodyType.hourglass,
        subcategory: 'dress',
        category: ClothingCategory.dress,
      );
      final hoodie = ClothingCatalog.bodyTypeScore(
        bodyType: BodyType.hourglass,
        subcategory: 'hoodie',
        category: ClothingCategory.upperwear,
      );
      expect(dress, greaterThan(hoodie));
    });

    test('footwear does not dominate silhouette scoring', () {
      expect(
        ClothingCatalog.bodyTypeScore(
          bodyType: BodyType.rectangle,
          subcategory: 'sneakers',
          category: ClothingCategory.footwear,
        ),
        0.80,
      );
    });

    test('weights including body type still sum to 1.0', () {
      const weights = RecommendationWeights();
      expect(weights.sum, closeTo(1.0, 0.0001));
    });

    test('profile round-trips body_type', () {
      const user = UserModel(
        id: 'u1',
        name: 'Ayesha',
        email: 'a@test.com',
        bodyType: BodyType.pear,
      );
      final row = user.toRow();
      expect(row['body_type'], 'pear');
      final loaded = UserModel.fromMap('u1', row);
      expect(loaded.bodyType, BodyType.pear);
    });
  });

  group('pattern', () {
    test('catalog includes the proposal pattern set', () {
      expect(
        ClothingCatalog.patterns,
        containsAll([
          'solid',
          'striped',
          'checked',
          'floral',
          'printed',
          'polka dot',
          'graphic',
          'other',
        ]),
      );
    });

    test('wardrobe item stores user-selected pattern metadata', () {
      final item = WardrobeItem(
        itemId: 'i1',
        userId: 'u1',
        imageUrl: '',
        category: ClothingCategory.upperwear,
        subcategory: 'shirt',
        color: 'navy',
        pattern: 'striped',
        patternSource: 'user',
        patternConfidence: 1.0,
      );
      final row = item.toRow();
      expect(row['pattern'], 'striped');
      expect(row['pattern_source'], 'user');
      expect(row['pattern_confidence'], 1.0);
      final loaded = WardrobeItem.fromMap('i1', 'u1', row);
      expect(loaded.pattern, 'striped');
      expect(loaded.patternSource, 'user');
    });
  });

  group('NLP request parser', () {
    const parser = NlpRequestParser();

    test('modest university outfit in hot weather', () {
      final r = parser.parse(
        'I need a modest outfit for university tomorrow. It will be hot.',
      );
      expect(r.occasion, Occasion.university);
      expect(r.weatherBand, WeatherBand.hot);
      expect(r.modest, isTrue);
    });

    test('formal wedding request', () {
      final r = parser.parse('I need something formal for a wedding.');
      expect(r.occasion, Occasion.wedding);
    });

    test('marriage request is a wedding, not everyday wear', () {
      final r = parser.parse('i need an outfit for marriage');
      expect(r.occasion, Occasion.wedding);
      expect(r.everyday, isFalse);
    });

    test('office meeting', () {
      final r = parser.parse('Outfit for an office meeting');
      expect(r.occasion, Occasion.office);
    });

    test('rainy outdoor day', () {
      final r = parser.parse('Something for a rainy outdoor picnic');
      expect(r.occasion, Occasion.outdoorActivity);
      expect(r.rainy, isTrue);
    });

    test('cold travel look', () {
      final r = parser.parse('Warm clothes for a cold travel day');
      expect(r.occasion, Occasion.travel);
      expect(r.weatherBand, WeatherBand.cold);
    });

    test('sports gym session', () {
      final r = parser.parse('Gym workout sports outfit');
      expect(r.occasion, Occasion.sports);
    });

    test('religious event', () {
      final r = parser.parse('Clothes for a religious event at the mosque');
      expect(r.occasion, Occasion.religiousEvent);
    });

    test('date night party', () {
      final r = parser.parse('Date night outfit');
      expect(r.occasion, Occasion.date);
    });

    test('navy casual weekend', () {
      final r = parser.parse('Casual navy look for a weekend hang out');
      expect(r.occasion, Occasion.casualDayOut);
      expect(r.colors, contains('navy'));
    });

    test('formal gala', () {
      final r = parser.parse('Black tie gala, formal event');
      expect(r.occasion, Occasion.formalEvent);
    });

    test('usual everyday clothes defaults to casual', () {
      final r = parser.parse('I need usual clothes to wear');
      expect(r.everyday, isTrue);
      expect(r.occasion, Occasion.casualDayOut);
      expect(r.hasFilters, isTrue);
    });

    test('shirt with jacket or blazer requests layering', () {
      final r = parser.parse('Recommend a shirt with a jacket or blazer');
      expect(r.wantsOuterwear, isTrue);
      expect(r.garmentHints, contains('shirt'));
    });

    test('lazer typo still means blazer layer', () {
      expect(parser.parse('shirt with lazers').wantsOuterwear, isTrue);
    });
  });
}

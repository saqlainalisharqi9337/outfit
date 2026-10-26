import 'dart:typed_data';

import 'package:adore/services/local_image_analysis.dart';
import 'package:adore/utils/clothing_catalog.dart';
import 'package:adore/utils/enums.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:image/image.dart' as img;

Uint8List _png(img.Image image) => Uint8List.fromList(img.encodePng(image));

img.Image _canvas() {
  final image = img.Image(width: 192, height: 192);
  img.fill(image, color: img.ColorRgb8(248, 248, 248));
  return image;
}

void _rect(img.Image image, int x, int y, int w, int h, int r, int g, int b) {
  img.fillRect(
    image,
    x1: x,
    y1: y,
    x2: x + w,
    y2: y + h,
    color: img.ColorRgb8(r, g, b),
  );
}

void main() {
  test('brown horizontal strip is a belt', () {
    final image = _canvas();
    _rect(image, 18, 86, 156, 16, 92, 54, 28);
    final result = LocalImageAnalysis.analyzeClothing(_png(image));
    expect(result.subcategory, 'belt');
    expect(result.category, ClothingCategory.accessories);
    expect(result.color, anyOf('brown', 'beige'));
  });

  test('gold ring-like circle is jewelry', () {
    final image = _canvas();
    img.fillCircle(
      image,
      x: 96,
      y: 96,
      radius: 22,
      color: img.ColorRgb8(206, 164, 48),
    );
    img.fillCircle(
      image,
      x: 96,
      y: 96,
      radius: 12,
      color: img.ColorRgb8(248, 248, 248),
    );
    final result = LocalImageAnalysis.analyzeClothing(_png(image));
    expect(result.subcategory, 'jewelry');
    expect(result.category, ClothingCategory.accessories);
    expect(result.color, anyOf('gold', 'yellow'));
  });

  test('grey compact square is a watch', () {
    final image = _canvas();
    _rect(image, 74, 70, 44, 48, 70, 74, 78);
    img.fillCircle(
      image,
      x: 96,
      y: 94,
      radius: 10,
      color: img.ColorRgb8(30, 32, 36),
    );
    final result = LocalImageAnalysis.analyzeClothing(_png(image));
    expect(result.subcategory, 'watch');
    expect(result.category, ClothingCategory.accessories);
    expect(result.color, anyOf('grey', 'black'));
  });

  test('blue tall panel is jeans', () {
    final image = _canvas();
    _rect(image, 62, 18, 68, 156, 36, 68, 150);
    final result = LocalImageAnalysis.analyzeClothing(_png(image));
    expect(result.subcategory, anyOf('jeans', 'trousers'));
    expect(result.category, ClothingCategory.lowerwear);
    expect(result.color, anyOf('blue', 'navy'));
  });

  test('red large square is a t-shirt', () {
    final image = _canvas();
    _rect(image, 28, 30, 136, 128, 198, 36, 42);
    final result = LocalImageAnalysis.analyzeClothing(_png(image));
    expect(result.category, ClothingCategory.upperwear);
    expect(result.subcategory, anyOf('t-shirt', 'shirt'));
    expect(result.color, 'red');
  });

  test('garment color is used instead of white studio background', () {
    final image = _canvas();
    _rect(image, 58, 22, 76, 150, 28, 72, 168);
    final result = LocalImageAnalysis.analyzeClothing(_png(image));
    expect(result.color, anyOf('blue', 'navy'));
    expect(result.color, isNot('white'));
    expect(result.color, isNot('cream'));
  });

  test('pink garment is not labeled as the cream background', () {
    final image = _canvas();
    _rect(image, 40, 28, 112, 132, 220, 96, 150);
    final result = LocalImageAnalysis.analyzeClothing(_png(image));
    expect(result.color, anyOf('pink', 'red', 'maroon'));
    expect(result.color, isNot('white'));
    expect(result.color, isNot('cream'));
  });

  test('brown compact rectangle is a bag', () {
    final image = _canvas();
    _rect(image, 54, 48, 84, 96, 118, 72, 40);
    final result = LocalImageAnalysis.analyzeClothing(_png(image));
    expect(result.subcategory, 'bag');
    expect(result.category, ClothingCategory.accessories);
    expect(result.color, anyOf('brown', 'orange', 'beige'));
  });

  test('pair of dark blobs near the bottom are shoes', () {
    final image = _canvas();
    _rect(image, 28, 118, 58, 36, 28, 24, 22);
    _rect(image, 108, 118, 58, 36, 28, 24, 22);
    final result = LocalImageAnalysis.analyzeClothing(_png(image));
    expect(result.category, ClothingCategory.footwear);
    expect(result.subcategory, anyOf('shoes', 'sneakers', 'sandals', 'flats'));
    expect(result.color, anyOf('black', 'brown', 'grey'));
  });

  test('two tiny gold circles are jewelry not footwear', () {
    final image = _canvas();
    img.fillCircle(
      image,
      x: 70,
      y: 96,
      radius: 10,
      color: img.ColorRgb8(206, 164, 48),
    );
    img.fillCircle(
      image,
      x: 122,
      y: 96,
      radius: 10,
      color: img.ColorRgb8(206, 164, 48),
    );
    final result = LocalImageAnalysis.analyzeClothing(_png(image));
    expect(result.category, ClothingCategory.accessories);
    expect(result.subcategory, 'jewelry');
    expect(result.color, anyOf('gold', 'yellow'));
  });

  test('single dark shoe-shaped block is footwear not jewelry', () {
    final image = _canvas();
    _rect(image, 36, 88, 120, 52, 32, 28, 26);
    final result = LocalImageAnalysis.analyzeClothing(_png(image));
    expect(result.category, ClothingCategory.footwear);
    expect(result.subcategory, isNot('jewelry'));
  });

  test('stiletto silhouette is heels not jewelry', () {
    final image = _canvas();
    _rect(image, 78, 48, 16, 100, 28, 24, 24);
    _rect(image, 78, 138, 82, 16, 28, 24, 24);
    final result = LocalImageAnalysis.analyzeClothing(_png(image));
    expect(result.category, ClothingCategory.footwear);
    expect(result.subcategory, 'heels');
  });

  test('gold heel is footwear not jewelry', () {
    final image = _canvas();
    _rect(image, 80, 50, 14, 96, 206, 164, 48);
    _rect(image, 80, 136, 78, 18, 206, 164, 48);
    final result = LocalImageAnalysis.analyzeClothing(_png(image));
    expect(result.category, ClothingCategory.footwear);
    expect(result.subcategory, isNot('jewelry'));
  });

  test('one-piece A-line dress is a dress not lowerwear', () {
    final image = _canvas();
    for (var i = 0; i < 8; i++) {
      final w = 48 + i * 8;
      _rect(image, 96 - w ~/ 2, 22 + i * 18, w, 18, 186, 42, 78);
    }
    final result = LocalImageAnalysis.analyzeClothing(_png(image));
    expect(result.category, ClothingCategory.dress);
    expect(result.subcategory, 'dress');
  });

  test('t-shirt and jewelry aliases keep their own types', () {
    expect(
      ClothingCatalog.normalizeDetection(
        category: ClothingCategory.upperwear,
        subcategory: 't-shirt',
      ).$2,
      't-shirt',
    );
    expect(
      ClothingCatalog.normalizeDetection(
        category: ClothingCategory.upperwear,
        subcategory: 'jewelry',
      ),
      (ClothingCategory.accessories, 'jewelry'),
    );
    expect(
      ClothingCatalog.normalizeDetection(
        category: ClothingCategory.upperwear,
        subcategory: 'heels',
      ),
      (ClothingCategory.footwear, 'heels'),
    );
  });

  test('gold necklace dots are jewelry not a belt or shoes', () {
    final image = _canvas();
    for (var i = 0; i < 7; i++) {
      final t = i / 6;
      img.fillCircle(
        image,
        x: (48 + t * 96).round(),
        y: (78 + (t * (1 - t) * 90)).round(),
        radius: 5,
        color: img.ColorRgb8(206, 164, 48),
      );
    }
    final result = LocalImageAnalysis.analyzeClothing(_png(image));
    expect(result.category, ClothingCategory.accessories);
    expect(result.subcategory, 'jewelry');
    expect(result.color, anyOf('gold', 'yellow'));
  });

  test('white sneaker pair is footwear', () {
    final image = _canvas();
    _rect(image, 26, 116, 56, 34, 236, 236, 236);
    _rect(image, 110, 116, 56, 34, 236, 236, 236);
    final result = LocalImageAnalysis.analyzeClothing(_png(image));
    expect(result.category, ClothingCategory.footwear);
    expect(result.subcategory, 'sneakers');
  });

  test('portrait pair of shoes is footwear not a dress', () {
    final image = img.Image(width: 110, height: 192);
    img.fill(image, color: img.ColorRgb8(248, 248, 248));
    _rect(image, 12, 118, 38, 30, 28, 24, 22);
    _rect(image, 60, 118, 38, 30, 28, 24, 22);
    final result = LocalImageAnalysis.analyzeClothing(_png(image));
    expect(result.category, ClothingCategory.footwear);
    expect(result.subcategory, isNot('dress'));
  });

  test('close-up shoe is footwear not a dress', () {
    final image = _canvas();
    _rect(image, 42, 86, 118, 56, 28, 24, 22);
    _rect(image, 60, 52, 52, 40, 28, 24, 22);
    img.fillCircle(
      image,
      x: 82,
      y: 68,
      radius: 11,
      color: img.ColorRgb8(248, 248, 248),
    );
    final result = LocalImageAnalysis.analyzeClothing(_png(image));
    expect(result.category, ClothingCategory.footwear);
    expect(result.subcategory, isNot('dress'));
  });

  test('stacked shoes stay footwear', () {
    final image = _canvas();
    _rect(image, 58, 40, 70, 40, 32, 28, 26);
    _rect(image, 58, 108, 70, 40, 32, 28, 26);
    final result = LocalImageAnalysis.analyzeClothing(_png(image));
    expect(result.category, ClothingCategory.footwear);
    expect(result.subcategory, isNot(anyOf('dress', 'jewelry')));
  });

  test('low thin pair is flats', () {
    final image = _canvas();
    _rect(image, 22, 132, 60, 16, 28, 24, 22);
    _rect(image, 110, 132, 60, 16, 28, 24, 22);
    final result = LocalImageAnalysis.analyzeClothing(_png(image));
    expect(result.category, ClothingCategory.footwear);
    expect(result.subcategory, 'flats');
  });

  test('top-down leather cap is a hat not a skirt', () {
    final image = _canvas();
    img.fillCircle(
      image,
      x: 96,
      y: 72,
      radius: 34,
      color: img.ColorRgb8(42, 28, 22),
    );
    img.fillCircle(
      image,
      x: 96,
      y: 68,
      radius: 14,
      color: img.ColorRgb8(28, 18, 14),
    );
    final result = LocalImageAnalysis.analyzeClothing(_png(image));
    expect(result.category, ClothingCategory.accessories);
    expect(result.subcategory, 'hat');
    expect(result.subcategory, isNot(anyOf('skirt', 'bag', 'belt')));
  });

  test('larger table-top newsboy cap is a hat not shorts or shoes', () {
    final image = _canvas();
    img.fillCircle(
      image,
      x: 96,
      y: 86,
      radius: 40,
      color: img.ColorRgb8(28, 22, 18),
    );
    _rect(image, 72, 112, 48, 12, 28, 22, 18);
    img.fillCircle(
      image,
      x: 96,
      y: 80,
      radius: 9,
      color: img.ColorRgb8(18, 14, 12),
    );
    final result = LocalImageAnalysis.analyzeClothing(_png(image));
    expect(result.category, ClothingCategory.accessories);
    expect(result.subcategory, 'hat');
    expect(
      result.subcategory,
      isNot(anyOf('shorts', 'shoes', 'skirt', 'bag')),
    );
  });

  test('local hat is not overwritten by a silhouette skirt', () {
    final resolved = ClothingCatalog.resolvePrediction(
      localCategory: ClothingCategory.accessories,
      localSubcategory: 'hat',
      localConfidence: 0.86,
      mlCategory: ClothingCategory.lowerwear,
      mlSubcategory: 'skirt',
      mlConfidence: 0.53,
      mlSource: 'silhouette',
      mlUncertain: false,
      mlMessage: 'Detected Skirt (53%).',
    );
    expect(resolved.subcategory, 'hat');
    expect(resolved.category, ClothingCategory.accessories);
  });

  test('local hat is not overwritten by lowerwear shorts', () {
    final resolved = ClothingCatalog.resolvePrediction(
      localCategory: ClothingCategory.accessories,
      localSubcategory: 'hat',
      localConfidence: 0.86,
      mlCategory: ClothingCategory.lowerwear,
      mlSubcategory: 'shorts',
      mlConfidence: 0.80,
      mlSource: 'lowerwear',
      mlUncertain: false,
      mlMessage: 'Detected Shorts (80%).',
    );
    expect(resolved.subcategory, 'hat');
    expect(resolved.category, ClothingCategory.accessories);
  });

  test('local hat is not overwritten by lowerwear skirt', () {
    final resolved = ClothingCatalog.resolvePrediction(
      localCategory: ClothingCategory.accessories,
      localSubcategory: 'hat',
      localConfidence: 0.84,
      mlCategory: ClothingCategory.lowerwear,
      mlSubcategory: 'skirt',
      mlConfidence: 0.71,
      mlSource: 'lowerwear',
      mlUncertain: false,
      mlMessage: 'Detected Skirt (71%).',
    );
    expect(resolved.subcategory, 'hat');
    expect(resolved.category, ClothingCategory.accessories);
  });

  test('local hat is not overwritten by an accessory bag', () {
    final resolved = ClothingCatalog.resolvePrediction(
      localCategory: ClothingCategory.accessories,
      localSubcategory: 'hat',
      localConfidence: 0.84,
      mlCategory: ClothingCategory.accessories,
      mlSubcategory: 'bag',
      mlConfidence: 0.72,
      mlSource: 'accessory',
      mlUncertain: false,
      mlMessage: 'Detected Bag (72%).',
    );
    expect(resolved.subcategory, 'hat');
    expect(resolved.category, ClothingCategory.accessories);
  });

  test('accessory hat overrides a local skirt guess', () {
    final resolved = ClothingCatalog.resolvePrediction(
      localCategory: ClothingCategory.lowerwear,
      localSubcategory: 'skirt',
      localConfidence: 0.80,
      mlCategory: ClothingCategory.accessories,
      mlSubcategory: 'hat',
      mlConfidence: 0.64,
      mlSource: 'accessory',
      mlUncertain: false,
      mlMessage: 'Detected Hat (64%).',
    );
    expect(resolved.subcategory, 'hat');
    expect(resolved.category, ClothingCategory.accessories);
  });

  test('local hat is not overwritten by accessory shoes', () {
    final resolved = ClothingCatalog.resolvePrediction(
      localCategory: ClothingCategory.accessories,
      localSubcategory: 'hat',
      localConfidence: 0.84,
      mlCategory: ClothingCategory.footwear,
      mlSubcategory: 'shoes',
      mlConfidence: 0.72,
      mlSource: 'accessory',
      mlUncertain: false,
      mlMessage: 'Detected Shoes (72%).',
    );
    expect(resolved.subcategory, 'hat');
    expect(resolved.category, ClothingCategory.accessories);
  });

  test('confident local hat survives a weak ImageNet shoe guess', () {
    final resolved = ClothingCatalog.resolvePrediction(
      localCategory: ClothingCategory.accessories,
      localSubcategory: 'hat',
      localConfidence: 0.91,
      mlCategory: ClothingCategory.footwear,
      mlSubcategory: 'shoes',
      mlConfidence: 0.31,
      mlSource: 'imagenet',
      mlUncertain: false,
      mlMessage: 'Detected Shoes (31%).',
    );
    expect(resolved.subcategory, 'hat');
    expect(resolved.category, ClothingCategory.accessories);
  });

  test('confident local bag survives a weak external shoe guess', () {
    final resolved = ClothingCatalog.resolvePrediction(
      localCategory: ClothingCategory.accessories,
      localSubcategory: 'bag',
      localConfidence: 0.88,
      mlCategory: ClothingCategory.footwear,
      mlSubcategory: 'shoes',
      mlConfidence: 0.22,
      mlSource: 'accessory',
      mlUncertain: false,
      mlMessage: 'Detected Shoes (22%).',
    );
    expect(resolved.subcategory, 'bag');
    expect(resolved.category, ClothingCategory.accessories);
  });

  test('anchor veto releases a low-confidence local hat guess', () {
    final resolved = ClothingCatalog.resolvePrediction(
      localCategory: ClothingCategory.accessories,
      localSubcategory: 'hat',
      localConfidence: 0.30,
      mlCategory: ClothingCategory.footwear,
      mlSubcategory: 'shoes',
      mlConfidence: 0.81,
      mlSource: 'accessory',
      mlUncertain: false,
      mlMessage: 'Detected Shoes (81%).',
    );
    expect(resolved.subcategory, 'shoes');
    expect(resolved.category, ClothingCategory.footwear);
  });

  test('vetoed ML leaves an uncertain local guess unknown', () {
    final resolved = ClothingCatalog.resolvePrediction(
      localCategory: ClothingCategory.accessories,
      localSubcategory: ClothingCatalog.unknownType,
      localConfidence: 0.20,
      mlCategory: ClothingCategory.footwear,
      mlSubcategory: 'shoes',
      mlConfidence: 0.11,
      mlSource: 'imagenet',
      mlUncertain: true,
    );
    expect(resolved.subcategory, ClothingCatalog.unknownType);
    expect(resolved.usedFallback, isTrue);
  });

  test('brimmed crown is a hat', () {
    final image = _canvas();
    img.fillCircle(
      image,
      x: 96,
      y: 58,
      radius: 26,
      color: img.ColorRgb8(28, 24, 22),
    );
    _rect(image, 46, 72, 100, 14, 28, 24, 22);
    final result = LocalImageAnalysis.analyzeClothing(_png(image));
    expect(result.category, ClothingCategory.accessories);
    expect(result.subcategory, 'hat');
  });

  test('column one-piece is a dress', () {
    final image = img.Image(width: 120, height: 192);
    img.fill(image, color: img.ColorRgb8(248, 248, 248));
    _rect(image, 38, 18, 28, 28, 40, 36, 48);
    _rect(image, 32, 44, 56, 136, 40, 36, 48);
    final result = LocalImageAnalysis.analyzeClothing(_png(image));
    expect(result.category, ClothingCategory.dress);
    expect(result.subcategory, 'dress');
  });

  test('dark two-lens frame is sunglasses', () {
    final image = _canvas();
    img.fillCircle(
      image,
      x: 70,
      y: 86,
      radius: 18,
      color: img.ColorRgb8(24, 22, 20),
    );
    img.fillCircle(
      image,
      x: 122,
      y: 86,
      radius: 18,
      color: img.ColorRgb8(24, 22, 20),
    );
    _rect(image, 86, 82, 20, 8, 24, 22, 20);
    final result = LocalImageAnalysis.analyzeClothing(_png(image));
    expect(result.category, ClothingCategory.accessories);
    expect(result.subcategory, 'sunglasses');
  });

  test('silver hoop is jewelry not a watch or hat', () {
    final image = _canvas();
    img.fillCircle(
      image,
      x: 96,
      y: 96,
      radius: 20,
      color: img.ColorRgb8(160, 164, 168),
    );
    img.fillCircle(
      image,
      x: 96,
      y: 96,
      radius: 12,
      color: img.ColorRgb8(248, 248, 248),
    );
    final result = LocalImageAnalysis.analyzeClothing(_png(image));
    expect(result.category, ClothingCategory.accessories);
    expect(result.subcategory, 'jewelry');
  });

  test('portrait one-piece is a dress not trousers', () {
    final image = img.Image(width: 110, height: 192);
    img.fill(image, color: img.ColorRgb8(248, 248, 248));
    for (var i = 0; i < 10; i++) {
      final w = 36 + i * 5;
      _rect(image, 55 - w ~/ 2, 8 + i * 17, w, 17, 40, 36, 48);
    }
    final result = LocalImageAnalysis.analyzeClothing(_png(image));
    expect(result.category, ClothingCategory.dress);
    expect(result.subcategory, isNot(anyOf('trousers', 'jeans', 'skirt')));
  });

  test('close-up dark sneaker is footwear not a hoodie', () {
    final image = _canvas();
    _rect(image, 22, 64, 148, 78, 28, 26, 30);
    img.fillCircle(
      image,
      x: 58,
      y: 88,
      radius: 16,
      color: img.ColorRgb8(248, 248, 248),
    );
    final result = LocalImageAnalysis.analyzeClothing(_png(image));
    expect(result.category, ClothingCategory.footwear);
    expect(result.subcategory, isNot(anyOf('hoodie', 'shirt', 't-shirt', 'jacket')));
  });

  test('navy one-piece is a dress not jeans', () {
    final image = img.Image(width: 120, height: 192);
    img.fill(image, color: img.ColorRgb8(248, 248, 248));
    _rect(image, 40, 16, 40, 32, 28, 32, 70);
    _rect(image, 28, 46, 64, 132, 28, 32, 70);
    final result = LocalImageAnalysis.analyzeClothing(_png(image));
    expect(result.category, ClothingCategory.dress);
    expect(result.subcategory, isNot(anyOf('jeans', 'trousers', 'skirt')));
  });

  test('wide brim hat is a hat not flats', () {
    final image = _canvas();
    img.fillCircle(
      image,
      x: 96,
      y: 70,
      radius: 22,
      color: img.ColorRgb8(28, 24, 22),
    );
    _rect(image, 28, 84, 136, 14, 28, 24, 22);
    final result = LocalImageAnalysis.analyzeClothing(_png(image));
    expect(result.category, ClothingCategory.accessories);
    expect(result.subcategory, 'hat');
    expect(result.subcategory, isNot(anyOf('flats', 'heels', 'shoes')));
  });

  test('l-shape brim hat is a hat not heels', () {
    final image = _canvas();
    _rect(image, 70, 40, 52, 48, 28, 24, 22);
    _rect(image, 40, 82, 112, 16, 28, 24, 22);
    final result = LocalImageAnalysis.analyzeClothing(_png(image));
    expect(result.category, ClothingCategory.accessories);
    expect(result.subcategory, 'hat');
    expect(result.subcategory, isNot('heels'));
  });

  test('tote bag is a bag not a dress', () {
    final image = _canvas();
    _rect(image, 58, 46, 76, 100, 118, 72, 40);
    _rect(image, 72, 34, 48, 14, 118, 72, 40);
    final result = LocalImageAnalysis.analyzeClothing(_png(image));
    expect(result.category, ClothingCategory.accessories);
    expect(result.subcategory, 'bag');
    expect(result.category, isNot(ClothingCategory.dress));
  });

  test('handled tote is a bag not heels', () {
    final image = _canvas();
    _rect(image, 56, 72, 80, 88, 40, 28, 22);
    _rect(image, 68, 38, 14, 40, 40, 28, 22);
    _rect(image, 68, 38, 56, 12, 40, 28, 22);
    _rect(image, 110, 38, 14, 40, 40, 28, 22);
    final result = LocalImageAnalysis.analyzeClothing(_png(image));
    expect(result.category, ClothingCategory.accessories);
    expect(result.subcategory, 'bag');
    expect(result.subcategory, isNot(anyOf('heels', 'shoes', 'hat')));
  });

  test('canvas bag panel is a bag not a skirt', () {
    final image = _canvas();
    _rect(image, 54, 48, 84, 96, 210, 190, 160);
    final result = LocalImageAnalysis.analyzeClothing(_png(image));
    expect(result.subcategory, 'bag');
    expect(result.category, ClothingCategory.accessories);
    expect(result.subcategory, isNot(anyOf('skirt', 'belt', 'heels')));
  });

  test('local bag is not overwritten by ImageNet belt', () {
    final resolved = ClothingCatalog.resolvePrediction(
      localCategory: ClothingCategory.accessories,
      localSubcategory: 'bag',
      localConfidence: 0.84,
      mlCategory: ClothingCategory.accessories,
      mlSubcategory: 'belt',
      mlConfidence: 0.80,
      mlSource: 'imagenet',
      mlUncertain: false,
      mlMessage: 'Detected belt with ImageNet MobileNetV2.',
    );
    expect(resolved.subcategory, 'bag');
    expect(resolved.category, ClothingCategory.accessories);
    expect(resolved.message.toLowerCase(), contains('bag'));
    expect(resolved.message.toLowerCase(), isNot(contains('belt')));
  });

  test('belt ImageNet message does not stay when the type is skirt', () {
    final resolved = ClothingCatalog.resolvePrediction(
      localCategory: ClothingCategory.lowerwear,
      localSubcategory: 'skirt',
      localConfidence: 0.84,
      mlCategory: ClothingCategory.lowerwear,
      mlSubcategory: 'skirt',
      mlConfidence: 0.70,
      mlSource: 'imagenet',
      mlUncertain: false,
      mlMessage: 'Detected belt with ImageNet MobileNetV2.',
    );
    expect(resolved.subcategory, 'skirt');
    expect(resolved.message.toLowerCase(), isNot(contains('belt')));
  });

  test('shoulder bag body is a bag not heels', () {
    final image = _canvas();
    _rect(image, 60, 64, 72, 78, 28, 24, 22);
    _rect(image, 88, 40, 16, 32, 28, 24, 22);
    final result = LocalImageAnalysis.analyzeClothing(_png(image));
    expect(result.subcategory, 'bag');
    expect(result.category, ClothingCategory.accessories);
    expect(result.subcategory, isNot('heels'));
  });

  test('bag veto wins when ML guesses heels', () {
    final resolved = ClothingCatalog.resolvePrediction(
      localCategory: ClothingCategory.accessories,
      localSubcategory: 'bag',
      localConfidence: 0.84,
      mlCategory: ClothingCategory.footwear,
      mlSubcategory: 'heels',
      mlConfidence: 0.91,
      mlSource: 'imagenet',
      mlUncertain: false,
    );
    expect(resolved.subcategory, 'bag');
    expect(resolved.category, ClothingCategory.accessories);
  });

  test('ML bag overrides a local heel guess', () {
    final resolved = ClothingCatalog.resolvePrediction(
      localCategory: ClothingCategory.footwear,
      localSubcategory: 'heels',
      localConfidence: 0.88,
      mlCategory: ClothingCategory.accessories,
      mlSubcategory: 'bag',
      mlConfidence: 0.28,
      mlSource: 'imagenet',
      mlUncertain: false,
    );
    expect(resolved.subcategory, 'bag');
    expect(resolved.category, ClothingCategory.accessories);
  });

  test('local bag wins when ML guesses jewellery', () {
    final resolved = ClothingCatalog.resolvePrediction(
      localCategory: ClothingCategory.accessories,
      localSubcategory: 'bag',
      localConfidence: 0.84,
      mlCategory: ClothingCategory.accessories,
      mlSubcategory: 'jewelry',
      mlConfidence: 0.88,
      mlSource: 'imagenet',
      mlUncertain: false,
    );
    expect(resolved.subcategory, 'bag');
    expect(resolved.category, ClothingCategory.accessories);
  });

  test('accessory bag overrides a local jewellery guess', () {
    final resolved = ClothingCatalog.resolvePrediction(
      localCategory: ClothingCategory.accessories,
      localSubcategory: 'jewelry',
      localConfidence: 0.80,
      mlCategory: ClothingCategory.accessories,
      mlSubcategory: 'bag',
      mlConfidence: 0.78,
      mlSource: 'accessory',
      mlUncertain: false,
    );
    expect(resolved.subcategory, 'bag');
    expect(resolved.category, ClothingCategory.accessories);
  });

  test('gold compact rectangle is a bag not jewellery', () {
    final image = _canvas();
    _rect(image, 52, 50, 88, 92, 206, 164, 48);
    final result = LocalImageAnalysis.analyzeClothing(_png(image));
    expect(result.subcategory, 'bag');
    expect(result.subcategory, isNot(anyOf('jewelry', 'heels', 'shoes')));
  });

  test('clutch panel is a bag not shoes', () {
    final image = _canvas();
    _rect(image, 48, 70, 96, 50, 28, 24, 22);
    final result = LocalImageAnalysis.analyzeClothing(_png(image));
    expect(result.subcategory, 'bag');
    expect(result.category, ClothingCategory.accessories);
    expect(result.subcategory, isNot(anyOf('heels', 'shoes', 'flats', 'jewelry')));
  });

  test('A-line skirt is a skirt not heels', () {
    final image = _canvas();
    for (var i = 0; i < 6; i++) {
      final w = 44 + i * 8;
      _rect(image, 96 - w ~/ 2, 70 + i * 14, w, 14, 40, 36, 90);
    }
    final result = LocalImageAnalysis.analyzeClothing(_png(image));
    expect(result.category, ClothingCategory.lowerwear);
    expect(result.subcategory, 'skirt');
    expect(result.subcategory, isNot(anyOf('heels', 'shoes', 'dress', 'bag')));
  });

  test('long hanging skirt is a skirt not a one-piece', () {
    final image = _canvas();
    for (var i = 0; i < 8; i++) {
      final w = 50 + i * 6;
      _rect(image, 96 - w ~/ 2, 52 + i * 16, w, 16, 48, 40, 96);
    }
    final result = LocalImageAnalysis.analyzeClothing(_png(image));
    expect(result.subcategory, 'skirt');
    expect(result.category, ClothingCategory.lowerwear);
    expect(result.category, isNot(ClothingCategory.dress));
  });

  test('local skirt wins when ML guesses a one-piece', () {
    final resolved = ClothingCatalog.resolvePrediction(
      localCategory: ClothingCategory.lowerwear,
      localSubcategory: 'skirt',
      localConfidence: 0.84,
      mlCategory: ClothingCategory.dress,
      mlSubcategory: 'gown',
      mlConfidence: 0.70,
      mlSource: 'imagenet',
      mlUncertain: false,
    );
    expect(resolved.subcategory, 'skirt');
    expect(resolved.category, ClothingCategory.lowerwear);
  });

  test('mini skirt panel is a skirt not heels', () {
    final image = _canvas();
    for (var i = 0; i < 4; i++) {
      final w = 56 + i * 10;
      _rect(image, 96 - w ~/ 2, 88 + i * 16, w, 16, 28, 32, 80);
    }
    final result = LocalImageAnalysis.analyzeClothing(_png(image));
    expect(result.subcategory, 'skirt');
    expect(result.category, ClothingCategory.lowerwear);
    expect(result.subcategory, isNot(anyOf('heels', 'bag', 'hat')));
  });

  test('skirt veto wins when ML guesses heels', () {
    final resolved = ClothingCatalog.resolvePrediction(
      localCategory: ClothingCategory.lowerwear,
      localSubcategory: 'skirt',
      localConfidence: 0.84,
      mlCategory: ClothingCategory.footwear,
      mlSubcategory: 'heels',
      mlConfidence: 0.91,
      mlSource: 'imagenet',
      mlUncertain: false,
    );
    expect(resolved.subcategory, 'skirt');
    expect(resolved.category, ClothingCategory.lowerwear);
  });

  test('ML skirt overrides a local heel guess', () {
    final resolved = ClothingCatalog.resolvePrediction(
      localCategory: ClothingCategory.footwear,
      localSubcategory: 'heels',
      localConfidence: 0.88,
      mlCategory: ClothingCategory.lowerwear,
      mlSubcategory: 'skirt',
      mlConfidence: 0.28,
      mlSource: 'imagenet',
      mlUncertain: false,
    );
    expect(resolved.subcategory, 'skirt');
    expect(resolved.category, ClothingCategory.lowerwear);
  });

  test('ImageNet skirt does not overwrite a local bag', () {
    final resolved = ClothingCatalog.resolvePrediction(
      localCategory: ClothingCategory.accessories,
      localSubcategory: 'bag',
      localConfidence: 0.86,
      mlCategory: ClothingCategory.lowerwear,
      mlSubcategory: 'skirt',
      mlConfidence: 0.28,
      mlSource: 'imagenet',
      mlUncertain: false,
    );
    expect(resolved.subcategory, 'bag');
    expect(resolved.category, ClothingCategory.accessories);
  });

  test('ImageNet skirt does not overwrite local shorts', () {
    final resolved = ClothingCatalog.resolvePrediction(
      localCategory: ClothingCategory.lowerwear,
      localSubcategory: 'shorts',
      localConfidence: 0.82,
      mlCategory: ClothingCategory.lowerwear,
      mlSubcategory: 'skirt',
      mlConfidence: 0.44,
      mlSource: 'imagenet',
      mlUncertain: false,
    );
    expect(resolved.subcategory, 'shorts');
  });

  test('ImageNet skirt does not overwrite a local dress', () {
    final resolved = ClothingCatalog.resolvePrediction(
      localCategory: ClothingCategory.dress,
      localSubcategory: 'dress',
      localConfidence: 0.84,
      mlCategory: ClothingCategory.lowerwear,
      mlSubcategory: 'skirt',
      mlConfidence: 0.50,
      mlSource: 'imagenet',
      mlUncertain: false,
    );
    expect(resolved.subcategory, 'dress');
    expect(resolved.category, ClothingCategory.dress);
  });

  test('skirt display name stays Skirt not Long Skirt', () {
    expect(ClothingCatalog.displayNameFor('skirt'), 'Skirt');
    expect(ClothingCatalog.displayNameFor('dress'), 'Dress');
    expect(ClothingCatalog.displayNameFor('shorts'), 'Shorts');
    expect(ClothingCatalog.displayNameFor('top'), 'Top');
  });

  test('top alias stays top instead of collapsing to t-shirt', () {
    expect(
      ClothingCatalog.normalizeDetection(
        category: ClothingCategory.upperwear,
        subcategory: 'top',
      ),
      (ClothingCategory.upperwear, 'top'),
    );
  });

  test('ImageNet bag is not overwritten by a local skirt guess', () {
    final resolved = ClothingCatalog.resolvePrediction(
      localCategory: ClothingCategory.lowerwear,
      localSubcategory: 'skirt',
      localConfidence: 0.84,
      mlCategory: ClothingCategory.accessories,
      mlSubcategory: 'bag',
      mlConfidence: 0.72,
      mlSource: 'imagenet',
      mlUncertain: false,
    );
    expect(resolved.subcategory, 'bag');
    expect(resolved.category, ClothingCategory.accessories);
  });

  test('local bag is not overwritten by ImageNet hat', () {
    final resolved = ClothingCatalog.resolvePrediction(
      localCategory: ClothingCategory.accessories,
      localSubcategory: 'bag',
      localConfidence: 0.84,
      mlCategory: ClothingCategory.accessories,
      mlSubcategory: 'hat',
      mlConfidence: 0.80,
      mlSource: 'imagenet',
      mlUncertain: false,
    );
    expect(resolved.subcategory, 'bag');
    expect(resolved.category, ClothingCategory.accessories);
  });

  test('local dress is not overwritten by ImageNet bag', () {
    final resolved = ClothingCatalog.resolvePrediction(
      localCategory: ClothingCategory.dress,
      localSubcategory: 'dress',
      localConfidence: 0.86,
      mlCategory: ClothingCategory.accessories,
      mlSubcategory: 'bag',
      mlConfidence: 0.42,
      mlSource: 'imagenet',
      mlUncertain: false,
    );
    expect(resolved.subcategory, 'dress');
    expect(resolved.category, ClothingCategory.dress);
  });

  test('baseball cap is a hat not a shirt', () {
    final image = _canvas();
    img.fillCircle(
      image,
      x: 96,
      y: 62,
      radius: 30,
      color: img.ColorRgb8(36, 40, 120),
    );
    _rect(image, 96, 68, 58, 16, 36, 40, 120);
    final result = LocalImageAnalysis.analyzeClothing(_png(image));
    expect(result.category, ClothingCategory.accessories);
    expect(result.subcategory, 'hat');
    expect(result.subcategory, isNot(anyOf('shirt', 't-shirt', 'hoodie')));
  });

  test('close-up navy cap filling the frame is a hat not a shirt', () {
    final image = _canvas();
    img.fillCircle(
      image,
      x: 96,
      y: 88,
      radius: 50,
      color: img.ColorRgb8(28, 34, 90),
    );
    _rect(image, 96, 112, 72, 24, 28, 34, 90);
    final result = LocalImageAnalysis.analyzeClothing(_png(image));
    expect(result.category, ClothingCategory.accessories);
    expect(result.subcategory, 'hat');
    expect(
      result.subcategory,
      isNot(anyOf('shirt', 't-shirt', 'hoodie', 'jacket')),
    );
  });

  test('red close-up cap is a hat not a t-shirt', () {
    final image = _canvas();
    img.fillCircle(
      image,
      x: 96,
      y: 86,
      radius: 46,
      color: img.ColorRgb8(198, 36, 42),
    );
    _rect(image, 96, 108, 68, 22, 198, 36, 42);
    final result = LocalImageAnalysis.analyzeClothing(_png(image));
    expect(result.subcategory, 'hat');
    expect(result.subcategory, isNot(anyOf('shirt', 't-shirt')));
  });

  test('centered cap stays a hat not a shirt or jeans', () {
    final image = _canvas();
    img.fillCircle(
      image,
      x: 96,
      y: 88,
      radius: 28,
      color: img.ColorRgb8(40, 44, 48),
    );
    _rect(image, 96, 96, 54, 14, 40, 44, 48);
    final result = LocalImageAnalysis.analyzeClothing(_png(image));
    expect(result.subcategory, 'hat');
    expect(
      result.subcategory,
      isNot(anyOf('shirt', 't-shirt', 'dress', 'jeans', 'trousers')),
    );
  });

  test('side visor baseball cap is a hat not heels', () {
    final image = _canvas();
    img.fillCircle(
      image,
      x: 78,
      y: 62,
      radius: 34,
      color: img.ColorRgb8(32, 38, 110),
    );
    _rect(image, 78, 78, 86, 16, 32, 38, 110);
    final result = LocalImageAnalysis.analyzeClothing(_png(image));
    expect(result.category, ClothingCategory.accessories);
    expect(result.subcategory, 'hat');
    expect(result.subcategory, isNot(anyOf('heels', 'shoes', 'flats')));
  });

  test('close-up visor cap is a hat not heels', () {
    final image = _canvas();
    img.fillCircle(
      image,
      x: 88,
      y: 80,
      radius: 48,
      color: img.ColorRgb8(18, 18, 22),
    );
    _rect(image, 88, 104, 90, 22, 18, 18, 22);
    final result = LocalImageAnalysis.analyzeClothing(_png(image));
    expect(result.subcategory, 'hat');
    expect(result.category, ClothingCategory.accessories);
    expect(result.subcategory, isNot('heels'));
  });

  test('hat veto wins when ML guesses heels', () {
    final resolved = ClothingCatalog.resolvePrediction(
      localCategory: ClothingCategory.accessories,
      localSubcategory: 'hat',
      localConfidence: 0.82,
      mlCategory: ClothingCategory.footwear,
      mlSubcategory: 'heels',
      mlConfidence: 0.90,
      mlSource: 'imagenet',
      mlUncertain: false,
    );
    expect(resolved.subcategory, 'hat');
    expect(resolved.category, ClothingCategory.accessories);
  });

  test('ML hat overrides a local heel guess', () {
    final resolved = ClothingCatalog.resolvePrediction(
      localCategory: ClothingCategory.footwear,
      localSubcategory: 'heels',
      localConfidence: 0.88,
      mlCategory: ClothingCategory.accessories,
      mlSubcategory: 'hat',
      mlConfidence: 0.41,
      mlSource: 'imagenet',
      mlUncertain: false,
    );
    expect(resolved.subcategory, 'hat');
    expect(resolved.category, ClothingCategory.accessories);
  });

  test('hat veto wins when ML guesses shirt', () {
    final resolved = ClothingCatalog.resolvePrediction(
      localCategory: ClothingCategory.accessories,
      localSubcategory: 'hat',
      localConfidence: 0.84,
      mlCategory: ClothingCategory.upperwear,
      mlSubcategory: 'shirt',
      mlConfidence: 0.91,
      mlSource: 'finetuned',
      mlUncertain: false,
    );
    expect(resolved.subcategory, 'hat');
    expect(resolved.category, ClothingCategory.accessories);
  });

  test('local dress is not overwritten by ImageNet hat', () {
    final resolved = ClothingCatalog.resolvePrediction(
      localCategory: ClothingCategory.dress,
      localSubcategory: 'dress',
      localConfidence: 0.84,
      mlCategory: ClothingCategory.accessories,
      mlSubcategory: 'hat',
      mlConfidence: 0.88,
      mlSource: 'imagenet',
      mlUncertain: false,
    );
    expect(resolved.subcategory, 'dress');
    expect(resolved.category, ClothingCategory.dress);
  });

  test('local shirt is not overwritten by ImageNet hat', () {
    final resolved = ClothingCatalog.resolvePrediction(
      localCategory: ClothingCategory.upperwear,
      localSubcategory: 'shirt',
      localConfidence: 0.84,
      mlCategory: ClothingCategory.accessories,
      mlSubcategory: 'hat',
      mlConfidence: 0.88,
      mlSource: 'imagenet',
      mlUncertain: false,
      mlMessage: 'Detected hat in blue.',
    );
    expect(resolved.subcategory, 'shirt');
    expect(resolved.category, ClothingCategory.upperwear);
  });

  test('local trousers are not overwritten by ImageNet hat', () {
    final resolved = ClothingCatalog.resolvePrediction(
      localCategory: ClothingCategory.lowerwear,
      localSubcategory: 'trousers',
      localConfidence: 0.82,
      mlCategory: ClothingCategory.accessories,
      mlSubcategory: 'hat',
      mlConfidence: 0.70,
      mlSource: 'imagenet',
      mlUncertain: false,
    );
    expect(resolved.subcategory, 'trousers');
    expect(resolved.category, ClothingCategory.lowerwear);
  });

  test('local jeans are not overwritten by ImageNet hat', () {
    final resolved = ClothingCatalog.resolvePrediction(
      localCategory: ClothingCategory.lowerwear,
      localSubcategory: 'jeans',
      localConfidence: 0.80,
      mlCategory: ClothingCategory.accessories,
      mlSubcategory: 'hat',
      mlConfidence: 0.65,
      mlSource: 'imagenet',
      mlUncertain: false,
    );
    expect(resolved.subcategory, 'jeans');
    expect(resolved.category, ClothingCategory.lowerwear);
  });

  test('local trousers are not overwritten by an accessory bag', () {
    final resolved = ClothingCatalog.resolvePrediction(
      localCategory: ClothingCategory.lowerwear,
      localSubcategory: 'trousers',
      localConfidence: 0.88,
      mlCategory: ClothingCategory.accessories,
      mlSubcategory: 'bag',
      mlConfidence: 0.69,
      mlSource: 'accessory',
      mlUncertain: false,
    );
    expect(resolved.subcategory, 'trousers');
    expect(resolved.category, ClothingCategory.lowerwear);
  });

  test('lowerwear trousers override a weak local hat guess', () {
    final resolved = ClothingCatalog.resolvePrediction(
      localCategory: ClothingCategory.accessories,
      localSubcategory: 'hat',
      localConfidence: 0.40,
      mlCategory: ClothingCategory.lowerwear,
      mlSubcategory: 'trousers',
      mlConfidence: 0.72,
      mlSource: 'lowerwear',
      mlUncertain: false,
      mlMessage: 'Detected Trousers/Pants.',
    );
    expect(resolved.subcategory, 'trousers');
    expect(resolved.category, ClothingCategory.lowerwear);
  });

  test('local trousers are not overwritten by a silhouette dress', () {
    final resolved = ClothingCatalog.resolvePrediction(
      localCategory: ClothingCategory.lowerwear,
      localSubcategory: 'trousers',
      localConfidence: 0.86,
      mlCategory: ClothingCategory.dress,
      mlSubcategory: 'dress',
      mlConfidence: 0.78,
      mlSource: 'silhouette',
      mlUncertain: false,
      mlMessage: 'Detected dress.',
    );
    expect(resolved.subcategory, 'trousers');
    expect(resolved.category, ClothingCategory.lowerwear);
  });

  test('silhouette dress overrides a local hat guess', () {
    final resolved = ClothingCatalog.resolvePrediction(
      localCategory: ClothingCategory.accessories,
      localSubcategory: 'hat',
      localConfidence: 0.80,
      mlCategory: ClothingCategory.dress,
      mlSubcategory: 'dress',
      mlConfidence: 0.82,
      mlSource: 'silhouette',
      mlUncertain: false,
    );
    expect(resolved.subcategory, 'dress');
    expect(resolved.category, ClothingCategory.dress);
  });

  test('local dress is not overwritten by ImageNet shoes', () {
    final resolved = ClothingCatalog.resolvePrediction(
      localCategory: ClothingCategory.dress,
      localSubcategory: 'dress',
      localConfidence: 0.84,
      mlCategory: ClothingCategory.footwear,
      mlSubcategory: 'shoes',
      mlConfidence: 0.88,
      mlSource: 'imagenet',
      mlUncertain: false,
    );
    expect(resolved.subcategory, 'dress');
    expect(resolved.category, ClothingCategory.dress);
  });

  test('silhouette dress overrides a local shoe guess', () {
    final resolved = ClothingCatalog.resolvePrediction(
      localCategory: ClothingCategory.footwear,
      localSubcategory: 'shoes',
      localConfidence: 0.80,
      mlCategory: ClothingCategory.dress,
      mlSubcategory: 'dress',
      mlConfidence: 0.82,
      mlSource: 'silhouette',
      mlUncertain: false,
    );
    expect(resolved.subcategory, 'dress');
    expect(resolved.category, ClothingCategory.dress);
  });

  test('lowerwear trousers override a local dress guess', () {
    final resolved = ClothingCatalog.resolvePrediction(
      localCategory: ClothingCategory.dress,
      localSubcategory: 'dress',
      localConfidence: 0.86,
      mlCategory: ClothingCategory.lowerwear,
      mlSubcategory: 'trousers',
      mlConfidence: 0.91,
      mlSource: 'lowerwear',
      mlUncertain: false,
      mlMessage: 'Detected Trousers/Pants (91%).',
    );
    expect(resolved.subcategory, 'trousers');
    expect(resolved.category, ClothingCategory.lowerwear);
    expect(resolved.usedFallback, isFalse);
  });

  test('silhouette trousers override a local dress guess', () {
    final resolved = ClothingCatalog.resolvePrediction(
      localCategory: ClothingCategory.dress,
      localSubcategory: 'dress',
      localConfidence: 0.84,
      mlCategory: ClothingCategory.lowerwear,
      mlSubcategory: 'trousers',
      mlConfidence: 0.80,
      mlSource: 'silhouette',
      mlUncertain: false,
      mlMessage: 'Detected Trousers/Pants (80%).',
    );
    expect(resolved.subcategory, 'trousers');
    expect(resolved.category, ClothingCategory.lowerwear);
  });

  test('ImageNet jeans are not rewritten as a local dress', () {
    final resolved = ClothingCatalog.resolvePrediction(
      localCategory: ClothingCategory.dress,
      localSubcategory: 'dress',
      localConfidence: 0.81,
      mlCategory: ClothingCategory.lowerwear,
      mlSubcategory: 'jeans',
      mlConfidence: 0.88,
      mlSource: 'imagenet',
      mlUncertain: false,
      mlMessage: 'Detected jeans.',
    );
    expect(resolved.subcategory, 'jeans');
    expect(resolved.category, ClothingCategory.lowerwear);
  });

  test('ImageNet trousers are not rewritten as a local dress', () {
    final resolved = ClothingCatalog.resolvePrediction(
      localCategory: ClothingCategory.dress,
      localSubcategory: 'dress',
      localConfidence: 0.84,
      mlCategory: ClothingCategory.lowerwear,
      mlSubcategory: 'trousers',
      mlConfidence: 0.79,
      mlSource: 'imagenet',
      mlUncertain: false,
      mlMessage: 'Detected trousers.',
    );
    expect(resolved.subcategory, 'trousers');
    expect(resolved.category, ClothingCategory.lowerwear);
  });

  test('close-up footwear overrides a local trousers guess', () {
    final resolved = ClothingCatalog.resolvePrediction(
      localCategory: ClothingCategory.lowerwear,
      localSubcategory: 'trousers',
      localConfidence: 0.69,
      mlCategory: ClothingCategory.footwear,
      mlSubcategory: 'sandals',
      mlConfidence: 0.34,
      mlSource: 'accessory',
      mlUncertain: false,
      mlMessage: 'Detected sandals (34%).',
    );
    expect(resolved.subcategory, 'sandals');
    expect(resolved.category, ClothingCategory.footwear);
  });

  test('ImageNet accessory at modest confidence fills an unknown type', () {
    final resolved = ClothingCatalog.resolvePrediction(
      localCategory: ClothingCategory.accessories,
      localSubcategory: ClothingCatalog.unknownType,
      localConfidence: 0.20,
      mlCategory: ClothingCategory.accessories,
      mlSubcategory: 'watch',
      mlConfidence: 0.31,
      mlSource: 'imagenet',
      mlUncertain: false,
    );
    expect(resolved.subcategory, 'watch');
    expect(resolved.category, ClothingCategory.accessories);
    expect(resolved.usedFallback, isFalse);
  });

  test('uncertain ML does not overwrite a confident local label', () {
    final resolved = ClothingCatalog.resolvePrediction(
      localCategory: ClothingCategory.footwear,
      localSubcategory: 'shoes',
      localConfidence: 0.86,
      mlCategory: ClothingCategory.upperwear,
      mlSubcategory: ClothingCatalog.unknownType,
      mlConfidence: 0.22,
      mlSource: 'imagenet',
      mlUncertain: true,
    );
    expect(resolved.subcategory, 'shoes');
  });

  test('two short legs are shorts not a skirt', () {
    final image = _canvas();
    _rect(image, 40, 70, 48, 70, 40, 70, 48);
    _rect(image, 104, 70, 48, 70, 40, 70, 48);
    final result = LocalImageAnalysis.analyzeClothing(_png(image));
    expect(result.category, ClothingCategory.lowerwear);
    expect(result.subcategory, 'shorts');
    expect(result.subcategory, isNot(anyOf('skirt', 'dress')));
  });

  test('lowerwear shorts override a local skirt guess', () {
    final resolved = ClothingCatalog.resolvePrediction(
      localCategory: ClothingCategory.lowerwear,
      localSubcategory: 'skirt',
      localConfidence: 0.84,
      mlCategory: ClothingCategory.lowerwear,
      mlSubcategory: 'shorts',
      mlConfidence: 0.81,
      mlSource: 'lowerwear',
      mlUncertain: false,
    );
    expect(resolved.subcategory, 'shorts');
    expect(resolved.category, ClothingCategory.lowerwear);
  });

  test('lowerwear trousers override a local skirt guess', () {
    final resolved = ClothingCatalog.resolvePrediction(
      localCategory: ClothingCategory.lowerwear,
      localSubcategory: 'skirt',
      localConfidence: 0.80,
      mlCategory: ClothingCategory.lowerwear,
      mlSubcategory: 'trousers',
      mlConfidence: 0.77,
      mlSource: 'lowerwear',
      mlUncertain: false,
    );
    expect(resolved.subcategory, 'trousers');
  });

  test('local shorts are not overwritten by ImageNet trousers', () {
    final resolved = ClothingCatalog.resolvePrediction(
      localCategory: ClothingCategory.lowerwear,
      localSubcategory: 'shorts',
      localConfidence: 0.80,
      mlCategory: ClothingCategory.lowerwear,
      mlSubcategory: 'trousers',
      mlConfidence: 0.70,
      mlSource: 'imagenet',
      mlUncertain: false,
    );
    expect(resolved.subcategory, 'shorts');
  });

  test('lowerwear keeps denim as jeans when ML says trousers', () {
    final resolved = ClothingCatalog.resolvePrediction(
      localCategory: ClothingCategory.lowerwear,
      localSubcategory: 'jeans',
      localConfidence: 0.82,
      mlCategory: ClothingCategory.lowerwear,
      mlSubcategory: 'trousers',
      mlConfidence: 0.79,
      mlSource: 'lowerwear',
      mlUncertain: false,
    );
    expect(resolved.subcategory, 'jeans');
  });

  test('low-confidence lowerwear stays unknown', () {
    final resolved = ClothingCatalog.resolvePrediction(
      localCategory: ClothingCategory.accessories,
      localSubcategory: ClothingCatalog.unknownType,
      localConfidence: 0.20,
      mlCategory: ClothingCategory.accessories,
      mlSubcategory: ClothingCatalog.unknownType,
      mlConfidence: 0.33,
      mlSource: 'lowerwear',
      mlUncertain: true,
      mlMessage: 'Uncertain between trousers, shorts, and skirt.',
    );
    expect(resolved.subcategory, ClothingCatalog.unknownType);
    expect(resolved.usedFallback, isTrue);
  });

  test('pressed-together pant legs are trousers not a dress', () {
    final image = _canvas();
    _rect(image, 64, 22, 64, 20, 28, 28, 30);
    _rect(image, 64, 40, 28, 140, 24, 24, 26);
    _rect(image, 96, 40, 28, 140, 24, 24, 26);
    final result = LocalImageAnalysis.analyzeClothing(_png(image));
    expect(result.category, ClothingCategory.lowerwear);
    expect(result.subcategory, anyOf('trousers', 'jeans'));
    expect(result.subcategory, isNot('dress'));
  });

  test('two separate pant legs are trousers not a skirt or dress', () {
    final image = _canvas();
    _rect(image, 48, 44, 36, 136, 48, 44, 92);
    _rect(image, 108, 44, 36, 136, 48, 44, 92);
    final result = LocalImageAnalysis.analyzeClothing(_png(image));
    expect(result.subcategory, anyOf('trousers', 'jeans'));
    expect(result.category, ClothingCategory.lowerwear);
    expect(result.subcategory, isNot(anyOf('skirt', 'dress', 'heels', 'shoes')));
  });

  test('wide-leg palazzo pants are trousers not a long skirt', () {
    final image = _canvas();
    _rect(image, 24, 50, 62, 128, 52, 48, 88);
    _rect(image, 106, 50, 62, 128, 52, 48, 88);
    final result = LocalImageAnalysis.analyzeClothing(_png(image));
    expect(result.subcategory, anyOf('trousers', 'jeans'));
    expect(result.category, ClothingCategory.lowerwear);
    expect(result.subcategory, isNot(anyOf('skirt', 'dress')));
  });

  test('blue jean legs are pants not a long skirt', () {
    final image = _canvas();
    _rect(image, 50, 40, 38, 140, 36, 68, 150);
    _rect(image, 104, 40, 38, 140, 36, 68, 150);
    final result = LocalImageAnalysis.analyzeClothing(_png(image));
    expect(result.subcategory, anyOf('jeans', 'trousers'));
    expect(result.subcategory, isNot(anyOf('skirt', 'dress')));
  });

  test('silhouette pants override a local skirt guess', () {
    final resolved = ClothingCatalog.resolvePrediction(
      localCategory: ClothingCategory.lowerwear,
      localSubcategory: 'skirt',
      localConfidence: 0.84,
      mlCategory: ClothingCategory.lowerwear,
      mlSubcategory: 'trousers',
      mlConfidence: 0.78,
      mlSource: 'silhouette',
      mlUncertain: false,
    );
    expect(resolved.subcategory, 'trousers');
    expect(resolved.category, ClothingCategory.lowerwear);
  });

  test('upperwear specialist hoodie beats a local shirt guess', () {
    final resolved = ClothingCatalog.resolvePrediction(
      localCategory: ClothingCategory.upperwear,
      localSubcategory: 'shirt',
      localConfidence: 0.72,
      mlCategory: ClothingCategory.upperwear,
      mlSubcategory: 'hoodie',
      mlConfidence: 0.61,
      mlSource: 'upperwear',
      mlUncertain: false,
      mlMessage: 'Detected Hoodie (61%).',
    );
    expect(resolved.subcategory, 'hoodie');
    expect(resolved.category, ClothingCategory.upperwear);
    expect(resolved.usedFallback, isFalse);
  });

  test('upperwear specialist gown is kept as dress', () {
    final resolved = ClothingCatalog.resolvePrediction(
      localCategory: ClothingCategory.upperwear,
      localSubcategory: 'shirt',
      localConfidence: 0.70,
      mlCategory: ClothingCategory.dress,
      mlSubcategory: 'dress',
      mlConfidence: 0.66,
      mlSource: 'upperwear',
      mlUncertain: false,
      mlMessage: 'Detected Dress (66%).',
    );
    expect(resolved.subcategory, 'dress');
    expect(resolved.category, ClothingCategory.dress);
  });

  test('silhouette long dress overrides a local skirt guess', () {
    final resolved = ClothingCatalog.resolvePrediction(
      localCategory: ClothingCategory.lowerwear,
      localSubcategory: 'skirt',
      localConfidence: 0.82,
      mlCategory: ClothingCategory.dress,
      mlSubcategory: 'dress',
      mlConfidence: 0.81,
      mlSource: 'silhouette',
      mlUncertain: false,
    );
    expect(resolved.subcategory, 'dress');
    expect(resolved.category, ClothingCategory.dress);
  });

  test('low-confidence silhouette stays unknown instead of mixing classes', () {
    final resolved = ClothingCatalog.resolvePrediction(
      localCategory: ClothingCategory.accessories,
      localSubcategory: ClothingCatalog.unknownType,
      localConfidence: 0.22,
      mlCategory: ClothingCategory.accessories,
      mlSubcategory: ClothingCatalog.unknownType,
      mlConfidence: 0.31,
      mlSource: 'silhouette',
      mlUncertain: true,
      mlMessage: 'Uncertain between long dress, pants, and long skirt.',
    );
    expect(resolved.subcategory, ClothingCatalog.unknownType);
    expect(resolved.usedFallback, isTrue);
  });

  test('unknown alias stays unknown instead of falling back to shirt', () {
    final mapped = ClothingCatalog.normalizeDetection(
      category: ClothingCategory.upperwear,
      subcategory: 'uncertain',
    );
    expect(mapped.$2, ClothingCatalog.unknownType);
  });
}

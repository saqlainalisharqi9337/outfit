import 'dart:math';

import 'outfit_part_weights.dart';

class ClothingDescriptor {
  const ClothingDescriptor({
    required this.features,
    required this.color,
    this.secondaryColor,
    required this.lShape,
    required this.heightFrac,
    required this.occupancy,
    required this.aspect,
    required this.flare,
    required this.upperMass,
    required this.denim,
    required this.fill,
    required this.blobs,
    required this.hollow,
    required this.largestBlob,
    required this.cy,
    required this.lowerCenterFill,
    required this.edgeRatio,
    required this.topFrac,
  });

  final List<double> features;
  final String color;
  final String? secondaryColor;
  final bool lShape;
  final double heightFrac;
  final double occupancy;
  final double aspect;
  final double flare;
  final double upperMass;
  final bool denim;
  final double fill;
  final int blobs;
  final double hollow;
  final int largestBlob;
  final double cy;
  final double lowerCenterFill;
  final double edgeRatio;
  final double topFrac;
}

class OutfitPrediction {
  const OutfitPrediction(this.label, this.confidence);
  final String label;
  final double confidence;
}

/// Hierarchical softmax trained by `flutter pub run tool/train_outfit_part.dart`.
class OutfitPartModel {
  static List<OutfitPrediction> _ranked(
    List<double> features,
    List<String> labels,
    List<List<double>> weights,
    List<double> bias,
  ) {
    final logits = List<double>.filled(labels.length, 0);
    var maxLogit = -1e9;
    for (var c = 0; c < labels.length; c++) {
      var sum = bias[c];
      final row = weights[c];
      final n = min(row.length, features.length);
      for (var i = 0; i < n; i++) {
        sum += row[i] * features[i];
      }
      logits[c] = sum;
      if (sum > maxLogit) maxLogit = sum;
    }
    var denom = 0.0;
    final scores = List<double>.filled(labels.length, 0);
    for (var c = 0; c < labels.length; c++) {
      scores[c] = pow(e, logits[c] - maxLogit).toDouble();
      denom += scores[c];
    }
    final ranked = <OutfitPrediction>[
      for (var c = 0; c < labels.length; c++)
        OutfitPrediction(labels[c], scores[c] / denom),
    ]..sort((a, b) => b.confidence.compareTo(a.confidence));
    return ranked;
  }

  static List<OutfitPrediction> rankedFamily(List<double> features) {
    return _ranked(
      features,
      OutfitPartWeights.familyLabels,
      OutfitPartWeights.familyWeights,
      OutfitPartWeights.familyBias,
    );
  }

  static OutfitPrediction predictFamily(List<double> features) {
    return rankedFamily(features).first;
  }

  static OutfitPrediction predictFootwear(List<double> features) {
    return _ranked(
      features,
      OutfitPartWeights.footwearLabels,
      OutfitPartWeights.footwearWeights,
      OutfitPartWeights.footwearBias,
    ).first;
  }

  static OutfitPrediction predictBottom(List<double> features) {
    return _ranked(
      features,
      OutfitPartWeights.bottomLabels,
      OutfitPartWeights.bottomWeights,
      OutfitPartWeights.bottomBias,
    ).first;
  }

  static OutfitPrediction predictTop(List<double> features) {
    return _ranked(
      features,
      OutfitPartWeights.topLabels,
      OutfitPartWeights.topWeights,
      OutfitPartWeights.topBias,
    ).first;
  }

  static OutfitPrediction predictAccessory(List<double> features) {
    return _ranked(
      features,
      OutfitPartWeights.accessoryLabels,
      OutfitPartWeights.accessoryWeights,
      OutfitPartWeights.accessoryBias,
    ).first;
  }

  static String leafForFamily(String family, List<double> features) {
    return switch (family) {
      'accessory' => predictAccessory(features).label,
      'footwear' => predictFootwear(features).label,
      'dress' => 'dress',
      'lowerwear' => predictBottom(features).label,
      'upperwear' => predictTop(features).label,
      _ => 'shirt',
    };
  }

  static OutfitPrediction predict(List<double> features) {
    final family = predictFamily(features);
    return OutfitPrediction(
      leafForFamily(family.label, features),
      family.confidence,
    );
  }

  static List<OutfitPrediction> predictRanked(List<double> features) {
    return [
      predictFootwear(features),
      predictTop(features),
      predictBottom(features),
      predictAccessory(features),
      OutfitPrediction(
        'dress',
        predictFamily(features).label == 'dress'
            ? predictFamily(features).confidence
            : 0.05,
      ),
    ]..sort((a, b) => b.confidence.compareTo(a.confidence));
  }
}

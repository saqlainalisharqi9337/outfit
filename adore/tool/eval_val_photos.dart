import 'dart:io';

import 'package:adore/services/local_image_analysis.dart';
import 'package:adore/utils/clothing_catalog.dart';

const _root = r'D:\fyp project\dataset';
const _folders = <String, String>{
  'bag': r'val\val\accessories\bag',
  'hat': r'val\val\accessories\hat',
  'trousers': r'val\val\bottomwear\pants',
  'shorts': r'val\val\bottomwear\shorts',
  'skirt': r'val\val\bottomwear\skirt',
  'flats': r'val\val\footwear\flats',
  'heels': r'val\val\footwear\heels',
  'shoes': r'val\val\footwear\shoes',
  'sneakers': r'val\val\footwear\sneakers',
  'dress': r'val\val\one-piece\dress',
  'jacket': r'val\val\upperwear\jacket',
  'shirt': r'val\val\upperwear\shirt',
  't-shirt': r'val\val\upperwear\tshirt',
};

String _family(String sub) {
  final f = ClothingCatalog.familyOf(sub);
  if (f == 'jewelry' || f == 'accessory') return 'accessory';
  return f;
}

void main() {
  var leafHit = 0, famHit = 0, tot = 0;
  for (final entry in _folders.entries) {
    final dir = Directory('$_root\\${entry.value}');
    if (!dir.existsSync()) continue;
    final files = dir
        .listSync()
        .whereType<File>()
        .where((f) {
          final n = f.path.toLowerCase();
          return n.endsWith('.png') || n.endsWith('.jpg') || n.endsWith('.jpeg');
        })
        .take(40)
        .toList();
    var hit = 0, fam = 0, n = 0;
    final counts = <String, int>{};
    for (final file in files) {
      final result = LocalImageAnalysis.analyzeClothing(file.readAsBytesSync());
      n++;
      tot++;
      counts[result.subcategory] = (counts[result.subcategory] ?? 0) + 1;
      if (result.subcategory == entry.key) {
        hit++;
        leafHit++;
      }
      if (_family(result.subcategory) == _family(entry.key)) {
        fam++;
        famHit++;
      }
    }
    if (n > 0) {
      stdout.writeln(
        '${entry.key.padRight(10)} leaf ${(100 * hit / n).toStringAsFixed(0)}%  '
        'family ${(100 * fam / n).toStringAsFixed(0)}%  $counts',
      );
    }
  }
  stdout.writeln(
    'overall     leaf ${(100 * leafHit / tot).toStringAsFixed(1)}%  '
    'family ${(100 * famHit / tot).toStringAsFixed(1)}%  ($tot photos)',
  );
}

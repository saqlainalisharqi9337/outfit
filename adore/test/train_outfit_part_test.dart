import 'package:flutter_test/flutter_test.dart';

import '../tool/train_outfit_part.dart';

void main() {
  test(
    'trains the outfit-part model and writes weights',
    () {
      trainOutfitPart();
    },
    skip: 'Run manually when retraining: flutter test test/train_outfit_part_test.dart --plain-name trains',
    timeout: const Timeout(Duration(minutes: 4)),
  );
}

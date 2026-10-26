import 'package:adore/services/demo_store.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('demo session seeds a complete FYP profile and wardrobe', () {
    final store = DemoStore.instance;
    store.start();
    expect(store.active, isTrue);
    expect(store.profile.onboardingComplete, isTrue);
    expect(store.profile.city, 'Muzaffarabad');
    expect(store.wardrobe.length, 10);
    expect(store.events.length, 3);
    store.stop();
    expect(store.active, isFalse);
  });
}

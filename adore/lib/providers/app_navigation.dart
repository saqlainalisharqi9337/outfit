import 'package:flutter/foundation.dart';

/// Bottom-nav index so Home shortcuts can switch tabs without a new route.
class AppNavigation extends ChangeNotifier {
  static const home = 0;
  static const calendar = 1;
  static const adroble = 2;
  static const shop = 3;
  static const profile = 4;

  int index = 0;

  void goTo(int value) {
    if (index == value) return;
    index = value;
    notifyListeners();
  }
}

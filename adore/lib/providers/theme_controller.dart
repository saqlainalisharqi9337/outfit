import 'package:flutter/material.dart';

import 'theme_file_stub.dart'
    if (dart.library.io) 'theme_file_io.dart';

/// Light/dark choice for every screen. Stored on the device, not in Supabase.
class ThemeController extends ChangeNotifier {
  ThemeMode mode = ThemeMode.light;

  bool get isDark => mode == ThemeMode.dark;

  Future<void> load() async {
    try {
      final value = await readThemeMode();
      if (value == null) return;
      mode = value == 'dark' ? ThemeMode.dark : ThemeMode.light;
      notifyListeners();
    } catch (_) {}
  }

  Future<void> setDark(bool dark) async {
    mode = dark ? ThemeMode.dark : ThemeMode.light;
    notifyListeners();
    try {
      await writeThemeMode(dark ? 'dark' : 'light');
    } catch (_) {}
  }
}

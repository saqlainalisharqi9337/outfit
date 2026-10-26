import 'dart:io';

import 'package:path_provider/path_provider.dart';

Future<String?> readThemeMode() async {
  final dir = await getApplicationSupportDirectory();
  final file = File('${dir.path}${Platform.pathSeparator}adore_theme.txt');
  if (!await file.exists()) return null;
  return (await file.readAsString()).trim();
}

Future<void> writeThemeMode(String value) async {
  final dir = await getApplicationSupportDirectory();
  final file = File('${dir.path}${Platform.pathSeparator}adore_theme.txt');
  await file.writeAsString(value);
}

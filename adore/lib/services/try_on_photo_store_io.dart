import 'dart:io';
import 'dart:typed_data';

import 'package:path_provider/path_provider.dart';

Future<Uint8List?> loadPersonPhoto() async {
  final file = await _file();
  if (!await file.exists()) return null;
  return file.readAsBytes();
}

Future<void> savePersonPhoto(Uint8List bytes) async {
  final file = await _file();
  await file.writeAsBytes(bytes, flush: true);
}

Future<File> _file() async {
  final dir = await getApplicationDocumentsDirectory();
  return File('${dir.path}/try_on_person.jpg');
}

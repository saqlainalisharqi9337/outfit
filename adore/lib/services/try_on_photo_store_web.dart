import 'dart:typed_data';

Uint8List? _person;

Future<Uint8List?> loadPersonPhoto() async => _person;

Future<void> savePersonPhoto(Uint8List bytes) async {
  _person = bytes;
}

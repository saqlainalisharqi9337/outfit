import 'dart:typed_data';

import 'try_on_photo_store_io.dart'
    if (dart.library.html) 'try_on_photo_store_web.dart' as impl;

/// The try-on photo stays on the device. It is uploaded only while generating.
class TryOnPhotoStore {
  static Future<Uint8List?> loadPerson() => impl.loadPersonPhoto();

  static Future<void> savePerson(Uint8List bytes) => impl.savePersonPhoto(bytes);
}

import 'package:flutter/foundation.dart';
import 'package:flutter_image_compress/flutter_image_compress.dart';
import 'package:image/image.dart' as img;
import 'package:supabase_flutter/supabase_flutter.dart';
import 'package:uuid/uuid.dart';

import '../config/supabase_config.dart';
import '../utils/constants.dart';
import '../utils/exceptions.dart' as app;
import 'demo_store.dart';

class StorageService {
  StorageService({SupabaseClient? client})
      : _client = client ?? Supabase.instance.client;

  final SupabaseClient _client;
  final _uuid = const Uuid();

  Future<Uint8List> compress(Uint8List bytes) async {
    if (!kIsWeb) {
      try {
        final result = await FlutterImageCompress.compressWithList(
          bytes,
          minWidth: AppConstants.imageMaxWidth,
          quality: AppConstants.imageQuality,
        );
        if (result.isNotEmpty) return Uint8List.fromList(result);
      } catch (_) {}
    }
    final decoded = img.decodeImage(bytes);
    if (decoded == null) return bytes;
    final resized = decoded.width > AppConstants.imageMaxWidth
        ? img.copyResize(decoded, width: AppConstants.imageMaxWidth)
        : decoded;
    return Uint8List.fromList(
      img.encodeJpg(resized, quality: AppConstants.imageQuality),
    );
  }

  Future<String> uploadBytes({
    required String bucket,
    required String path,
    required Uint8List bytes,
    String contentType = 'image/jpeg',
    void Function(double progress)? onProgress,
  }) async {
    if (DemoStore.instance.active) {
      final compressed = await compress(bytes);
      onProgress?.call(1);
      return Uri.dataFromBytes(compressed, mimeType: contentType).toString();
    }
    try {
      final compressed = await compress(bytes);
      onProgress?.call(0.2);
      await _client.storage.from(bucket).uploadBinary(
            path,
            compressed,
            fileOptions: FileOptions(
              contentType: contentType,
              upsert: true,
            ),
          );
      onProgress?.call(1);
      return _client.storage.from(bucket).getPublicUrl(path);
    } catch (_) {
      throw app.StorageException('Image upload failed. Please retry.');
    }
  }

  Future<String> uploadProfileImage({
    required String uid,
    required Uint8List bytes,
    void Function(double progress)? onProgress,
  }) {
    return uploadBytes(
      bucket: SupabaseConfig.avatarsBucket,
      path: '$uid/profile/${_uuid.v4()}.jpg',
      bytes: bytes,
      onProgress: onProgress,
    );
  }

  Future<String> uploadWardrobeImage({
    required String uid,
    required Uint8List bytes,
    void Function(double progress)? onProgress,
  }) {
    return uploadBytes(
      bucket: SupabaseConfig.wardrobeBucket,
      path: '$uid/items/${_uuid.v4()}.jpg',
      bytes: bytes,
      onProgress: onProgress,
    );
  }

  Future<void> deleteByUrl(String url) async {
    if (DemoStore.instance.active || url.startsWith('data:')) return;
    try {
      final uri = Uri.parse(url);
      final parts = uri.pathSegments;
      final publicIndex = parts.indexOf('public');
      if (publicIndex < 0 || publicIndex + 2 >= parts.length) return;
      final bucket = parts[publicIndex + 1];
      final objectPath = parts.sublist(publicIndex + 2).join('/');
      await _client.storage.from(bucket).remove([objectPath]);
    } catch (_) {}
  }
}

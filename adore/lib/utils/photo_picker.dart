import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

import '../theme/app_theme.dart';
import 'webcam_unsupported.dart' if (dart.library.html) 'webcam_web.dart'
    as webcam;

enum PhotoPickMode { camera, gallery }

class PhotoPicker {
  static Future<PhotoPickMode?> chooseSource(BuildContext context) {
    return showModalBottomSheet<PhotoPickMode>(
      context: context,
      showDragHandle: true,
      builder: (ctx) {
        return SafeArea(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(16, 0, 16, 20),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Text(
                  'Add a photo',
                  style: TextStyle(fontWeight: FontWeight.w700, fontSize: 16),
                ),
                const SizedBox(height: 8),
                ListTile(
                  leading: const Icon(Icons.photo_camera_outlined,
                      color: AppColors.primary),
                  title: const Text('Take a picture'),
                  subtitle: const Text('Use the camera'),
                  onTap: () => Navigator.pop(ctx, PhotoPickMode.camera),
                ),
                ListTile(
                  leading: const Icon(Icons.photo_library_outlined,
                      color: AppColors.primary),
                  title: const Text('Upload from gallery'),
                  subtitle: const Text('Choose an existing photo'),
                  onTap: () => Navigator.pop(ctx, PhotoPickMode.gallery),
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  static Future<Uint8List?> pick(
    BuildContext context, {
    required PhotoPickMode mode,
    bool selfie = false,
  }) async {
    if (mode == PhotoPickMode.gallery) {
      return _fromPicker(ImageSource.gallery, selfie: selfie);
    }
    if (kIsWeb) {
      final live = await webcam.captureWebcam(context, selfie: selfie);
      if (live != null) return live;
    }
    return _fromPicker(ImageSource.camera, selfie: selfie);
  }

  static Future<Uint8List?> pickWithSheet(
    BuildContext context, {
    bool selfie = false,
  }) async {
    final mode = await chooseSource(context);
    if (mode == null || !context.mounted) return null;
    return pick(context, mode: mode, selfie: selfie);
  }

  static Future<Uint8List?> _fromPicker(
    ImageSource source, {
    bool selfie = false,
  }) async {
    final file = await ImagePicker().pickImage(
      source: source,
      imageQuality: 85,
      preferredCameraDevice:
          selfie ? CameraDevice.front : CameraDevice.rear,
    );
    if (file == null) return null;
    return file.readAsBytes();
  }
}

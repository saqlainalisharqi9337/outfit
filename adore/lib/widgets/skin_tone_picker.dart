import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../services/image_analysis_service.dart';
import '../theme/app_theme.dart';
import '../utils/enums.dart';
import '../utils/exceptions.dart';
import '../utils/photo_picker.dart';

/// Manual skin-tone choice plus camera/gallery extraction.
class SkinTonePicker extends StatelessWidget {
  const SkinTonePicker({
    super.key,
    required this.value,
    required this.onChanged,
    this.busy = false,
    this.message,
    this.onBusy,
    this.onMessage,
  });

  final SkinTone? value;
  final ValueChanged<SkinTone> onChanged;
  final bool busy;
  final String? message;
  final ValueChanged<bool>? onBusy;
  final ValueChanged<String?>? onMessage;

  Future<void> _fromPhoto(BuildContext context, PhotoPickMode mode) async {
    try {
      final bytes = await PhotoPicker.pick(
        context,
        mode: mode,
        selfie: true,
      );
      if (bytes == null) return;
      onBusy?.call(true);
      onMessage?.call('Reading skin tone from the photo…');
      if (!context.mounted) return;
      final result = await context.read<ImageAnalysisService>().analyzeSkinTone(
            bytes,
            previous: value,
          );
      onChanged(result.skinTone);
      onMessage?.call(
        result.message ??
            'Suggested ${result.skinTone.label}. You can tap another tone if this is wrong.',
      );
    } on AppException catch (e) {
      onMessage?.call(e.message);
    } catch (_) {
      onMessage?.call('Could not open the photo. Pick a tone below instead.');
    } finally {
      onBusy?.call(false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'Choose your skin tone, or take a face photo and Adore will suggest one.',
        ),
        const SizedBox(height: 12),
        Row(
          children: [
            Expanded(
              child: FilledButton.tonal(
                onPressed: busy ? null : () => _fromPhoto(context, PhotoPickMode.camera),
                child: const Text('Take photo'),
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: OutlinedButton(
                onPressed: busy ? null : () => _fromPhoto(context, PhotoPickMode.gallery),
                child: const Text('From gallery'),
              ),
            ),
          ],
        ),
        if (busy)
          const Padding(
            padding: EdgeInsets.only(top: 12),
            child: LinearProgressIndicator(),
          ),
        if (message != null)
          Padding(
            padding: const EdgeInsets.only(top: 8),
            child: Text(message!),
          ),
        const SizedBox(height: 16),
        const Text('Or select manually'),
        const SizedBox(height: 8),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: [
            for (final tone in SkinTone.values)
              ChoiceChip(
                label: Text(tone.label),
                selected: value == tone,
                onSelected: (_) => onChanged(tone),
              ),
          ],
        ),
        if (value != null)
          Padding(
            padding: const EdgeInsets.only(top: 8),
            child: Text(
              'Selected: ${value!.label}',
              style: const TextStyle(color: AppColors.muted),
            ),
          ),
      ],
    );
  }
}

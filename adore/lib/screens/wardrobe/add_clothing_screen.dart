import 'dart:math';
import 'dart:typed_data';
import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:uuid/uuid.dart';

import '../../models/product_model.dart';
import '../../models/wardrobe_item.dart';
import '../../providers/auth_provider.dart';
import '../../providers/wardrobe_provider.dart';
import '../../services/image_analysis_service.dart';
import '../../theme/app_theme.dart';
import '../../utils/clothing_catalog.dart';
import '../../utils/enums.dart';
import '../../utils/exceptions.dart';
import '../../utils/photo_picker.dart';
import '../../widgets/common.dart';

class AddClothingScreen extends StatefulWidget {
  const AddClothingScreen({super.key});

  @override
  State<AddClothingScreen> createState() => _AddClothingScreenState();
}

class _AddClothingScreenState extends State<AddClothingScreen> {
  Uint8List? _bytes;
  ClothingCategory _category = ClothingCategory.upperwear;
  String _subcategory = 'shirt';
  String _color = 'black';
  String? _secondary;
  String _pattern = 'solid';
  final String _material = 'cotton';
  String _style = 'casual';
  Formality _formality = Formality.casual;
  bool _busy = false;
  String? _message;
  double? _confidence;
  List<DetectedClothingItem> _detected = const [];
  bool _teachModel = true;
  double _imageWidth = 0;
  double _imageHeight = 0;
  bool _awaitingType = false;

  Future<void> _capture(PhotoPickMode mode) async {
    try {
      final bytes = await PhotoPicker.pick(context, mode: mode);
      if (bytes == null) return;
      final size = await _imageSize(bytes);
      setState(() {
        _bytes = bytes;
        _imageWidth = size.$1;
        _imageHeight = size.$2;
        _message = 'Preview the photo. Analyzing…';
        _detected = const [];
      });
      await _analyze();
    } catch (_) {
      setState(() => _message = 'Camera permission denied or unavailable.');
    }
  }

  Future<(double, double)> _imageSize(Uint8List bytes) async {
    try {
      final codec = await ui.instantiateImageCodec(bytes);
      final frame = await codec.getNextFrame();
      final width = frame.image.width.toDouble();
      final height = frame.image.height.toDouble();
      frame.image.dispose();
      codec.dispose();
      return (width, height);
    } catch (_) {
      return (0.0, 0.0);
    }
  }

  Future<void> _analyze() async {
    if (_bytes == null) return;
    setState(() {
      _busy = true;
      _message = null;
    });
    try {
      final result =
          await context.read<ImageAnalysisService>().analyzeClothing(_bytes!);
      setState(() {
        _color = result.color;
        _secondary = result.secondaryColor ??
            (result.secondaryColors.isNotEmpty
                ? ClothingCatalog.catalogColor(result.secondaryColors.first)
                : null);
        if (ClothingCatalog.patterns.contains(result.pattern)) {
          _pattern = result.pattern;
        }
        _confidence = result.confidence;
        _detected = result.detectedItems;
        if (result.subcategory == ClothingCatalog.unknownType ||
            result.usedFallback) {
          DetectedClothingItem? pants;
          for (final item in result.detectedItems) {
            if ({'trousers', 'jeans', 'shorts'}.contains(item.subcategory) &&
                (pants == null || item.confidence > pants.confidence)) {
              pants = item;
            }
          }
          if (pants != null && pants.confidence >= 0.50) {
            _awaitingType = false;
            _category = ClothingCategory.lowerwear;
            _subcategory = pants.subcategory;
            _formality =
                ClothingCatalog.formalityForSubcategory(pants.subcategory);
            _message = result.message ??
                'Detected ${ClothingCatalog.displayNameFor(pants.subcategory)}.';
            return;
          }
          _awaitingType = true;
          _category = ClothingCategory.accessories;
          _subcategory = '';
          _detected = const [];
          _confidence = null;
          _message = result.message ??
              'Not recognized. Please choose the category and type.';
          return;
        }
        _awaitingType = false;
        _category = result.category;
        _subcategory = result.subcategory;
        _formality = ClothingCatalog.formalityForSubcategory(result.subcategory);
        _message = result.message ??
            'Detected ${ClothingCatalog.displayNameFor(result.subcategory)} · ${result.color}'
                '${result.secondaryColors.isEmpty ? '' : ' / ${result.secondaryColors.join(', ')}'}'
                '${result.pattern == 'solid' ? '' : ' · ${ClothingCatalog.patternLabel(result.pattern)}'}'
                ' (${(result.confidence * 100).round()}%). Change the fields below if this is wrong.';
      });
    } on AppException catch (e) {
      setState(() => _message = e.message);
    } finally {
      setState(() => _busy = false);
    }
  }

  void _applyDetected(DetectedClothingItem item) {
    final normalized = ClothingCatalog.normalizeDetection(
      category: item.category,
      subcategory: item.subcategory,
    );
    setState(() {
      _category = normalized.$1;
      _subcategory = normalized.$2;
      if (item.color != null && ClothingCatalog.colors.contains(item.color)) {
        _color = item.color!;
      }
      if (item.secondaryColor != null &&
          ClothingCatalog.colors.contains(item.secondaryColor)) {
        _secondary = item.secondaryColor;
      }
      if (item.pattern != null &&
          ClothingCatalog.patterns.contains(item.pattern)) {
        _pattern = item.pattern!;
      }
      _confidence = item.confidence;
      _formality = ClothingCatalog.formalityForSubcategory(_subcategory);
      _message =
          'Selected ${ClothingCatalog.displayNameFor(_subcategory)}'
          '${item.color == null ? '' : ' · ${item.color}'}'
          '${item.secondaryColors.isEmpty ? '' : ' / ${item.secondaryColors.join(', ')}'}'
          ' (${(item.confidence * 100).round()}%). Save, or tap another item.';
    });
  }

  Future<void> _save() async {
    final user = context.read<AuthProvider>().profile;
    if (user == null || _bytes == null) return;
    final allowed = ClothingCatalog.subcategories[_category] ?? const <String>[];
    if (_subcategory.isEmpty || !allowed.contains(_subcategory)) {
      setState(() => _message = 'Please choose the category and type.');
      return;
    }
    setState(() => _busy = true);
    try {
      final draft = WardrobeItem.inferred(
        itemId: const Uuid().v4(),
        userId: user.id,
        imageUrl: '',
        category: _category,
        subcategory: _subcategory,
        color: _color,
        secondaryColor: _secondary,
        aiConfidence: _confidence,
        culture: user.culture,
      ).copyWith(
        pattern: _pattern,
        patternSource: 'user',
        patternConfidence: 1.0,
        material: _material,
        style: _style,
        formality: _formality,
      );
      await context.read<WardrobeProvider>().addItem(
            user: user,
            imageBytes: _bytes!,
            draft: draft,
          );
      if (_teachModel) {
        await context.read<ImageAnalysisService>().teachClothing(
              _bytes!,
              _subcategory,
            );
      }
      if (mounted) Navigator.pop(context);
    } on AppException catch (e) {
      setState(() => _message = e.message);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final wardrobe = context.watch<WardrobeProvider>();
    final subs = ClothingCatalog.subcategories[_category] ?? const <String>[];
    return Scaffold(
      appBar: AppBar(title: const Text('Add to Adorable')),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          if (_bytes == null)
            const Text(
              'Photograph a piece from your cupboard, or pick one from the gallery.',
            )
          else
            GestureDetector(
              onTap: () => showImageLightbox(context, bytes: _bytes),
              child: ClipRRect(
                borderRadius: BorderRadius.circular(20),
                child: Stack(
                  children: [
                    ColoredBox(
                      color: AppColors.cardBorder.withValues(alpha: 0.55),
                      child: SizedBox(
                        height: min(
                          520.0,
                          max(320.0, MediaQuery.sizeOf(context).height * 0.46),
                        ),
                        width: double.infinity,
                        child: Image.memory(_bytes!, fit: BoxFit.contain),
                      ),
                    ),
                    if (_detected.any((e) => e.bbox != null && e.bbox!.length == 4))
                      Positioned.fill(
                        child: IgnorePointer(
                          child: CustomPaint(
                            painter: _DetectionBoxPainter(
                              _detected,
                              imageWidth: _imageWidth,
                              imageHeight: _imageHeight,
                            ),
                          ),
                        ),
                      ),
                    const Positioned(
                      right: 10,
                      bottom: 10,
                      child: DecoratedBox(
                        decoration: BoxDecoration(
                          color: Color(0x99000000),
                          shape: BoxShape.circle,
                        ),
                        child: Padding(
                          padding: EdgeInsets.all(8),
                          child: Icon(
                            Icons.open_in_full,
                            size: 16,
                            color: Colors.white,
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(
                child: OutlinedButton(
                  onPressed: () => _capture(PhotoPickMode.camera),
                  child: const Text('Camera'),
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: OutlinedButton(
                  onPressed: () => _capture(PhotoPickMode.gallery),
                  child: const Text('Gallery'),
                ),
              ),
            ],
          ),
          if (_bytes != null)
            TextButton(
              onPressed: () => _capture(PhotoPickMode.camera),
              child: const Text('Retake'),
            ),
          const SizedBox(height: 8),
          SizedBox(
            width: double.infinity,
            child: FilledButton.tonal(
              onPressed: _bytes == null || _busy ? null : _analyze,
              child: _busy
                  ? const SizedBox(
                      width: 18,
                      height: 18,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Text('Analyze with AI'),
            ),
          ),
          if (_message != null)
            Padding(
              padding: const EdgeInsets.only(top: 12),
              child: Text(_message!),
            ),
          const SizedBox(height: 20),
          if (_detected.isNotEmpty) ...[
            const Text(
              'Visible items — tap one to save it, or remove a wrong box.',
              style: TextStyle(fontWeight: FontWeight.w600),
            ),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                for (final item in _detected)
                  InputChip(
                    label: Text(
                      '${ClothingCatalog.displayNameFor(item.subcategory)}'
                      '${item.color == null ? '' : ' · ${item.color}'}'
                      ' ${(item.confidence * 100).round()}%',
                    ),
                    onPressed: () => _applyDetected(item),
                    onDeleted: () => setState(() {
                      _detected = [
                        for (final row in _detected)
                          if (row != item) row,
                      ];
                    }),
                    deleteIcon: const Icon(Icons.close, size: 16),
                  ),
              ],
            ),
            const SizedBox(height: 12),
          ],
          DropdownButtonFormField<ClothingCategory>(
            key: ValueKey('category-$_category'),
            initialValue: _category,
            isExpanded: true,
            decoration: const InputDecoration(labelText: 'Category'),
            items: [
              for (final c in ClothingCategory.values)
                DropdownMenuItem(
                  value: c,
                  child: Text(c.label, overflow: TextOverflow.ellipsis, maxLines: 1),
                ),
            ],
            onChanged: (v) => setState(() {
              _category = v ?? _category;
              _awaitingType = false;
              _subcategory = (ClothingCatalog.subcategories[_category] ?? ['item']).first;
            }),
          ),
          const SizedBox(height: 8),
          DropdownButtonFormField<String>(
            key: ValueKey('type-$_category-$_subcategory-$_awaitingType'),
            initialValue: _awaitingType
                ? ''
                : (subs.contains(_subcategory) ? _subcategory : subs.first),
            isExpanded: true,
            decoration: const InputDecoration(labelText: 'Type'),
            items: [
              if (_awaitingType)
                const DropdownMenuItem(
                  value: '',
                  child: Text('Select type', overflow: TextOverflow.ellipsis),
                ),
              for (final s in subs)
                DropdownMenuItem(
                  value: s,
                  child: Text(s, overflow: TextOverflow.ellipsis, maxLines: 1),
                ),
            ],
            onChanged: (v) => setState(() => _subcategory = v ?? _subcategory),
          ),
          CheckboxListTile(
            contentPadding: EdgeInsets.zero,
            value: _teachModel,
            onChanged: (v) => setState(() => _teachModel = v ?? true),
            title: const Text('Teach the model this type'),
            subtitle: const Text(
              'If AI was wrong, keep the correct Type and save. '
              'Photos are stored for training; the live model updates after you retrain.',
            ),
            controlAffinity: ListTileControlAffinity.leading,
          ),
          const SizedBox(height: 8),
          DropdownButtonFormField<String>(
            key: ValueKey('color-$_color'),
            initialValue: ClothingCatalog.colors.contains(_color) ? _color : 'black',
            decoration: const InputDecoration(labelText: 'Color'),
            items: [
              for (final c in ClothingCatalog.colors)
                DropdownMenuItem(value: c, child: Text(c)),
            ],
            onChanged: (v) => setState(() => _color = v ?? _color),
          ),
          const SizedBox(height: 8),
          DropdownButtonFormField<Formality>(
            key: ValueKey('formality-$_formality'),
            initialValue: _formality,
            decoration: const InputDecoration(labelText: 'Formality'),
            items: [
              for (final f in Formality.values)
                DropdownMenuItem(value: f, child: Text(f.label)),
            ],
            onChanged: (v) => setState(() => _formality = v ?? _formality),
          ),
          const SizedBox(height: 8),
          DropdownButtonFormField<String>(
            key: ValueKey('pattern-$_pattern'),
            initialValue: ClothingCatalog.patterns.contains(_pattern)
                ? _pattern
                : 'solid',
            decoration: const InputDecoration(
              labelText: 'Pattern',
              helperText: 'Auto-filled from the garment crop. You can change it.',
            ),
            items: [
              for (final p in ClothingCatalog.patterns)
                DropdownMenuItem(
                  value: p,
                  child: Text(ClothingCatalog.patternLabel(p)),
                ),
            ],
            onChanged: (v) => setState(() => _pattern = v ?? _pattern),
          ),
          const SizedBox(height: 8),
          DropdownButtonFormField<String>(
            initialValue: _style,
            decoration: const InputDecoration(labelText: 'Style'),
            items: [
              for (final s in ClothingCatalog.styles)
                DropdownMenuItem(value: s, child: Text(s)),
            ],
            onChanged: (v) => setState(() => _style = v ?? _style),
          ),
          if (wardrobe.uploadProgress != null)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 8),
              child: LinearProgressIndicator(value: wardrobe.uploadProgress),
            ),
          const SizedBox(height: 16),
          FilledButton(
            onPressed: _busy || _bytes == null ? null : _save,
            child: const Text('Save to cupboard'),
          ),
          if (_busy)
            const Padding(
              padding: EdgeInsets.only(top: 12),
              child: Center(child: CircularProgressIndicator()),
            ),
        ],
      ),
    );
  }
}

class _DetectionBoxPainter extends CustomPainter {
  const _DetectionBoxPainter(
    this.items, {
    required this.imageWidth,
    required this.imageHeight,
  });

  final List<DetectedClothingItem> items;
  final double imageWidth;
  final double imageHeight;

  Rect _imageRect(Size size) {
    if (imageWidth <= 0 || imageHeight <= 0) return Offset.zero & size;
    final fitted = applyBoxFit(
      BoxFit.contain,
      Size(imageWidth, imageHeight),
      size,
    );
    final dest = fitted.destination;
    return Rect.fromLTWH(
      (size.width - dest.width) / 2,
      (size.height - dest.height) / 2,
      dest.width,
      dest.height,
    );
  }

  @override
  void paint(Canvas canvas, Size size) {
    final stroke = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2
      ..color = const Color(0xE67A2F45);
    final fill = Paint()
      ..style = PaintingStyle.fill
      ..color = const Color(0xCC7A2F45);
    final frame = _imageRect(size);
    for (final item in items) {
      final box = item.bbox;
      if (box == null || box.length != 4) continue;
      final rect = Rect.fromLTRB(
        frame.left + box[0] * frame.width,
        frame.top + box[1] * frame.height,
        frame.left + box[2] * frame.width,
        frame.top + box[3] * frame.height,
      );
      canvas.drawRect(rect, stroke);
      final label =
          '${item.subcategory} ${(item.confidence * 100).round()}%';
      final tp = TextPainter(
        text: TextSpan(
          text: label,
          style: const TextStyle(color: Colors.white, fontSize: 11),
        ),
        textDirection: TextDirection.ltr,
      )..layout(maxWidth: size.width);
      canvas.drawRect(
        Rect.fromLTWH(rect.left, rect.top, tp.width + 8, tp.height + 4),
        fill,
      );
      tp.paint(canvas, Offset(rect.left + 4, rect.top + 2));
    }
  }

  @override
  bool shouldRepaint(covariant _DetectionBoxPainter oldDelegate) =>
      oldDelegate.items != items ||
      oldDelegate.imageWidth != imageWidth ||
      oldDelegate.imageHeight != imageHeight;
}

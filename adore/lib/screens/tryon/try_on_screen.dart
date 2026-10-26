import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:http/http.dart' as http;
import 'package:share_plus/share_plus.dart';

import '../../services/try_on_photo_store.dart';
import '../../services/try_on_service.dart';
import '../../theme/app_theme.dart';
import '../../utils/photo_picker.dart';

class TryOnScreen extends StatefulWidget {
  const TryOnScreen({
    super.key,
    this.clothingBytes,
    this.clothingUrl,
    this.clothingName,
  });

  final Uint8List? clothingBytes;
  final String? clothingUrl;
  final String? clothingName;

  @override
  State<TryOnScreen> createState() => _TryOnScreenState();
}

class _TryOnScreenState extends State<TryOnScreen> {
  Uint8List? _person;
  Uint8List? _clothing;
  Uint8List? _result;
  bool _busy = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _clothing = widget.clothingBytes;
    _load();
  }

  Future<void> _load() async {
    final saved = await TryOnPhotoStore.loadPerson();
    if (!mounted) return;
    setState(() => _person = saved);
    final url = widget.clothingUrl;
    if (_clothing == null && url != null && url.startsWith('http')) {
      try {
        final response = await http.get(Uri.parse(url)).timeout(
          const Duration(seconds: 20),
        );
        if (!mounted || response.statusCode != 200) return;
        setState(() => _clothing = response.bodyBytes);
      } catch (_) {
        if (!mounted) return;
        setState(() => _error = 'Could not load that clothing photo.');
      }
    }
  }

  Future<void> _pickPerson() async {
    final bytes = await PhotoPicker.pickWithSheet(context, selfie: true);
    if (bytes == null || !mounted) return;
    await TryOnPhotoStore.savePerson(bytes);
    setState(() {
      _person = bytes;
      _result = null;
      _error = null;
    });
  }

  Future<void> _pickClothing() async {
    final bytes = await PhotoPicker.pickWithSheet(context);
    if (bytes == null || !mounted) return;
    setState(() {
      _clothing = bytes;
      _result = null;
      _error = null;
    });
  }

  Future<void> _generate() async {
    final person = _person;
    final clothing = _clothing;
    if (person == null || clothing == null) {
      setState(() => _error = 'Add your photo and a clothing photo first.');
      return;
    }
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final result = await TryOnService().generate(
        person: person,
        clothing: clothing,
      );
      if (!mounted) return;
      setState(() => _result = result.bytes);
    } on TryOnException catch (error) {
      if (!mounted) return;
      setState(() => _error = error.message);
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _error = 'Could not reach the try-on service. Start it, then try again.';
      });
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Virtual try-on')),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(20, 12, 20, 32),
        children: [
          Text(
            'See how it looks on you',
            style: GoogleFonts.playfairDisplay(
              fontSize: 28,
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: 8),
          const Text(
            'Upload your photo once, then add any clothing photo from a shop, your wardrobe, or your gallery.',
            style: TextStyle(color: AppColors.muted, height: 1.35),
          ),
          const SizedBox(height: 18),
          Row(
            children: [
              Expanded(
                child: _PhotoSlot(
                  title: 'You',
                  bytes: _person,
                  action: _person == null ? 'Add photo' : 'Change photo',
                  onPick: _busy ? null : _pickPerson,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: _PhotoSlot(
                  title: widget.clothingName ?? 'Clothing',
                  bytes: _clothing,
                  action: _clothing == null ? 'Add clothing' : 'Change clothing',
                  onPick: _busy ? null : _pickClothing,
                ),
              ),
            ],
          ),
          const SizedBox(height: 18),
          FilledButton(
            onPressed: _busy ? null : _generate,
            child: Padding(
              padding: const EdgeInsets.symmetric(vertical: 12),
              child: Text(_busy ? 'Creating your look…' : 'See it on me'),
            ),
          ),
          if (_busy)
            const Padding(
              padding: EdgeInsets.only(top: 16),
              child: LinearProgressIndicator(),
            ),
          if (_error != null)
            Padding(
              padding: const EdgeInsets.only(top: 12),
              child: Text(_error!, style: const TextStyle(color: AppColors.danger)),
            ),
          if (_result != null) ...[
            const SizedBox(height: 20),
            ClipRRect(
              borderRadius: BorderRadius.circular(20),
              child: Image.memory(_result!, fit: BoxFit.contain),
            ),
            const SizedBox(height: 12),
            OutlinedButton.icon(
              onPressed: () {
                SharePlus.instance.share(
                  ShareParams(
                    files: [
                      XFile.fromData(
                        _result!,
                        mimeType: 'image/jpeg',
                        name: 'adore-try-on.jpg',
                      ),
                    ],
                  ),
                );
              },
              icon: const Icon(Icons.ios_share),
              label: const Text('Share this look'),
            ),
          ],
          const SizedBox(height: 16),
          const Text(
            'Your photo stays on this phone. Magic Hour only receives it while creating the try-on.',
            style: TextStyle(color: AppColors.muted, fontSize: 12, height: 1.35),
          ),
        ],
      ),
    );
  }
}

class TryOnHomeCard extends StatelessWidget {
  const TryOnHomeCard({super.key});

  @override
  Widget build(BuildContext context) {
    final dark = Theme.of(context).brightness == Brightness.dark;
    return DecoratedBox(
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(20),
        color: dark ? AppColors.darkSurface : AppColors.surface,
        border: Border.all(
          color: AppColors.secondary.withValues(alpha: dark ? 0.45 : 0.28),
        ),
      ),
      child: Padding(
        padding: const EdgeInsets.fromLTRB(16, 16, 16, 12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Free virtual try-on',
              style: TextStyle(fontSize: 16, fontWeight: FontWeight.w700),
            ),
            const SizedBox(height: 6),
            const Text(
              'See how clothes look on you before buying. Add your photo once, then any clothing image.',
              style: TextStyle(color: AppColors.muted, height: 1.35),
            ),
            Align(
              alignment: Alignment.centerLeft,
              child: TextButton(
                onPressed: () {
                  Navigator.push(
                    context,
                    MaterialPageRoute(builder: (_) => const TryOnScreen()),
                  );
                },
                child: const Text('Try it on'),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _PhotoSlot extends StatelessWidget {
  const _PhotoSlot({
    required this.title,
    required this.bytes,
    required this.action,
    required this.onPick,
  });

  final String title;
  final Uint8List? bytes;
  final String action;
  final VoidCallback? onPick;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        AspectRatio(
          aspectRatio: 3 / 4,
          child: DecoratedBox(
            decoration: BoxDecoration(
              color: Theme.of(context).colorScheme.surfaceContainerHighest,
              borderRadius: BorderRadius.circular(16),
            ),
            child: ClipRRect(
              borderRadius: BorderRadius.circular(16),
              child: bytes == null
                  ? const Icon(Icons.add_a_photo_outlined, color: AppColors.muted)
                  : Image.memory(bytes!, fit: BoxFit.cover),
            ),
          ),
        ),
        const SizedBox(height: 8),
        Text(
          title,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: const TextStyle(fontWeight: FontWeight.w600),
        ),
        TextButton(onPressed: onPick, child: Text(action)),
      ],
    );
  }
}

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../models/wardrobe_item.dart';
import '../../providers/wardrobe_provider.dart';
import '../../theme/app_theme.dart';
import '../../utils/clothing_catalog.dart';
import '../../utils/enums.dart';
import '../../widgets/common.dart';
import '../tryon/try_on_screen.dart';

class ClothingDetailScreen extends StatefulWidget {
  const ClothingDetailScreen({super.key, required this.item});

  final WardrobeItem item;

  @override
  State<ClothingDetailScreen> createState() => _ClothingDetailScreenState();
}

class _ClothingDetailScreenState extends State<ClothingDetailScreen> {
  late WardrobeItem _item;

  @override
  void initState() {
    super.initState();
    _item = widget.item;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(_item.subcategory),
        actions: [
          IconButton(
            tooltip: 'Delete this piece',
            onPressed: () => _deletePiece(context),
            icon: const Icon(Icons.delete_outline),
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          NetworkImageView(
            url: _item.imageUrl,
            height: (MediaQuery.sizeOf(context).height * 0.46)
                .clamp(320.0, 520.0)
                .toDouble(),
            width: double.infinity,
            fit: BoxFit.contain,
            openOnTap: true,
          ),
          const SizedBox(height: 16),
          DropdownButtonFormField<ClothingCategory>(
            initialValue: _item.category,
            decoration: const InputDecoration(labelText: 'Category'),
            items: [
              for (final c in ClothingCategory.values)
                DropdownMenuItem(value: c, child: Text(c.label)),
            ],
            onChanged: (v) => setState(() {
              final next = v ?? _item.category;
              _item = _item.copyWith(
                category: next,
                subcategory:
                    (ClothingCatalog.subcategories[next] ?? ['item']).first,
              );
            }),
          ),
          const SizedBox(height: 8),
          DropdownButtonFormField<String>(
            key: ValueKey(_item.category.name),
            initialValue: (ClothingCatalog.subcategories[_item.category] ?? const <String>[])
                    .contains(_item.subcategory)
                ? _item.subcategory
                : (ClothingCatalog.subcategories[_item.category] ?? ['item']).first,
            decoration: const InputDecoration(labelText: 'Type'),
            items: [
              for (final s in ClothingCatalog.subcategories[_item.category] ?? const <String>[])
                DropdownMenuItem(value: s, child: Text(s)),
            ],
            onChanged: (v) => setState(() => _item = _item.copyWith(subcategory: v)),
          ),
          const SizedBox(height: 8),
          DropdownButtonFormField<String>(
            initialValue: _item.color,
            decoration: const InputDecoration(labelText: 'Color'),
            items: [
              for (final c in ClothingCatalog.colors)
                DropdownMenuItem(value: c, child: Text(c)),
            ],
            onChanged: (v) => setState(() => _item = _item.copyWith(color: v)),
          ),
          const SizedBox(height: 8),
          DropdownButtonFormField<String>(
            initialValue: ClothingCatalog.patterns.contains(_item.pattern)
                ? _item.pattern
                : 'solid',
            decoration: const InputDecoration(labelText: 'Pattern'),
            items: [
              for (final p in ClothingCatalog.patterns)
                DropdownMenuItem(
                  value: p,
                  child: Text(ClothingCatalog.patternLabel(p)),
                ),
            ],
            onChanged: (v) => setState(
              () => _item = _item.copyWith(
                pattern: v,
                patternSource: 'user',
                patternConfidence: 1.0,
              ),
            ),
          ),
          const SizedBox(height: 16),
          OutlinedButton.icon(
            onPressed: _item.imageUrl.isEmpty
                ? null
                : () {
                    Navigator.push(
                      context,
                      MaterialPageRoute(
                        builder: (_) => TryOnScreen(
                          clothingUrl: _item.imageUrl,
                          clothingName: _item.subcategory,
                        ),
                      ),
                    );
                  },
            icon: const Icon(Icons.accessibility_new_outlined),
            label: const Text('Try this on'),
          ),
          const SizedBox(height: 8),
          FilledButton(
            onPressed: () async {
              await context.read<WardrobeProvider>().updateItem(_item);
              if (context.mounted) Navigator.pop(context);
            },
            child: const Text('Save changes'),
          ),
          const SizedBox(height: 8),
          OutlinedButton.icon(
            onPressed: () => _deletePiece(context),
            icon: const Icon(Icons.delete_outline),
            label: const Text('Delete this piece'),
            style: OutlinedButton.styleFrom(foregroundColor: AppColors.danger),
          ),
        ],
      ),
    );
  }

  Future<void> _deletePiece(BuildContext context) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Delete this piece?'),
        content: Text(
          'Remove ${_item.subcategory} from Adorable? This cannot be undone.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Keep'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Delete'),
          ),
        ],
      ),
    );
    if (ok == true && context.mounted) {
      await context.read<WardrobeProvider>().deleteItem(_item);
      if (context.mounted) Navigator.pop(context);
    }
  }
}

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../models/wardrobe_item.dart';
import '../../providers/wardrobe_provider.dart';
import '../../theme/app_theme.dart';
import '../../utils/enums.dart';
import '../../widgets/common.dart';
import '../../widgets/motion.dart';
import 'add_clothing_screen.dart';
import 'clothing_detail_screen.dart';

/// Adorable — photos of clothes currently in the user's cupboard.
class AdorableScreen extends StatelessWidget {
  const AdorableScreen({super.key});

  @override
  Widget build(BuildContext context) => const WardrobeScreen();
}

class WardrobeScreen extends StatelessWidget {
  const WardrobeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final wardrobe = context.watch<WardrobeProvider>();
    final items = [...wardrobe.visible]
      ..sort((a, b) {
        final at = a.createdAt ?? DateTime.fromMillisecondsSinceEpoch(0);
        final bt = b.createdAt ?? DateTime.fromMillisecondsSinceEpoch(0);
        return bt.compareTo(at);
      });
    return Scaffold(
      appBar: AppBar(
        title: const Text('Adorable'),
      ),
      body: SoftBackdrop(
        child: Column(
          children: [
            SizedBox(
              height: 48,
              child: ListView(
                scrollDirection: Axis.horizontal,
                padding: const EdgeInsets.symmetric(horizontal: 16),
                children: [
                  Padding(
                    padding: const EdgeInsets.only(right: 8),
                    child: ChoiceChip(
                      label: const Text('All'),
                      selected: wardrobe.filter == null,
                      onSelected: (_) => wardrobe.setFilter(null),
                    ),
                  ),
                  for (final c in ClothingCategory.values)
                    Padding(
                      padding: const EdgeInsets.only(right: 8),
                      child: ChoiceChip(
                        label: Text(c.label),
                        selected: wardrobe.filter == c,
                        onSelected: (_) => wardrobe.setFilter(c),
                      ),
                    ),
                ],
              ),
            ),
            Expanded(
              child: items.isEmpty
                  ? Padding(
                      padding: EdgeInsets.only(bottom: bottomNavClearance(context)),
                      child: EmptyView(
                        title: wardrobe.filter == null
                            ? 'Your cupboard is empty'
                            : 'No ${wardrobe.filter!.label.toLowerCase()} yet',
                        message: wardrobe.filter == null
                            ? 'Adorable keeps photos of clothes you already have. '
                                'Add a photo from your cupboard so outfits can use real items.'
                            : 'Add a photo of your ${wardrobe.filter!.label.toLowerCase()} so outfits can use real items.',
                        actionLabel: 'Add a clothing photo',
                        onAction: () => Navigator.push(
                          context,
                          MaterialPageRoute(builder: (_) => const AddClothingScreen()),
                        ),
                      ),
                    )
                  : CustomScrollView(
                      slivers: [
                        SliverToBoxAdapter(
                          child: Padding(
                            padding: const EdgeInsets.fromLTRB(16, 8, 16, 12),
                            child: Text(
                              '${items.length} ${wardrobe.filter == null ? "piece" : wardrobe.filter!.label.toLowerCase()}${items.length == 1 ? "" : "s"} in your cupboard. '
                              'Newest photos first.',
                              style: const TextStyle(color: AppColors.muted),
                            ),
                          ),
                        ),
                        SliverPadding(
                          padding: const EdgeInsets.fromLTRB(16, 0, 16, 12),
                          sliver: SliverLayoutBuilder(
                            builder: (context, constraints) {
                              final w = constraints.crossAxisExtent;
                              final cols = w >= 900 ? 4 : w >= 600 ? 3 : 2;
                              return SliverGrid(
                                gridDelegate:
                                    SliverGridDelegateWithFixedCrossAxisCount(
                                  crossAxisCount: cols,
                                  crossAxisSpacing: 12,
                                  mainAxisSpacing: 12,
                                  childAspectRatio: 0.62,
                                ),
                                delegate: SliverChildBuilderDelegate(
                                  (_, i) {
                                    final item = items[i];
                                    return FadeSlideIn(
                                      delay: Duration(milliseconds: 40 * (i % 8)),
                                      child: PhotoTile(
                                        imageUrl: item.imageUrl,
                                        title: item.subcategory,
                                        subtitle:
                                            '${item.color} · ${item.category.label}',
                                        onTap: () => Navigator.push(
                                          context,
                                          MaterialPageRoute(
                                            builder: (_) =>
                                                ClothingDetailScreen(item: item),
                                          ),
                                        ),
                                        onDelete: () =>
                                            _confirmDelete(context, item),
                                      ),
                                    );
                                  },
                                  childCount: items.length,
                                ),
                              );
                            },
                          ),
                        ),
                        SliverToBoxAdapter(
                          child: Padding(
                            padding: EdgeInsets.fromLTRB(
                              16,
                              8,
                              16,
                              bottomNavClearance(context),
                            ),
                            child: FilledButton.icon(
                              onPressed: () => Navigator.push(
                                context,
                                MaterialPageRoute(
                                  builder: (_) => const AddClothingScreen(),
                                ),
                              ),
                              icon: const Icon(Icons.add_a_photo_outlined),
                              label: const Text('Add cupboard photo'),
                            ),
                          ),
                        ),
                      ],
                    ),
            ),
          ],
        ),
      ),
    );
  }
}

Future<void> _confirmDelete(BuildContext context, WardrobeItem item) async {
  final ok = await showDialog<bool>(
    context: context,
    builder: (ctx) => AlertDialog(
      title: const Text('Delete this piece?'),
      content: Text(
        'Remove ${item.subcategory} from Adorable? This cannot be undone.',
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(ctx, false),
          child: const Text('Keep'),
        ),
        FilledButton(
          onPressed: () => Navigator.pop(ctx, true),
          style: FilledButton.styleFrom(backgroundColor: AppColors.danger),
          child: const Text('Delete'),
        ),
      ],
    ),
  );
  if (ok == true && context.mounted) {
    await context.read<WardrobeProvider>().deleteItem(item);
  }
}

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../providers/shop_provider.dart';
import '../../utils/enums.dart';
import '../../widgets/common.dart';
import '../../widgets/motion.dart';
import 'cart_screen.dart';
import 'product_detail_screen.dart';

class ShopScreen extends StatelessWidget {
  const ShopScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final shop = context.watch<ShopProvider>();
    return Scaffold(
      appBar: AppBar(
        title: const Text('Shop'),
        actions: [
          IconButton(
            onPressed: () => Navigator.push(
              context,
              MaterialPageRoute(builder: (_) => const CartScreen()),
            ),
            icon: Badge(
              isLabelVisible: shop.cart.isNotEmpty,
              label: Text('${shop.cart.length}'),
              child: const Icon(Icons.shopping_bag_outlined),
            ),
          ),
        ],
      ),
      body: SoftBackdrop(
        child: Column(
        children: [
          Padding(
            padding: const EdgeInsets.all(16),
            child: TextField(
              decoration: const InputDecoration(
                prefixIcon: Icon(Icons.search),
                labelText: 'Search clothing',
              ),
              onChanged: (q) => shop.applyFilters(query: q),
            ),
          ),
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
                    selected: shop.category == null,
                    onSelected: (_) => shop.applyFilters(clearCategory: true),
                  ),
                ),
                for (final c in ClothingCategory.values)
                  Padding(
                    padding: const EdgeInsets.only(right: 8),
                    child: ChoiceChip(
                      label: Text(c.label),
                      selected: shop.category == c,
                      onSelected: (_) => shop.applyFilters(category: c),
                    ),
                  ),
              ],
            ),
          ),
          Expanded(
            child: shop.loading
                ? const LoadingView(message: 'Loading catalog…', skeleton: true)
                : shop.error != null
                    ? ErrorView(message: shop.error!, onRetry: () => shop.loadCatalog(null))
                    : shop.products.isEmpty
                        ? const EmptyView(
                            title: 'No products',
                            message: 'Try another search or category.',
                            icon: Icons.storefront_outlined,
                          )
                        : LayoutBuilder(
                            builder: (context, constraints) {
                              final w = constraints.maxWidth;
                              final cols = w >= 900 ? 4 : w >= 600 ? 3 : 2;
                              return GridView.builder(
                            padding: const EdgeInsets.fromLTRB(16, 16, 16, 88),
                            gridDelegate:
                                SliverGridDelegateWithFixedCrossAxisCount(
                              crossAxisCount: cols,
                              childAspectRatio: 0.56,
                              crossAxisSpacing: 12,
                              mainAxisSpacing: 12,
                            ),
                            itemCount: shop.products.length,
                            itemBuilder: (_, i) {
                              final p = shop.products[i];
                              return FadeSlideIn(
                                delay: Duration(milliseconds: 40 * (i % 6)),
                                child: PhotoTile(
                                  imageUrl: p.imageUrl,
                                  title: p.name,
                                  subtitle: p.priceLabel,
                                  onTap: () => Navigator.push(
                                    context,
                                    MaterialPageRoute(
                                      builder: (_) =>
                                          ProductDetailScreen(product: p),
                                    ),
                                  ),
                                ),
                              );
                            },
                          );
                            },
                          ),
          ),
        ],
      ),
      ),
    );
  }
}

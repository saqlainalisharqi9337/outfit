import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../models/product_model.dart';
import '../../providers/auth_provider.dart';
import '../../providers/shop_provider.dart';
import '../../widgets/common.dart';
import '../tryon/try_on_screen.dart';

class ProductDetailScreen extends StatelessWidget {
  const ProductDetailScreen({super.key, required this.product});

  final ProductModel product;

  @override
  Widget build(BuildContext context) {
    final uid = context.watch<AuthProvider>().profile?.id;
    return Scaffold(
      appBar: AppBar(title: Text(product.name)),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          NetworkImageView(
            url: product.imageUrl,
            height: (MediaQuery.sizeOf(context).height * 0.46)
                .clamp(320.0, 520.0)
                .toDouble(),
            width: double.infinity,
            fit: BoxFit.contain,
            openOnTap: true,
          ),
          const SizedBox(height: 16),
          Text(product.priceLabel, style: Theme.of(context).textTheme.headlineSmall),
          Text('${product.subcategory} · ${product.color} · ${product.style}'),
          const SizedBox(height: 12),
          Text(product.description),
          const SizedBox(height: 16),
          OutlinedButton.icon(
            onPressed: () {
              Navigator.push(
                context,
                MaterialPageRoute(
                  builder: (_) => TryOnScreen(
                    clothingUrl: product.imageUrl,
                    clothingName: product.name,
                  ),
                ),
              );
            },
            icon: const Icon(Icons.accessibility_new_outlined),
            label: const Text('Try this on'),
          ),
          const SizedBox(height: 8),
          FilledButton(
            onPressed: uid == null
                ? null
                : () async {
                    await context.read<ShopProvider>().addToCart(uid, product);
                    if (context.mounted) {
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(content: Text('Added to cart')),
                      );
                    }
                  },
            child: const Text('Add to cart'),
          ),
        ],
      ),
    );
  }
}

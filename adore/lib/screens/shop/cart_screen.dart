import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../providers/auth_provider.dart';
import '../../providers/shop_provider.dart';
import '../../theme/app_theme.dart';
import '../../widgets/common.dart';
import '../../widgets/motion.dart';
import 'checkout_screen.dart';

class CartScreen extends StatelessWidget {
  const CartScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final shop = context.watch<ShopProvider>();
    final uid = context.watch<AuthProvider>().profile?.id;
    return Scaffold(
      appBar: AppBar(title: const Text('Cart')),
      body: SoftBackdrop(
        child: shop.cart.isEmpty
          ? const EmptyView(
              title: 'Cart is empty',
              message: 'Add recommended missing items or browse the shop.',
              icon: Icons.shopping_bag_outlined,
            )
          : ListView(
              padding: const EdgeInsets.all(16),
              children: [
                ...shop.cart.map(
                  (item) => ListTile(
                    leading: NetworkImageView(
                      url: item.product.imageUrl,
                      height: 56,
                      width: 56,
                      fit: BoxFit.contain,
                      openOnTap: true,
                    ),
                    title: Text(item.product.name),
                    subtitle: Text(item.product.priceLabel),
                    trailing: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        IconButton(
                          onPressed: uid == null
                              ? null
                              : () => shop.setQuantity(
                                    uid,
                                    item.product.id,
                                    item.quantity - 1,
                                  ),
                          icon: const Icon(Icons.remove),
                        ),
                        Text('${item.quantity}'),
                        IconButton(
                          onPressed: uid == null
                              ? null
                              : () => shop.setQuantity(
                                    uid,
                                    item.product.id,
                                    item.quantity + 1,
                                  ),
                          icon: const Icon(Icons.add),
                        ),
                      ],
                    ),
                  ),
                ),
                const Divider(),
                Text(
                  'Total  PKR ${shop.cartTotal.toStringAsFixed(0)}',
                  style: Theme.of(context).textTheme.titleMedium,
                ),
                const SizedBox(height: 8),
                const Text(
                  'Checkout is a simulated FYP order. No real payment is taken.',
                  style: TextStyle(color: AppColors.muted),
                ),
                const SizedBox(height: 12),
                FilledButton(
                  onPressed: () => Navigator.push(
                    context,
                    MaterialPageRoute(builder: (_) => const CheckoutScreen()),
                  ),
                  child: const Text('Checkout'),
                ),
              ],
            ),
      ),
    );
  }
}

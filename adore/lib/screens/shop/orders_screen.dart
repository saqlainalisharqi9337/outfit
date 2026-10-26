import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';

import '../../providers/auth_provider.dart';
import '../../providers/shop_provider.dart';
import '../../theme/app_theme.dart';
import '../../widgets/common.dart';

class OrdersScreen extends StatefulWidget {
  const OrdersScreen({super.key});

  @override
  State<OrdersScreen> createState() => _OrdersScreenState();
}

class _OrdersScreenState extends State<OrdersScreen> {
  @override
  void initState() {
    super.initState();
    final uid = context.read<AuthProvider>().profile?.id;
    if (uid != null) {
      context.read<ShopProvider>().loadOrders(uid);
    }
  }

  @override
  Widget build(BuildContext context) {
    final shop = context.watch<ShopProvider>();
    return Scaffold(
      appBar: AppBar(title: const Text('Demo orders')),
      body: shop.orders.isEmpty
          ? const EmptyView(
              title: 'No orders yet',
              message: 'Checkout is simulated for the FYP. Place a demo order from the cart.',
              icon: Icons.receipt_long_outlined,
            )
          : ListView.separated(
              padding: const EdgeInsets.all(16),
              itemCount: shop.orders.length,
              separatorBuilder: (_, _) => const SizedBox(height: 8),
              itemBuilder: (_, i) {
                final order = shop.orders[i];
                return ListTile(
                  tileColor: AppColors.surface,
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(16),
                  ),
                  title: Text('PKR ${order.total.toStringAsFixed(0)}'),
                  subtitle: Text(
                    '${order.status.name} · ${DateFormat.yMMMd().format(order.createdAt)}\n'
                    '${order.note ?? 'Simulated checkout'}',
                  ),
                  isThreeLine: true,
                );
              },
            ),
    );
  }
}

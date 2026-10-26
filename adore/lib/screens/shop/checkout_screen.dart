import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../providers/auth_provider.dart';
import '../../providers/shop_provider.dart';
import '../../theme/app_theme.dart';
import '../../utils/exceptions.dart';

class CheckoutScreen extends StatefulWidget {
  const CheckoutScreen({super.key});

  @override
  State<CheckoutScreen> createState() => _CheckoutScreenState();
}

class _CheckoutScreenState extends State<CheckoutScreen> {
  bool _busy = false;
  String? _error;

  @override
  Widget build(BuildContext context) {
    final shop = context.watch<ShopProvider>();
    return Scaffold(
      appBar: AppBar(title: const Text('Checkout')),
      body: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'This is a simulated checkout for the Final Year Project. '
              'Placing an order stores it in Supabase and clears your cart. '
              'No payment gateway is charged.',
            ),
            const SizedBox(height: 16),
            Text('Items: ${shop.cart.length}'),
            Text('Total: PKR ${shop.cartTotal.toStringAsFixed(0)}'),
            const Spacer(),
            if (_error != null)
              Text(_error!, style: const TextStyle(color: AppColors.danger)),
            FilledButton(
              onPressed: _busy
                  ? null
                  : () async {
                      final uid = context.read<AuthProvider>().profile?.id;
                      if (uid == null) return;
                      setState(() {
                        _busy = true;
                        _error = null;
                      });
                      try {
                        final order = await shop.checkout(uid);
                        if (!context.mounted) return;
                        Navigator.pushReplacement(
                          context,
                          MaterialPageRoute(
                            builder: (_) => OrderConfirmationScreen(
                              orderId: order.id,
                              total: order.total,
                            ),
                          ),
                        );
                      } on AppException catch (e) {
                        setState(() => _error = e.message);
                      } finally {
                        if (mounted) setState(() => _busy = false);
                      }
                    },
              child: const Text('Place demo order'),
            ),
          ],
        ),
      ),
    );
  }
}

class OrderConfirmationScreen extends StatelessWidget {
  const OrderConfirmationScreen({
    super.key,
    required this.orderId,
    required this.total,
  });

  final String orderId;
  final double total;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Order placed')),
      body: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          children: [
            const Icon(Icons.check_circle, color: AppColors.success, size: 64),
            const SizedBox(height: 16),
            const Text('Demo order recorded.'),
            Text('Order ID: $orderId'),
            Text('Total: PKR ${total.toStringAsFixed(0)}'),
            const SizedBox(height: 12),
            const Text(
              'This is not a real purchase. Use it to demonstrate the shopping flow in your FYP presentation.',
              textAlign: TextAlign.center,
            ),
            const Spacer(),
            FilledButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('Back to shop'),
            ),
          ],
        ),
      ),
    );
  }
}

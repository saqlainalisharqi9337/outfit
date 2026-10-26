import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../providers/auth_provider.dart';
import '../../providers/shop_provider.dart';
import '../../widgets/common.dart';

class TrendsScreen extends StatelessWidget {
  const TrendsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final shop = context.watch<ShopProvider>();
    final user = context.watch<AuthProvider>().profile;
    return Scaffold(
      appBar: AppBar(title: const Text('Fashion trends')),
      body: shop.trends.isEmpty
          ? EmptyView(
              title: 'No matching trends',
              message:
                  'Trends are filtered against your culture and explicit clothing restrictions.',
              actionLabel: 'Reload',
              onAction: () => shop.loadCatalog(user),
            )
          : ListView.builder(
              padding: const EdgeInsets.all(16),
              itemCount: shop.trends.length,
              itemBuilder: (_, i) {
                final t = shop.trends[i];
                return Card(
                  margin: const EdgeInsets.only(bottom: 12),
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        NetworkImageView(
                          url: t.imageUrl,
                          height: 240,
                          width: double.infinity,
                          fit: BoxFit.contain,
                          openOnTap: true,
                        ),
                        const SizedBox(height: 8),
                        Text(t.title, style: Theme.of(context).textTheme.titleMedium),
                        Text(t.subtitle),
                        const SizedBox(height: 8),
                        Text(t.description),
                        if (t.stylingIdea != null) ...[
                          const SizedBox(height: 8),
                          Text('Styling idea: ${t.stylingIdea}'),
                        ],
                        const SizedBox(height: 8),
                        Wrap(
                          spacing: 6,
                          children: [
                            for (final c in t.colors) Chip(label: Text(c)),
                            for (final item in t.itemTypes)
                              Chip(label: Text(item)),
                          ],
                        ),
                      ],
                    ),
                  ),
                );
              },
            ),
    );
  }
}

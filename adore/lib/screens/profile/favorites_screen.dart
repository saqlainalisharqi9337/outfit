import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../providers/auth_provider.dart';
import '../../services/feedback_service.dart';
import '../../theme/app_theme.dart';
import '../../widgets/common.dart';

class FavoritesScreen extends StatefulWidget {
  const FavoritesScreen({super.key});

  @override
  State<FavoritesScreen> createState() => _FavoritesScreenState();
}

class _FavoritesScreenState extends State<FavoritesScreen> {
  late Future<List<Map<String, dynamic>>> _future;

  @override
  void initState() {
    super.initState();
    final uid = context.read<AuthProvider>().profile?.id;
    _future = uid == null
        ? Future.value(const [])
        : FeedbackService().listFavorites(uid);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Saved outfits')),
      body: FutureBuilder(
        future: _future,
        builder: (context, snapshot) {
          if (snapshot.connectionState != ConnectionState.done) {
            return const LoadingView(message: 'Loading saved looks…');
          }
          final rows = snapshot.data ?? const [];
          if (rows.isEmpty) {
            return const EmptyView(
              title: 'No saved outfits',
              message: 'Like an outfit and tap Save on the Outfit screen.',
              icon: Icons.favorite_outline,
            );
          }
          return ListView.separated(
            padding: const EdgeInsets.all(16),
            itemCount: rows.length,
            separatorBuilder: (_, _) => const SizedBox(height: 8),
            itemBuilder: (_, i) {
              final row = rows[i];
              final score = (row['score'] as num?)?.toDouble();
              return ListTile(
                tileColor: AppColors.surface,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(16),
                ),
                title: Text(row['title'] as String? ?? 'Saved look'),
                subtitle: Text(
                  score == null
                      ? 'Saved outfit'
                      : 'Score ${(score * 100).round()}%',
                ),
              );
            },
          );
        },
      ),
    );
  }
}

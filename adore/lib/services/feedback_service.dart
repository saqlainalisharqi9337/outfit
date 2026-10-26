import 'package:supabase_flutter/supabase_flutter.dart';
import 'package:uuid/uuid.dart';

import '../models/outfit_model.dart';
import '../models/product_model.dart';
import '../utils/enums.dart';
import 'demo_store.dart';

class FeedbackService {
  FeedbackService({SupabaseClient? client})
      : _client = client ?? Supabase.instance.client;

  final SupabaseClient _client;
  final _uuid = const Uuid();

  Future<void> record({
    required String uid,
    required OutfitRecommendation outfit,
    required FeedbackType type,
  }) async {
    final feedback = OutfitFeedback(
      id: _uuid.v4(),
      outfitId: outfit.id,
      type: type,
      colors: outfit.ownedItems.map((e) => e.color).toList(),
      subcategories: outfit.ownedItems.map((e) => e.subcategory).toList(),
      createdAt: DateTime.now(),
    );
    if (DemoStore.instance.active) {
      DemoStore.instance.feedback.insert(0, feedback);
      if (type == FeedbackType.save) {
        DemoStore.instance.favorites.insert(0, {
          'id': outfit.id,
          'user_id': uid,
          'title': outfit.title,
          'score': outfit.breakdown.finalScore,
          'item_ids': outfit.ownedItems.map((e) => e.itemId).toList(),
        });
      }
      return;
    }
    await _client.from('outfit_feedback').insert(feedback.toRow(uid));
    if (type == FeedbackType.save) {
      await _client.from('favorites').upsert({
        'id': outfit.id,
        'user_id': uid,
        'title': outfit.title,
        'score': outfit.breakdown.finalScore,
        'item_ids': outfit.ownedItems.map((e) => e.itemId).toList(),
      });
    }
  }

  Future<List<OutfitFeedback>> list(String uid) async {
    if (DemoStore.instance.active) {
      return List.of(DemoStore.instance.feedback);
    }
    final rows = await _client
        .from('outfit_feedback')
        .select()
        .eq('user_id', uid)
        .order('created_at', ascending: false)
        .limit(80);
    return rows
        .map(
          (row) => OutfitFeedback.fromMap(
            row['id'] as String,
            Map<String, dynamic>.from(row),
          ),
        )
        .toList();
  }

  Future<List<Map<String, dynamic>>> listFavorites(String uid) async {
    if (DemoStore.instance.active) {
      return List.of(DemoStore.instance.favorites);
    }
    final rows = await _client
        .from('favorites')
        .select()
        .eq('user_id', uid)
        .order('created_at', ascending: false);
    return rows.map((row) => Map<String, dynamic>.from(row)).toList();
  }
}

import 'package:supabase_flutter/supabase_flutter.dart';

import '../models/wardrobe_item.dart';
import '../utils/exceptions.dart';
import 'demo_store.dart';

class WardrobeService {
  WardrobeService({SupabaseClient? client})
      : _client = client ?? Supabase.instance.client;

  final SupabaseClient _client;

  Stream<List<WardrobeItem>> watch(String uid) {
    if (DemoStore.instance.active) {
      return DemoStore.instance.watchWardrobe();
    }
    return _client
        .from('wardrobe_items')
        .stream(primaryKey: ['id'])
        .eq('user_id', uid)
        .order('created_at', ascending: false)
        .map(
          (rows) => rows
              .map(
                (row) => WardrobeItem.fromMap(
                  row['id'] as String,
                  uid,
                  Map<String, dynamic>.from(row),
                ),
              )
              .toList(),
        );
  }

  Future<List<WardrobeItem>> list(String uid) async {
    if (DemoStore.instance.active) {
      return List.of(DemoStore.instance.wardrobe);
    }
    try {
      final rows = await _client
          .from('wardrobe_items')
          .select()
          .eq('user_id', uid)
          .order('created_at', ascending: false);
      return rows
          .map(
            (row) => WardrobeItem.fromMap(
              row['id'] as String,
              uid,
              Map<String, dynamic>.from(row),
            ),
          )
          .toList();
    } catch (e) {
      throw DatabaseException(_mapError('Could not load your wardrobe.', e));
    }
  }

  Future<void> upsert(WardrobeItem item) async {
    if (DemoStore.instance.active) {
      final items = DemoStore.instance.wardrobe;
      final index = items.indexWhere((e) => e.itemId == item.itemId);
      if (index >= 0) {
        items[index] = item;
      } else {
        items.insert(0, item);
      }
      DemoStore.instance.emitWardrobe();
      return;
    }
    try {
      // Saves pattern, pattern_source, pattern_confidence, colors, category…
      await _client.from('wardrobe_items').upsert(item.toRow());
    } catch (e) {
      throw DatabaseException(_mapError('Could not save this clothing item.', e));
    }
  }

  Future<void> delete(String uid, String itemId) async {
    if (DemoStore.instance.active) {
      DemoStore.instance.wardrobe.removeWhere((e) => e.itemId == itemId);
      DemoStore.instance.emitWardrobe();
      return;
    }
    try {
      await _client
          .from('wardrobe_items')
          .delete()
          .eq('id', itemId)
          .eq('user_id', uid);
    } catch (e) {
      throw DatabaseException(_mapError('Could not delete this clothing item.', e));
    }
  }

  String _mapError(String fallback, Object error) {
    final text = error.toString();
    if (text.contains('pattern_source') ||
        text.contains('pattern_confidence')) {
      return 'Database is missing pattern columns. In Supabase SQL Editor run '
          'supabase/SETUP_ALL.sql, then save the clothing item again.';
    }
    if (text.contains('PGRST205') || text.contains('schema cache')) {
      return 'Database tables are not set up yet. Run supabase/SETUP_ALL.sql '
          'in the Supabase SQL Editor, then try again.';
    }
    if (text.contains('row-level security') || text.contains('42501')) {
      return 'Could not save wardrobe item (security policy). Make sure you are '
          'logged in with a real Supabase account, not Local Demo.';
    }
    return '$fallback $text';
  }
}

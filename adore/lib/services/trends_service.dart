import 'dart:convert';

import 'package:flutter/services.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import '../models/product_model.dart';
import '../models/user_model.dart';
import 'demo_store.dart';
import 'shopping_service.dart';

class TrendsService {
  TrendsService({SupabaseClient? client})
      : _client = client ?? Supabase.instance.client;

  final SupabaseClient _client;
  List<TrendModel>? _bundled;

  Future<List<TrendModel>> loadTrends() async {
    final bundled = await _loadBundled();
    if (DemoStore.instance.active) {
      return bundled;
    }
    try {
      final rows = await _client.from('trends').select();
      if (rows.isNotEmpty) {
        final bundledMap = {for (final b in bundled) b.id: b};
        return rows.map((row) {
          final id = row['id'] as String;
          final map = Map<String, dynamic>.from(row);
          final rawUrl = (map['image_url'] ?? map['imageUrl']) as String?;
          final cleanUrl = ShoppingService.sanitizeUrl(id, rawUrl, bundledMap[id]?.imageUrl);
          if (cleanUrl != rawUrl && cleanUrl.isNotEmpty) {
            map['image_url'] = cleanUrl;
            map['imageUrl'] = cleanUrl;
            _client
                .from('trends')
                .update({'image_url': cleanUrl})
                .eq('id', id)
                .catchError((_) {});
          }
          return TrendModel.fromMap(id, map);
        }).toList();
      }
    } catch (_) {}
    return bundled;
  }

  Future<List<TrendModel>> _loadBundled() async {
    if (_bundled != null) return _bundled!;
    final raw = await rootBundle.loadString('assets/data/trends.json');
    final list = jsonDecode(raw) as List<dynamic>;
    _bundled = list
        .map((e) => TrendModel.fromMap(
              (e as Map<String, dynamic>)['id'] as String,
              e,
            ))
        .toList();
    return _bundled!;
  }

  List<TrendModel> forUser(List<TrendModel> all, UserModel user) {
    final excluded = user.preferences.excludedItemTypes
        .map((e) => e.toLowerCase())
        .toSet();
    final culture = user.culture?.name;
    return all.where((trend) {
      final conflicts = trend.itemTypes.any(
        (t) => excluded.contains(t.toLowerCase()),
      );
      if (conflicts) return false;
      if (user.preferences.modestPreference) {
        const immodest = {'shorts', 'mini skirt', 'crop top'};
        if (trend.itemTypes.any((t) => immodest.contains(t.toLowerCase()))) {
          return false;
        }
      }
      if (culture == null || trend.cultureTags.contains('all')) return true;
      return trend.cultureTags.contains(culture) ||
          trend.cultureTags.contains('all');
    }).toList();
  }
}

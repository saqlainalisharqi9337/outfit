import 'package:supabase_flutter/supabase_flutter.dart';

import '../models/user_model.dart';
import '../utils/exceptions.dart';
import '../utils/transient_retry.dart';
import 'demo_store.dart';

class UserService {
  UserService({SupabaseClient? client})
      : _client = client ?? Supabase.instance.client;

  final SupabaseClient _client;

  Future<void> createUser(UserModel user) async {
    if (DemoStore.instance.active) {
      DemoStore.instance.profile = user;
      return;
    }
    try {
      await retryTransient(
        () => _client.from('profiles').upsert(user.toRow(), onConflict: 'id'),
      );
    } catch (e) {
      throw DatabaseException(_mapError('Could not create your profile.', e));
    }
  }

  Future<UserModel?> getUser(String uid) async {
    if (DemoStore.instance.active) {
      return DemoStore.instance.profile.id == uid
          ? DemoStore.instance.profile
          : null;
    }
    try {
      final row = await retryTransient(
        () => _client.from('profiles').select().eq('id', uid).maybeSingle(),
      );
      if (row == null) return null;
      return UserModel.fromMap(uid, Map<String, dynamic>.from(row));
    } catch (e) {
      throw DatabaseException(_mapError('Could not load your profile.', e));
    }
  }

  Stream<UserModel?> watchUser(String uid) {
    if (DemoStore.instance.active) {
      return Stream.value(DemoStore.instance.profile);
    }
    return _client
        .from('profiles')
        .stream(primaryKey: ['id'])
        .eq('id', uid)
        .map((rows) {
          if (rows.isEmpty) return null;
          return UserModel.fromMap(uid, Map<String, dynamic>.from(rows.first));
        });
  }

  Future<void> updateUser(UserModel user) async {
    if (DemoStore.instance.active) {
      DemoStore.instance.profile = user;
      return;
    }
    try {
      // Upsert writes body_type, skin_tone, culture, preferences, etc.
      await _client.from('profiles').upsert(user.toRow(), onConflict: 'id');
    } catch (e) {
      throw DatabaseException(_mapError('Could not save profile changes.', e));
    }
  }

  String _mapError(String fallback, Object error) {
    final text = error.toString();
    if (text.contains('body_type') ||
        (text.contains('PGRST204') && text.contains('body'))) {
      return 'Database is missing body_type. In Supabase SQL Editor run '
          'supabase/SETUP_ALL.sql (or the body_type migration), then try again.';
    }
    if (text.contains('PGRST205') || text.contains('schema cache')) {
      return 'Database tables are not set up yet. In the Supabase SQL Editor '
          'run supabase/SETUP_ALL.sql, wait a few seconds, then log in again.';
    }
    if (text.contains('row-level security') || text.contains('42501')) {
      return 'Could not save your profile (security policy). In Supabase Auth '
          'settings turn off Confirm email for FYP demos, then register/login again.';
    }
    return '$fallback $text';
  }
}

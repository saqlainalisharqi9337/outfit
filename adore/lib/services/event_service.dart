import 'package:supabase_flutter/supabase_flutter.dart';
import 'package:uuid/uuid.dart';

import '../models/product_model.dart';
import '../utils/exceptions.dart';
import 'demo_store.dart';

class EventService {
  EventService({SupabaseClient? client})
      : _client = client ?? Supabase.instance.client;

  final SupabaseClient _client;
  final _uuid = const Uuid();

  Stream<List<EventModel>> watch(String uid) {
    if (DemoStore.instance.active) {
      return DemoStore.instance.watchEvents();
    }
    return _client
        .from('events')
        .stream(primaryKey: ['id'])
        .eq('user_id', uid)
        .order('date_time')
        .map(
          (rows) => rows
              .map(
                (row) => EventModel.fromMap(
                  row['id'] as String,
                  Map<String, dynamic>.from(row),
                ),
              )
              .toList(),
        );
  }

  Future<void> upsert(String uid, EventModel event) async {
    if (DemoStore.instance.active) {
      final id = event.id.isEmpty ? _uuid.v4() : event.id;
      final saved = EventModel(
        id: id,
        name: event.name,
        dateTime: event.dateTime,
        occasion: event.occasion,
        location: event.location,
        notes: event.notes,
      );
      final items = DemoStore.instance.events;
      final index = items.indexWhere((e) => e.id == id);
      if (index >= 0) {
        items[index] = saved;
      } else {
        items.add(saved);
      }
      DemoStore.instance.emitEvents();
      return;
    }
    try {
      final id = event.id.isEmpty ? _uuid.v4() : event.id;
      await _client.from('events').upsert(
            EventModel(
              id: id,
              name: event.name,
              dateTime: event.dateTime,
              occasion: event.occasion,
              location: event.location,
              notes: event.notes,
            ).toRow(uid),
          );
    } catch (_) {
      throw DatabaseException('Could not save this event.');
    }
  }

  Future<void> delete(String uid, String eventId) async {
    if (DemoStore.instance.active) {
      DemoStore.instance.events.removeWhere((e) => e.id == eventId);
      DemoStore.instance.emitEvents();
      return;
    }
    await _client.from('events').delete().eq('id', eventId).eq('user_id', uid);
  }
}

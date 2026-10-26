import 'package:flutter/foundation.dart';

import '../models/product_model.dart';
import '../services/event_service.dart';

class EventProvider extends ChangeNotifier {
  EventProvider({required EventService eventService}) : _events = eventService;

  final EventService _events;
  List<EventModel> items = [];
  DateTime focusedDay = DateTime.now();
  DateTime selectedDay = DateTime.now();

  void bind(String uid) {
    _events.watch(uid).listen((value) {
      items = value;
      notifyListeners();
    });
  }

  List<EventModel> eventsOn(DateTime day) {
    return items.where((e) {
      return e.dateTime.year == day.year &&
          e.dateTime.month == day.month &&
          e.dateTime.day == day.day;
    }).toList();
  }

  void selectDay(DateTime selected, DateTime focused) {
    selectedDay = selected;
    focusedDay = focused;
    notifyListeners();
  }

  Future<void> save(String uid, EventModel event) =>
      _events.upsert(uid, event);

  Future<void> remove(String uid, String id) => _events.delete(uid, id);
}

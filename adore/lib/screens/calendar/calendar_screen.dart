import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';
import 'package:table_calendar/table_calendar.dart';
import 'package:uuid/uuid.dart';

import '../../models/product_model.dart';
import '../../providers/auth_provider.dart';
import '../../providers/event_provider.dart';
import '../../providers/recommendation_provider.dart';
import '../../providers/wardrobe_provider.dart';
import '../../providers/weather_provider.dart';
import '../../services/weather_service.dart';
import '../../theme/app_theme.dart';
import '../../utils/enums.dart';
import '../../utils/event_context.dart';
import '../outfit/outfit_screen.dart';

class CalendarScreen extends StatelessWidget {
  const CalendarScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final events = context.watch<EventProvider>();
    final selected = events.eventsOn(events.selectedDay);
    return Scaffold(
      appBar: AppBar(title: const Text('Calendar')),
      body: ListView(
        padding: EdgeInsets.only(bottom: bottomNavClearance(context)),
        children: [
          TableCalendar<EventModel>(
            firstDay: DateTime.utc(2024, 1, 1),
            lastDay: DateTime.utc(2030, 12, 31),
            focusedDay: events.focusedDay,
            selectedDayPredicate: (d) => isSameDay(d, events.selectedDay),
            eventLoader: events.eventsOn,
            onDaySelected: (selectedDay, focusedDay) {
              events.selectDay(selectedDay, focusedDay);
            },
            calendarStyle: const CalendarStyle(outsideDaysVisible: false),
          ),
          const Padding(
            padding: EdgeInsets.all(16),
            child: Text('Events'),
          ),
          if (selected.isEmpty)
            const Padding(
              padding: EdgeInsets.symmetric(horizontal: 16),
              child: Text('No events on this day.'),
            ),
          ...selected.map(
            (e) => ListTile(
              title: Text(e.name),
              subtitle: Text(
                '${DateFormat.jm().format(e.dateTime)} · ${e.occasion.label}',
              ),
              onTap: () => Navigator.push(
                context,
                MaterialPageRoute(builder: (_) => EventDetailScreen(event: e)),
              ),
            ),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
            child: FilledButton.icon(
              onPressed: () => Navigator.push(
                context,
                MaterialPageRoute(builder: (_) => const EventFormScreen()),
              ),
              icon: const Icon(Icons.add),
              label: const Text('Add event'),
            ),
          ),
        ],
      ),
    );
  }
}

class EventFormScreen extends StatefulWidget {
  const EventFormScreen({super.key, this.existing});

  final EventModel? existing;

  @override
  State<EventFormScreen> createState() => _EventFormScreenState();
}

class _EventFormScreenState extends State<EventFormScreen> {
  final _formKey = GlobalKey<FormState>();
  late final TextEditingController _name;
  late final TextEditingController _location;
  late final TextEditingController _notes;
  late DateTime _date;
  Occasion _occasion = Occasion.casualDayOut;
  String? _weatherNote;
  bool _saving = false;

  @override
  void initState() {
    super.initState();
    final e = widget.existing;
    _name = TextEditingController(text: e?.name ?? '');
    _location = TextEditingController(text: e?.location ?? '');
    _notes = TextEditingController(text: e?.notes ?? '');
    _date = e?.dateTime ?? DateTime.now().add(const Duration(days: 1));
    _occasion = e?.occasion ?? Occasion.casualDayOut;
  }

  @override
  void dispose() {
    _name.dispose();
    _location.dispose();
    _notes.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    if (!_formKey.currentState!.validate()) return;
    final uid = context.read<AuthProvider>().profile?.id;
    if (uid == null || _saving) return;
    setState(() => _saving = true);
    try {
    final city = _location.text.trim();
    final forecast = await context.read<WeatherProvider>().forecastForEvent(
          city: city,
          date: _date,
        );
    if (!mounted) return;
    setState(() {
      _weatherNote = forecast.weather == null
          ? (forecast.message ??
              'Weather information could not be retrieved for this city.')
          : 'Weather for $city on this date: '
              '${forecast.weather!.condition}, '
              '${forecast.weather!.temperature.round()}°C.';
    });
    await context.read<EventProvider>().save(
          uid,
          EventModel(
            id: widget.existing?.id ?? const Uuid().v4(),
            name: _name.text.trim(),
            dateTime: _date,
            occasion: _occasion,
            location: city,
            notes: _notes.text.trim().isEmpty ? null : _notes.text.trim(),
          ),
        );
    if (!mounted) return;
    final note = _weatherNote;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(note ?? 'Event saved.')),
    );
    Navigator.pop(context);
    } catch (_) {
      if (!mounted) return;
      setState(() => _saving = false);
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Could not save this event. Please retry.')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final bottomInset = MediaQuery.viewInsetsOf(context).bottom;
    return Scaffold(
      resizeToAvoidBottomInset: true,
      appBar: AppBar(
        title: Text(widget.existing == null ? 'New event' : 'Edit event'),
      ),
      body: SafeArea(
        child: Form(
          key: _formKey,
          child: ListView(
        padding: EdgeInsets.fromLTRB(20, 20, 20, 20 + bottomInset),
        children: [
          TextFormField(
            controller: _name,
            textInputAction: TextInputAction.next,
            decoration: const InputDecoration(labelText: 'Event name'),
            validator: (value) =>
                (value == null || value.trim().isEmpty) ? 'Enter an event name' : null,
          ),
          const SizedBox(height: 12),
          TextFormField(
            controller: _location,
            textCapitalization: TextCapitalization.words,
            textInputAction: TextInputAction.next,
            decoration: const InputDecoration(
              labelText: 'City',
              hintText: 'Islamabad',
            ),
            validator: (value) {
              if (value == null || value.trim().isEmpty) {
                return 'Enter a city so the outfit can use that location\'s weather.';
              }
              return null;
            },
          ),
          const SizedBox(height: 12),
          TextFormField(
            controller: _notes,
            textCapitalization: TextCapitalization.sentences,
            decoration: const InputDecoration(
              labelText: 'Description',
              hintText: 'Family wedding at a hotel in the evening',
              alignLabelWithHint: true,
            ),
            maxLines: 3,
          ),
          const SizedBox(height: 12),
          ListTile(
            title: Text(DateFormat.yMMMd().add_jm().format(_date)),
            trailing: const Icon(Icons.schedule),
            onTap: () async {
              final d = await showDatePicker(
                context: context,
                firstDate: DateTime.now().subtract(const Duration(days: 1)),
                lastDate: DateTime.now().add(const Duration(days: 800)),
                initialDate: _date,
              );
              if (d == null || !context.mounted) return;
              final t = await showTimePicker(
                context: context,
                initialTime: TimeOfDay.fromDateTime(_date),
              );
              setState(() {
                _date = DateTime(
                  d.year,
                  d.month,
                  d.day,
                  t?.hour ?? 10,
                  t?.minute ?? 0,
                );
              });
            },
          ),
          DropdownButtonFormField<Occasion>(
            initialValue: _occasion,
            decoration: const InputDecoration(labelText: 'Occasion'),
            items: [
              for (final o in Occasion.values)
                DropdownMenuItem(value: o, child: Text(o.label)),
            ],
            onChanged: (v) => setState(() => _occasion = v ?? _occasion),
          ),
          if (_weatherNote != null) ...[
            const SizedBox(height: 12),
            Text(_weatherNote!),
          ],
          const SizedBox(height: 16),
          FilledButton(
            onPressed: _saving ? null : _save,
            child: Text(_saving ? 'Saving…' : 'Save event'),
          ),
        ],
          ),
        ),
      ),
    );
  }
}

class EventDetailScreen extends StatelessWidget {
  const EventDetailScreen({super.key, required this.event});

  final EventModel event;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(event.name),
        actions: [
          IconButton(
            onPressed: () => Navigator.push(
              context,
              MaterialPageRoute(
                builder: (_) => EventFormScreen(existing: event),
              ),
            ),
            icon: const Icon(Icons.edit_outlined),
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          Text(DateFormat.yMMMMEEEEd().add_jm().format(event.dateTime)),
          Text(event.occasion.label),
          if (event.location != null) Text(event.location!),
          if (event.notes != null && event.notes!.isNotEmpty) ...[
            const SizedBox(height: 8),
            Text(event.notes!),
          ],
          const SizedBox(height: 16),
          FilledButton(
            onPressed: () async {
              final user = context.read<AuthProvider>().profile;
              final city = event.location?.trim() ?? '';
              if (user == null) return;
              if (city.isEmpty) {
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(
                    content: Text('Add a city to this event before recommending an outfit.'),
                  ),
                );
                return;
              }
              final forecast = await context.read<WeatherProvider>().forecastForEvent(
                    city: city,
                    date: event.dateTime,
                  );
              if (!context.mounted) return;
              final weather = forecast.weather ??
                  WeatherService.seasonalEstimate(
                    latitude: user.latitude ?? 31.5,
                    longitude: user.longitude ?? 74.3,
                    city: city,
                    country: user.country ?? '',
                    date: event.dateTime,
                  );
              final contextHint = resolveEventContext(
                selected: event.occasion,
                description: event.notes ?? '',
              );
              final timeStr = DateFormat('MMM d, yyyy · h:mm a').format(event.dateTime);
              final eventTitle = event.name.trim().isNotEmpty
                  ? event.name.trim()
                  : event.occasion.label;
              final eventSubtitle = '$timeStr · ${weather.condition}';
              await context.read<RecommendationProvider>().generate(
                    user: user,
                    wardrobe: context.read<WardrobeProvider>().items,
                    weather: weather,
                    occasionOverride: contextHint.primary,
                    nlp: contextHint.request,
                    eventTitle: eventTitle,
                    eventSubtitle: eventSubtitle,
                  );
              if (!context.mounted) return;
              Navigator.push(
                context,
                MaterialPageRoute(
                  builder: (_) => OutfitScreen(
                    eventWeather: weather,
                    eventTitle: eventTitle,
                    eventSubtitle: eventSubtitle,
                  ),
                ),
              );
            },
            child: const Text('Recommend outfit for this event'),
          ),
          TextButton(
            onPressed: () async {
              final uid = context.read<AuthProvider>().profile?.id;
              if (uid == null) return;
              await context.read<EventProvider>().remove(uid, event.id);
              if (context.mounted) Navigator.pop(context);
            },
            child: const Text('Delete event'),
          ),
        ],
      ),
    );
  }
}

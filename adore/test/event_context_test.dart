import 'package:adore/services/geocoding_service.dart';
import 'package:adore/services/nlp_request_parser.dart';
import 'package:adore/services/weather_service.dart';
import 'package:adore/utils/enums.dart';
import 'package:adore/utils/event_context.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('event description context', () {
    test('a clear wedding description sets the event type', () {
      final context = resolveEventContext(
        selected: Occasion.office,
        description:
            "Friend's wedding reception in the evening. I will attend with my family.",
      );
      expect(context.extracted, Occasion.wedding);
      expect(context.primary, Occasion.wedding);
      expect(context.request.occasion, isNull);
      expect(context.request.weatherBand, isNull);
    });

    test('office, hiking, and date descriptions are recognised', () {
      expect(
        resolveEventContext(
          selected: Occasion.casualDayOut,
          description: 'Meeting with clients at the office',
        ).primary,
        Occasion.office,
      );
      expect(
        resolveEventContext(
          selected: Occasion.casualDayOut,
          description: 'Going hiking with friends',
        ).primary,
        Occasion.outdoorActivity,
      );
      expect(
        resolveEventContext(
          selected: Occasion.casualDayOut,
          description: 'Romantic dinner with my wife',
        ).primary,
        Occasion.date,
      );
    });

    test('an empty or vague description keeps the selected type', () {
      final empty = resolveEventContext(
        selected: Occasion.party,
        description: '   ',
      );
      expect(empty.primary, Occasion.party);
      expect(empty.extracted, isNull);

      final vague = resolveEventContext(
        selected: Occasion.formalEvent,
        description: 'See you there',
      );
      expect(vague.primary, Occasion.formalEvent);
      expect(vague.extracted, isNull);
    });
  });

  group('event date forecast window', () {
    final now = DateTime(2026, 9, 27, 15);

    test('today and the next 15 days can be looked up', () {
      expect(unavailableForecastReason(now, now), isNull);
      expect(
        unavailableForecastReason(DateTime(2026, 10, 12), now),
        isNull,
      );
    });

    test('past dates and dates beyond the forecast window are refused', () {
      expect(
        unavailableForecastReason(DateTime(2026, 9, 26), now),
        contains('past date'),
      );
      expect(
        unavailableForecastReason(DateTime(2026, 10, 13), now),
        contains('not available this far ahead'),
      );
    });
  });

  group('event date and time exact temperature estimation', () {
    test('seasonal estimate adjusts temperature based on exact event hour', () {
      final afternoonEvent = DateTime(2026, 12, 15, 14); // 2:00 PM
      final nightEvent = DateTime(2026, 12, 15, 23); // 11:00 PM

      final afternoonWeather = WeatherService.seasonalEstimate(
        latitude: 31.5,
        longitude: 74.3,
        city: 'Lahore',
        country: 'PK',
        date: afternoonEvent,
      );
      final nightWeather = WeatherService.seasonalEstimate(
        latitude: 31.5,
        longitude: 74.3,
        city: 'Lahore',
        country: 'PK',
        date: nightEvent,
      );

      // Afternoon (peak sun) must be significantly warmer than late night
      expect(afternoonWeather.temperature, greaterThan(nightWeather.temperature));
      expect(afternoonWeather.fetchedAt, afternoonEvent);
      expect(nightWeather.fetchedAt, nightEvent);
    });
  });

  group('nlp target date parsing', () {
    const parser = NlpRequestParser();

    test('detects today / current day', () {
      final req1 = parser.parse('casual clothes for today');
      expect(req1.dateLabel, 'Today');
      expect(req1.targetDate, isNotNull);

      final req2 = parser.parse('what should i wear for current day');
      expect(req2.dateLabel, 'Today');
      expect(req2.targetDate, isNotNull);
    });

    test('detects tomorrow and day after tomorrow', () {
      final req1 = parser.parse('outfit for tomorrow');
      expect(req1.dateLabel, 'Tomorrow');
      expect(req1.targetDate, isNotNull);

      final req2 = parser.parse('clothes for day after tomorrow');
      expect(req2.dateLabel, 'Day after tomorrow');
      expect(req2.targetDate, isNotNull);
    });

    test('detects upcoming weekdays', () {
      final req = parser.parse('formal dress for Friday');
      expect(req.dateLabel, 'Friday');
      expect(req.targetDate, isNotNull);
      expect(req.targetDate!.weekday, DateTime.friday);
    });

    test('leaves targetDate null when no date is requested', () {
      final req = parser.parse('casual summer clothes');
      expect(req.targetDate, isNull);
      expect(req.dateLabel, isNull);
    });
  });

  group('geocoding and weather offline resilience', () {
    test('findCity resolves major cities instantly offline', () async {
      final geocoding = GeocodingService();
      final lahore = await geocoding.findCity('Lahore');
      expect(lahore, isNotNull);
      expect(lahore!.name, 'Lahore');
      expect(lahore.countryCode, 'PK');
      expect(lahore.latitude, closeTo(31.52, 0.1));

      final karachi = await geocoding.findCity('karachi');
      expect(karachi, isNotNull);
      expect(karachi!.name, 'Karachi');
    });

    test('searchCities matches known cities by country', () async {
      final geocoding = GeocodingService();
      final pkCities = await geocoding.searchCities(query: 'lah', countryCode: 'PK');
      expect(pkCities.any((c) => c.name == 'Lahore'), isTrue);
    });
  });
}

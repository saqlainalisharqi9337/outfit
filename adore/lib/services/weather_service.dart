import 'dart:convert';

import 'package:http/http.dart' as http;

import '../models/weather_model.dart';
import '../utils/clothing_catalog.dart';
import '../utils/constants.dart';
import '../utils/enums.dart';

class WeatherService {
  WeatherService({http.Client? client}) : _client = client ?? http.Client();

  final http.Client _client;
  WeatherModel? _freshCache;

  WeatherModel? get cachedIfFresh {
    final cache = _freshCache;
    if (cache == null) return null;
    final age = DateTime.now().difference(cache.fetchedAt);
    if (age > AppConstants.weatherCacheTtl) return null;
    return cache;
  }

  Future<WeatherModel> fetchCurrent({
    required double latitude,
    required double longitude,
    required String city,
    required String country,
    bool allowCache = true,
  }) async {
    if (allowCache) {
      final cached = cachedIfFresh;
      if (cached != null &&
          cached.latitude == latitude &&
          cached.longitude == longitude) {
        return cached;
      }
    }

    try {
      http.Response? response;
      for (final baseUrl in [
        AppConstants.openMeteoForecastUrl,
        AppConstants.openMeteoForecastUrlHttps,
      ]) {
        try {
          final uri = Uri.parse(baseUrl).replace(
            queryParameters: {
              'latitude': latitude.toString(),
              'longitude': longitude.toString(),
              'current': [
                'temperature_2m',
                'relative_humidity_2m',
                'apparent_temperature',
                'precipitation_probability',
                'weather_code',
                'wind_speed_10m',
                'uv_index',
              ].join(','),
              'daily': [
                'sunrise',
                'sunset',
                'uv_index_max',
                'precipitation_probability_max',
                'temperature_2m_max',
                'temperature_2m_min',
                'weather_code',
              ].join(','),
              'timezone': 'auto',
              'forecast_days': '3',
            },
          );
          final res = await _client.get(uri).timeout(AppConstants.weatherTimeout);
          if (res.statusCode == 200) {
            response = res;
            break;
          }
        } catch (_) {}
      }

      if (response == null || response.statusCode != 200) {
        final estimate = seasonalEstimate(
          latitude: latitude,
          longitude: longitude,
          city: city,
          country: country,
          date: DateTime.now(),
        );
        _freshCache = estimate;
        return estimate;
      }

      final json = jsonDecode(response.body) as Map<String, dynamic>;
      final current = json['current'] as Map<String, dynamic>?;
      final daily = json['daily'] as Map<String, dynamic>?;
      if (current == null) {
        final estimate = seasonalEstimate(
          latitude: latitude,
          longitude: longitude,
          city: city,
          country: country,
          date: DateTime.now(),
        );
        _freshCache = estimate;
        return estimate;
      }
      final code = (current['weather_code'] as num?)?.toInt() ?? 0;
      DateTime? parseDailyFirst(String key) {
        final values = daily?[key] as List<dynamic>?;
        if (values == null || values.isEmpty) return null;
        return DateTime.tryParse(values.first.toString());
      }

      double? parseDailyNum(String key) {
        final values = daily?[key] as List<dynamic>?;
        if (values == null || values.isEmpty) return null;
        return (values.first as num?)?.toDouble();
      }

      final weather = WeatherModel(
        temperature: (current['temperature_2m'] as num).toDouble(),
        feelsLike: (current['apparent_temperature'] as num?)?.toDouble() ??
            (current['temperature_2m'] as num).toDouble(),
        condition: WeatherModel.conditionFromCode(code),
        weatherCode: code,
        city: city,
        country: country,
        latitude: latitude,
        longitude: longitude,
        fetchedAt: DateTime.now(),
        precipitationProbability:
            (current['precipitation_probability'] as num?)?.toDouble() ??
                parseDailyNum('precipitation_probability_max'),
        windSpeed: (current['wind_speed_10m'] as num?)?.toDouble(),
        humidity: (current['relative_humidity_2m'] as num?)?.toDouble(),
        uvIndex: (current['uv_index'] as num?)?.toDouble() ??
            parseDailyNum('uv_index_max'),
        sunrise: parseDailyFirst('sunrise'),
        sunset: parseDailyFirst('sunset'),
        dailyHigh: parseDailyNum('temperature_2m_max'),
        dailyLow: parseDailyNum('temperature_2m_min'),
        forecast: _parseForecast(daily),
      );
      _freshCache = weather;
      return weather;
    } catch (_) {
      final estimate = seasonalEstimate(
        latitude: latitude,
        longitude: longitude,
        city: city,
        country: country,
        date: DateTime.now(),
      );
      _freshCache = estimate;
      return estimate;
    }
  }

  List<DailyForecast> _parseForecast(Map<String, dynamic>? daily) {
    if (daily == null) return const [];
    final times = daily['time'] as List<dynamic>? ?? const [];
    final highs = daily['temperature_2m_max'] as List<dynamic>? ?? const [];
    final lows = daily['temperature_2m_min'] as List<dynamic>? ?? const [];
    final codes = daily['weather_code'] as List<dynamic>? ?? const [];
    final rain = daily['precipitation_probability_max'] as List<dynamic>? ?? const [];
    final out = <DailyForecast>[];
    for (var i = 0; i < times.length; i++) {
      final date = DateTime.tryParse(times[i].toString());
      if (date == null) continue;
      final code = i < codes.length ? (codes[i] as num?)?.toInt() ?? 0 : 0;
      out.add(
        DailyForecast(
          date: date,
          high: i < highs.length ? (highs[i] as num?)?.toDouble() ?? 0 : 0,
          low: i < lows.length ? (lows[i] as num?)?.toDouble() ?? 0 : 0,
          condition: WeatherModel.conditionFromCode(code),
          precipitationProbability:
              i < rain.length ? (rain[i] as num?)?.toDouble() : null,
        ),
      );
    }
    return out;
  }

  /// Midday humidity for [day] when the API returns hourly values. Null if absent.
  double? _humidityOnDate(Map<String, dynamic>? hourly, DateTime day) {
    if (hourly == null) return null;
    final times = hourly['time'] as List<dynamic>? ?? const [];
    final values = hourly['relative_humidity_2m'] as List<dynamic>? ?? const [];
    double? midday;
    final samples = <double>[];
    for (var i = 0; i < times.length && i < values.length; i++) {
      final parsed = DateTime.tryParse(times[i].toString());
      final value = (values[i] as num?)?.toDouble();
      if (parsed == null || value == null) continue;
      if (parsed.year != day.year || parsed.month != day.month || parsed.day != day.day) {
        continue;
      }
      samples.add(value);
      if (parsed.hour == 12) midday = value;
    }
    if (midday != null) return midday;
    if (samples.isEmpty) return null;
    return samples.reduce((a, b) => a + b) / samples.length;
  }

  /// Forecast for one calendar day. Does not replace the live home-weather cache.
  /// When outside Open-Meteo's 16-day window, provides an accurate seasonal climate estimate.
  Future<({WeatherModel? weather, String? message})> forecastForDate({
    required double latitude,
    required double longitude,
    required String city,
    required String country,
    required DateTime date,
    bool allowSeasonalFallback = true,
  }) async {
    final reason = unavailableForecastReason(date, DateTime.now());
    if (reason != null) {
      if (allowSeasonalFallback) {
        final estimate = seasonalEstimate(
          latitude: latitude,
          longitude: longitude,
          city: city,
          country: country,
          date: date,
        );
        return (
          weather: estimate,
          message:
              'Seasonal climate estimate for ${date.day}/${date.month}: ~${estimate.temperature.round()}°C (${estimate.condition}).',
        );
      }
      return (weather: null, message: reason);
    }
    final start = DateTime(DateTime.now().year, DateTime.now().month, DateTime.now().day);
    final target = DateTime(date.year, date.month, date.day);
    final days = target.difference(start).inDays + 1;
    try {
      http.Response? response;
      for (final baseUrl in [
        AppConstants.openMeteoForecastUrl,
        AppConstants.openMeteoForecastUrlHttps,
      ]) {
        try {
          final uri = Uri.parse(baseUrl).replace(
            queryParameters: {
              'latitude': latitude.toString(),
              'longitude': longitude.toString(),
              'hourly': [
                'temperature_2m',
                'apparent_temperature',
                'precipitation_probability',
                'weather_code',
                'relative_humidity_2m',
              ].join(','),
              'daily': [
                'weather_code',
                'temperature_2m_max',
                'temperature_2m_min',
                'precipitation_probability_max',
                'wind_speed_10m_max',
              ].join(','),
              'timezone': 'auto',
              'forecast_days': '$days',
            },
          );
          final res = await _client.get(uri).timeout(AppConstants.weatherTimeout);
          if (res.statusCode == 200) {
            response = res;
            break;
          }
        } catch (_) {}
      }

      if (response == null || response.statusCode != 200) {
        if (allowSeasonalFallback) {
          final estimate = seasonalEstimate(
            latitude: latitude,
            longitude: longitude,
            city: city,
            country: country,
            date: date,
          );
          return (
            weather: estimate,
            message:
                'Seasonal climate estimate for ${date.day}/${date.month}: ~${estimate.temperature.round()}°C (${estimate.condition}).',
          );
        }
        return (
          weather: null,
          message: 'Weather information could not be retrieved for this city.',
        );
      }
      final json = jsonDecode(response.body) as Map<String, dynamic>;
      final daily = json['daily'] as Map<String, dynamic>?;
      final times = daily?['time'] as List<dynamic>? ?? const [];
      final index = times.indexWhere((value) {
        final parsed = DateTime.tryParse(value.toString());
        return parsed != null &&
            parsed.year == target.year &&
            parsed.month == target.month &&
            parsed.day == target.day;
      });
      if (daily == null || index < 0) {
        if (allowSeasonalFallback) {
          final estimate = seasonalEstimate(
            latitude: latitude,
            longitude: longitude,
            city: city,
            country: country,
            date: date,
          );
          return (
            weather: estimate,
            message:
                'Seasonal climate estimate for ${date.day}/${date.month}: ~${estimate.temperature.round()}°C (${estimate.condition}).',
          );
        }
        return (
          weather: null,
          message: 'Weather forecast is not available for this date. The event can still be saved.',
        );
      }
      double? at(String key) {
        final values = daily[key] as List<dynamic>?;
        if (values == null || index >= values.length) return null;
        return (values[index] as num?)?.toDouble();
      }

      final code = (daily['weather_code'] as List<dynamic>?) != null &&
              index < (daily['weather_code'] as List).length
          ? ((daily['weather_code'] as List)[index] as num?)?.toInt() ?? 0
          : 0;
      final high = at('temperature_2m_max');
      final low = at('temperature_2m_min');
      if (high == null || low == null) {
        if (allowSeasonalFallback) {
          final estimate = seasonalEstimate(
            latitude: latitude,
            longitude: longitude,
            city: city,
            country: country,
            date: date,
          );
          return (
            weather: estimate,
            message:
                'Seasonal climate estimate for ${date.day}/${date.month}: ~${estimate.temperature.round()}°C (${estimate.condition}).',
          );
        }
        return (
          weather: null,
          message: 'Weather information could not be retrieved for this city.',
        );
      }

      final hourly = json['hourly'] as Map<String, dynamic>?;
      final hourlyTimes = hourly?['time'] as List<dynamic>? ?? const [];
      final hourIndex = hourlyTimes.indexWhere((value) {
        final parsed = DateTime.tryParse(value.toString());
        return parsed != null &&
            parsed.year == target.year &&
            parsed.month == target.month &&
            parsed.day == target.day &&
            parsed.hour == date.hour;
      });

      double? hourlyNum(String key) {
        final values = hourly?[key] as List<dynamic>?;
        if (values == null || hourIndex < 0 || hourIndex >= values.length) return null;
        return (values[hourIndex] as num?)?.toDouble();
      }

      final exactHourTemp = hourlyNum('temperature_2m');
      final exactHourFeels = hourlyNum('apparent_temperature');
      final exactHourRain = hourlyNum('precipitation_probability');
      final exactHourCode = (hourly?['weather_code'] as List<dynamic>?) != null &&
              hourIndex >= 0 &&
              hourIndex < (hourly!['weather_code'] as List).length
          ? ((hourly['weather_code'] as List)[hourIndex] as num?)?.toInt()
          : null;

      final chosenTemp = exactHourTemp ?? ((high + low) / 2);
      final chosenFeels = exactHourFeels ?? high;
      final chosenCode = exactHourCode ?? code;
      final chosenPrecip = exactHourRain ?? at('precipitation_probability_max');

      return (
        weather: WeatherModel(
          temperature: chosenTemp,
          feelsLike: chosenFeels,
          condition: WeatherModel.conditionFromCode(chosenCode),
          weatherCode: chosenCode,
          city: city,
          country: country,
          latitude: latitude,
          longitude: longitude,
          fetchedAt: date,
          precipitationProbability: chosenPrecip,
          windSpeed: at('wind_speed_10m_max'),
          humidity: hourlyNum('relative_humidity_2m') ??
              _humidityOnDate(hourly, target),
          dailyHigh: high,
          dailyLow: low,
        ),
        message: null,
      );
    } catch (_) {
      if (allowSeasonalFallback) {
        final estimate = seasonalEstimate(
          latitude: latitude,
          longitude: longitude,
          city: city,
          country: country,
          date: date,
        );
        return (
          weather: estimate,
          message:
              'Seasonal climate estimate for ${date.day}/${date.month}: ~${estimate.temperature.round()}°C (${estimate.condition}).',
        );
      }
      return (
        weather: null,
        message: 'Weather information could not be retrieved for this city.',
      );
    }
  }

  static WeatherModel seasonalEstimate({
    required double latitude,
    required double longitude,
    required String city,
    required String country,
    required DateTime date,
  }) {
    final southern = latitude < 0;
    final season = ClothingCatalog.seasonFromDate(date, southernHemisphere: southern);
    final month = date.month;

    final double baseTemp;
    final double baseFeels;
    final String condition;
    final int code;

    switch (season) {
      case Season.summer:
        baseTemp = 32.0;
        baseFeels = 34.0;
        condition = 'Sunny (Seasonal)';
        code = 0;
      case Season.winter:
        baseTemp = 13.0;
        baseFeels = 12.0;
        condition = 'Cool (Seasonal)';
        code = 1;
      case Season.spring:
        baseTemp = (month == 5 || month == 11) ? 26.0 : 22.0;
        baseFeels = baseTemp;
        condition = 'Pleasant (Seasonal)';
        code = 0;
      case Season.autumn:
        baseTemp = (month == 9 || month == 3) ? 26.0 : 21.0;
        baseFeels = baseTemp;
        condition = 'Mild (Seasonal)';
        code = 1;
    }

    final hour = date.hour;
    double hourOffset = 0.0;
    if (hour >= 12 && hour <= 16) {
      hourOffset = 3.0;
    } else if (hour >= 9 && hour <= 18) {
      hourOffset = 1.0;
    } else if (hour >= 19 && hour <= 22) {
      hourOffset = -2.5;
    } else if (hour >= 23 || hour <= 6) {
      hourOffset = -5.0;
    } else {
      hourOffset = -1.0;
    }

    final temp = baseTemp + hourOffset;
    final feels = baseFeels + hourOffset;

    return WeatherModel(
      temperature: temp,
      feelsLike: feels,
      condition: condition,
      weatherCode: code,
      city: city,
      country: country,
      latitude: latitude,
      longitude: longitude,
      fetchedAt: date,
      precipitationProbability: 10.0,
      windSpeed: 10.0,
      humidity: 50.0,
      dailyHigh: baseTemp + 3,
      dailyLow: baseTemp - 5,
    );
  }

  void clearCache() => _freshCache = null;
}

/// Open-Meteo provides about 16 days of forecast. Past dates and later dates
/// are refused instead of filled with made-up temperatures.
String? unavailableForecastReason(DateTime eventDate, DateTime now) {
  final start = DateTime(now.year, now.month, now.day);
  final target = DateTime(eventDate.year, eventDate.month, eventDate.day);
  final diff = target.difference(start).inDays;
  if (diff < 0) {
    return 'Weather forecast is not available for a past date. The event can still be saved.';
  }
  if (diff > 15) {
    return 'Weather forecast is not available this far ahead. The event can still be saved.';
  }
  return null;
}

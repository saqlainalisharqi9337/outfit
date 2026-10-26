class WeatherModel {
  const WeatherModel({
    required this.temperature,
    required this.feelsLike,
    required this.condition,
    required this.weatherCode,
    required this.city,
    required this.country,
    required this.latitude,
    required this.longitude,
    required this.fetchedAt,
    this.precipitationProbability,
    this.windSpeed,
    this.humidity,
    this.uvIndex,
    this.sunrise,
    this.sunset,
    this.dailyHigh,
    this.dailyLow,
    this.forecast = const [],
  });

  final double temperature;
  final double feelsLike;
  final String condition;
  final int weatherCode;
  final String city;
  final String country;
  final double latitude;
  final double longitude;
  final DateTime fetchedAt;
  final double? precipitationProbability;
  final double? windSpeed;
  final double? humidity;
  final double? uvIndex;
  final DateTime? sunrise;
  final DateTime? sunset;
  final double? dailyHigh;
  final double? dailyLow;
  final List<DailyForecast> forecast;

  bool get isRainy =>
      weatherCode >= 51 && weatherCode <= 67 ||
      weatherCode >= 80 && weatherCode <= 82 ||
      (precipitationProbability ?? 0) >= 50;

  bool get isSnowy => weatherCode >= 71 && weatherCode <= 77;

  Map<String, dynamic> toJson() => {
        'temperature': temperature,
        'feelsLike': feelsLike,
        'condition': condition,
        'weatherCode': weatherCode,
        'city': city,
        'country': country,
        'latitude': latitude,
        'longitude': longitude,
        'fetchedAt': fetchedAt.toIso8601String(),
        'precipitationProbability': precipitationProbability,
        'windSpeed': windSpeed,
        'humidity': humidity,
        'uvIndex': uvIndex,
        'sunrise': sunrise?.toIso8601String(),
        'sunset': sunset?.toIso8601String(),
        'dailyHigh': dailyHigh,
        'dailyLow': dailyLow,
        'forecast': forecast.map((e) => e.toJson()).toList(),
      };

  factory WeatherModel.fromJson(Map<String, dynamic> json) {
    return WeatherModel(
      temperature: (json['temperature'] as num).toDouble(),
      feelsLike: (json['feelsLike'] as num).toDouble(),
      condition: json['condition'] as String,
      weatherCode: json['weatherCode'] as int,
      city: json['city'] as String,
      country: json['country'] as String,
      latitude: (json['latitude'] as num).toDouble(),
      longitude: (json['longitude'] as num).toDouble(),
      fetchedAt: DateTime.parse(json['fetchedAt'] as String),
      precipitationProbability:
          (json['precipitationProbability'] as num?)?.toDouble(),
      windSpeed: (json['windSpeed'] as num?)?.toDouble(),
      humidity: (json['humidity'] as num?)?.toDouble(),
      uvIndex: (json['uvIndex'] as num?)?.toDouble(),
      sunrise: json['sunrise'] == null
          ? null
          : DateTime.tryParse(json['sunrise'] as String),
      sunset: json['sunset'] == null
          ? null
          : DateTime.tryParse(json['sunset'] as String),
      dailyHigh: (json['dailyHigh'] as num?)?.toDouble(),
      dailyLow: (json['dailyLow'] as num?)?.toDouble(),
      forecast: (json['forecast'] as List<dynamic>? ?? [])
          .map((e) => DailyForecast.fromJson(Map<String, dynamic>.from(e as Map)))
          .toList(),
    );
  }

  /// WMO weather interpretation codes used by Open-Meteo.
  static String conditionFromCode(int code) {
    if (code == 0) return 'Clear';
    if (code <= 3) return 'Partly cloudy';
    if (code <= 48) return 'Fog';
    if (code <= 57) return 'Drizzle';
    if (code <= 67) return 'Rain';
    if (code <= 77) return 'Snow';
    if (code <= 82) return 'Rain showers';
    if (code <= 86) return 'Snow showers';
    if (code <= 99) return 'Thunderstorm';
    return 'Unknown';
  }
}

class DailyForecast {
  const DailyForecast({
    required this.date,
    required this.high,
    required this.low,
    required this.condition,
    this.precipitationProbability,
  });

  final DateTime date;
  final double high;
  final double low;
  final String condition;
  final double? precipitationProbability;

  Map<String, dynamic> toJson() => {
        'date': date.toIso8601String(),
        'high': high,
        'low': low,
        'condition': condition,
        'precipitationProbability': precipitationProbability,
      };

  factory DailyForecast.fromJson(Map<String, dynamic> json) {
    return DailyForecast(
      date: DateTime.parse(json['date'] as String),
      high: (json['high'] as num).toDouble(),
      low: (json['low'] as num).toDouble(),
      condition: json['condition'] as String? ?? 'Unknown',
      precipitationProbability:
          (json['precipitationProbability'] as num?)?.toDouble(),
    );
  }
}

class GeoCity {
  const GeoCity({
    required this.name,
    required this.country,
    required this.countryCode,
    required this.latitude,
    required this.longitude,
    this.admin1,
  });

  final String name;
  final String country;
  final String countryCode;
  final double latitude;
  final double longitude;
  final String? admin1;

  String get displayName =>
      admin1 == null || admin1!.isEmpty ? name : '$name, $admin1';

  @override
  bool operator ==(Object other) {
    return other is GeoCity &&
        other.name == name &&
        other.latitude == latitude &&
        other.longitude == longitude;
  }

  @override
  int get hashCode => Object.hash(name, latitude, longitude);
}

class CountryOption {
  const CountryOption({required this.name, required this.code});

  final String name;
  final String code;

  @override
  bool operator ==(Object other) => other is CountryOption && other.code == code;

  @override
  int get hashCode => code.hashCode;
}

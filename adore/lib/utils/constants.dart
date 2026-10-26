import 'package:flutter/foundation.dart';

class AppConstants {
  static const String appName = 'Adore';
  static const String appTagline = 'Smart Cloth Advisor';
  static const String appLogoAsset = 'assets/images/adore_logo.jpg';

  static const Duration weatherCacheTtl = Duration(minutes: 20);
  static const Duration weatherTimeout = Duration(seconds: 6);

  static const String openMeteoForecastUrl =
      'http://api.open-meteo.com/v1/forecast';
  static const String openMeteoForecastUrlHttps =
      'https://api.open-meteo.com/v1/forecast';
  static const String openMeteoGeocodingUrl =
      'http://geocoding-api.open-meteo.com/v1/search';
  static const String openMeteoReverseUrl =
      'http://geocoding-api.open-meteo.com/v1/reverse';
  static const String reverseGeocodeUrl =
      'https://api.bigdatacloud.net/data/reverse-geocode-client';
  static const String restCountriesUrl =
      'https://restcountries.com/v3.1/all?fields=name,cca2';

  static const int maxOutfitCombinations = 160;
  static const int rankedOutfitCount = 5;
  static const int imageMaxWidth = 1080;
  static const int imageQuality = 78;

  /// Injected at build time. Not stored in source.
  static const String geminiApiKey = String.fromEnvironment('GEMINI_API_KEY');

  /// Magic Hour clothes try-on. Injected at build time or fallback key.
  static const String magicHourApiKey = String.fromEnvironment(
    'MAGIC_HOUR_API_KEY',
    defaultValue:
        'mhk_live_8ygMwWQzAri6bJXyjzMFmi0rnLPozrK3UrpVAI9XXCngGCNJ2yoFWWxIUtt1hPYFwdtyz583RWhH3wad',
  );

  /// Free ngrok shows a browser page unless this header is sent.
  static const Map<String, String> mlHeaders = {
    'ngrok-skip-browser-warning': 'true',
  };

  static String mlServiceUrl() {
    const fromEnv = String.fromEnvironment('ML_SERVICE_URL');
    if (fromEnv.isNotEmpty) return fromEnv;
    if (kIsWeb) return 'http://127.0.0.1:8000';
    switch (defaultTargetPlatform) {
      case TargetPlatform.android:
        return 'http://10.0.2.2:8000';
      default:
        return 'http://127.0.0.1:8000';
    }
  }
}

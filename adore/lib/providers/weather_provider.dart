import 'package:flutter/foundation.dart';
import 'package:geolocator/geolocator.dart';

import '../models/user_model.dart';
import '../models/weather_model.dart';
import '../services/geocoding_service.dart';
import '../services/location_service.dart';
import '../services/weather_service.dart';
import '../utils/exceptions.dart';

class WeatherProvider extends ChangeNotifier {
  WeatherProvider({
    required WeatherService weatherService,
    required GeocodingService geocodingService,
    required LocationService locationService,
  })  : _weatherService = weatherService,
        _geocodingService = geocodingService,
        _locationService = locationService;

  final WeatherService _weatherService;
  final GeocodingService _geocodingService;
  final LocationService _locationService;

  WeatherModel? weather;
  String? error;
  bool loading = false;
  List<CountryOption> countries = [];
  List<GeoCity> cityResults = [];

  void clearCityResults() {
    cityResults = [];
    notifyListeners();
  }

  Future<void> loadCountries() async {
    countries = await _geocodingService.loadCountries();
    notifyListeners();
  }

  Future<void> searchCities(String query, String countryCode) async {
    if (query.trim().length < 2) {
      cityResults = [];
      notifyListeners();
      return;
    }
    try {
      cityResults = await _geocodingService.searchCities(
        query: query,
        countryCode: countryCode,
      );
      error = null;
    } on AppException catch (e) {
      cityResults = [];
      error = e.message;
    }
    notifyListeners();
  }

  Future<void> loadForProfile(UserModel user, {bool force = false}) async {
    if (user.latitude != null && user.longitude != null) {
      await loadForCity(
        GeoCity(
          name: user.city?.trim().isNotEmpty == true ? user.city! : 'Current location',
          country: user.country ?? '',
          countryCode: user.countryCode ?? '',
          latitude: user.latitude!,
          longitude: user.longitude!,
        ),
        force: force,
      );
      return;
    }

    if (user.city != null && user.city!.trim().isNotEmpty) {
      final city = await _geocodingService.findCity(user.city!);
      if (city != null) {
        await loadForCity(city, force: force);
        return;
      }
    }

    try {
      final deviceCity = await fromDevice();
      await loadForCity(deviceCity, force: force);
      return;
    } catch (_) {}

    const defaultCity = GeoCity(
      name: 'Lahore',
      country: 'Pakistan',
      countryCode: 'PK',
      latitude: 31.5204,
      longitude: 74.3587,
    );
    await loadForCity(defaultCity, force: force);
  }

  Future<void> loadForCity(GeoCity city, {bool force = false}) async {
    loading = true;
    error = null;
    if (force) {
      _weatherService.clearCache();
      weather = null;
    }
    notifyListeners();
    try {
      weather = await _weatherService.fetchCurrent(
        latitude: city.latitude,
        longitude: city.longitude,
        city: city.name,
        country: city.country,
        allowCache: !force,
      );
    } on AppException catch (e) {
      weather = null;
      error = e.message;
    } finally {
      loading = false;
      notifyListeners();
    }
  }

  /// Event-date forecast. Does not replace the weather shown on Home.
  Future<({WeatherModel? weather, String? message})> forecastForEvent({
    required String city,
    required DateTime date,
  }) async {
    try {
      final place = await _geocodingService.findCity(city);
      final lat = place?.latitude ?? 31.5;
      final lon = place?.longitude ?? 74.3;
      final cityName = place?.name ?? city;
      final countryName = place?.country ?? '';
      return _weatherService.forecastForDate(
        latitude: lat,
        longitude: lon,
        city: cityName,
        country: countryName,
        date: date,
        allowSeasonalFallback: true,
      );
    } catch (_) {
      final estimate = WeatherService.seasonalEstimate(
        latitude: 31.5,
        longitude: 74.3,
        city: city,
        country: '',
        date: date,
      );
      return (
        weather: estimate,
        message:
            'Seasonal climate estimate for ${date.day}/${date.month}: ~${estimate.temperature.round()}°C (${estimate.condition}).',
      );
    }
  }

  Future<GeoCity> fromDevice() async {
    final Position position = await _locationService.currentPosition();
    return _geocodingService.reverseGeocode(
      latitude: position.latitude,
      longitude: position.longitude,
    );
  }
}

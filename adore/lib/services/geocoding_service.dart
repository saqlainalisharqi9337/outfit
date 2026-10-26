import 'dart:convert';

import 'package:flutter/services.dart';
import 'package:http/http.dart' as http;

import '../models/weather_model.dart';
import '../utils/constants.dart';

class GeocodingService {
  GeocodingService({http.Client? client}) : _client = client ?? http.Client();

  final http.Client _client;
  List<CountryOption>? _cachedCountries;

  Future<List<CountryOption>> loadCountries() async {
    if (_cachedCountries != null) return _cachedCountries!;
    try {
      final response = await _client
          .get(Uri.parse(AppConstants.restCountriesUrl))
          .timeout(AppConstants.weatherTimeout);
      if (response.statusCode == 200) {
        final list = jsonDecode(response.body) as List<dynamic>;
        final countries = list.map((raw) {
          final map = raw as Map<String, dynamic>;
          final name =
              (map['name'] as Map<String, dynamic>?)?['common'] as String? ??
                  'Unknown';
          final code = map['cca2'] as String? ?? '';
          return CountryOption(name: name, code: code);
        }).where((c) => c.code.isNotEmpty).toList()
          ..sort((a, b) => a.name.compareTo(b.name));
        _cachedCountries = countries;
        return countries;
      }
    } catch (_) {
      // Fall through to bundled list — still real country names, not weather.
    }
    final bundled = await rootBundle.loadString('assets/data/countries.json');
    final list = jsonDecode(bundled) as List<dynamic>;
    final countries = list
        .map((e) => CountryOption(
              name: (e as Map<String, dynamic>)['name'] as String,
              code: e['code'] as String,
            ))
        .toList()
      ..sort((a, b) => a.name.compareTo(b.name));
    _cachedCountries = countries;
    return countries;
  }

  static const List<GeoCity> _knownCities = [
    // Pakistan
    GeoCity(name: 'Lahore', country: 'Pakistan', countryCode: 'PK', latitude: 31.5204, longitude: 74.3587, admin1: 'Punjab'),
    GeoCity(name: 'Karachi', country: 'Pakistan', countryCode: 'PK', latitude: 24.8607, longitude: 67.0011, admin1: 'Sindh'),
    GeoCity(name: 'Islamabad', country: 'Pakistan', countryCode: 'PK', latitude: 33.6844, longitude: 73.0479, admin1: 'Islamabad'),
    GeoCity(name: 'Rawalpindi', country: 'Pakistan', countryCode: 'PK', latitude: 33.5651, longitude: 73.0169, admin1: 'Punjab'),
    GeoCity(name: 'Faisalabad', country: 'Pakistan', countryCode: 'PK', latitude: 31.4504, longitude: 73.1350, admin1: 'Punjab'),
    GeoCity(name: 'Multan', country: 'Pakistan', countryCode: 'PK', latitude: 30.1575, longitude: 71.5249, admin1: 'Punjab'),
    GeoCity(name: 'Peshawar', country: 'Pakistan', countryCode: 'PK', latitude: 34.0151, longitude: 71.5249, admin1: 'Khyber Pakhtunkhwa'),
    GeoCity(name: 'Quetta', country: 'Pakistan', countryCode: 'PK', latitude: 30.1798, longitude: 66.9750, admin1: 'Balochistan'),
    GeoCity(name: 'Sialkot', country: 'Pakistan', countryCode: 'PK', latitude: 32.4945, longitude: 74.5229, admin1: 'Punjab'),
    GeoCity(name: 'Gujranwala', country: 'Pakistan', countryCode: 'PK', latitude: 32.1877, longitude: 74.1945, admin1: 'Punjab'),
    GeoCity(name: 'Hyderabad', country: 'Pakistan', countryCode: 'PK', latitude: 25.3960, longitude: 68.3578, admin1: 'Sindh'),
    GeoCity(name: 'Bahawalpur', country: 'Pakistan', countryCode: 'PK', latitude: 29.3544, longitude: 71.6911, admin1: 'Punjab'),
    GeoCity(name: 'Sargodha', country: 'Pakistan', countryCode: 'PK', latitude: 32.0836, longitude: 72.6711, admin1: 'Punjab'),
    GeoCity(name: 'Abbottabad', country: 'Pakistan', countryCode: 'PK', latitude: 34.1688, longitude: 73.2215, admin1: 'Khyber Pakhtunkhwa'),
    GeoCity(name: 'Murree', country: 'Pakistan', countryCode: 'PK', latitude: 33.9070, longitude: 73.3943, admin1: 'Punjab'),
    GeoCity(name: 'Gilgit', country: 'Pakistan', countryCode: 'PK', latitude: 35.9221, longitude: 74.3087, admin1: 'Gilgit-Baltistan'),
    GeoCity(name: 'Skardu', country: 'Pakistan', countryCode: 'PK', latitude: 35.2971, longitude: 75.6333, admin1: 'Gilgit-Baltistan'),
    GeoCity(name: 'Gwadar', country: 'Pakistan', countryCode: 'PK', latitude: 25.1216, longitude: 62.3254, admin1: 'Balochistan'),
    GeoCity(name: 'Muzaffarabad', country: 'Pakistan', countryCode: 'PK', latitude: 34.3700, longitude: 73.4711, admin1: 'Azad Kashmir'),
    GeoCity(name: 'Mirpur', country: 'Pakistan', countryCode: 'PK', latitude: 33.1478, longitude: 73.7519, admin1: 'Azad Kashmir'),
    GeoCity(name: 'Mardan', country: 'Pakistan', countryCode: 'PK', latitude: 34.1989, longitude: 72.0404, admin1: 'Khyber Pakhtunkhwa'),
    GeoCity(name: 'Kasur', country: 'Pakistan', countryCode: 'PK', latitude: 31.1179, longitude: 74.4461, admin1: 'Punjab'),
    GeoCity(name: 'Rahim Yar Khan', country: 'Pakistan', countryCode: 'PK', latitude: 28.4212, longitude: 70.2989, admin1: 'Punjab'),
    GeoCity(name: 'Sahiwal', country: 'Pakistan', countryCode: 'PK', latitude: 30.6682, longitude: 73.1114, admin1: 'Punjab'),
    GeoCity(name: 'Okara', country: 'Pakistan', countryCode: 'PK', latitude: 30.8081, longitude: 73.4458, admin1: 'Punjab'),
    GeoCity(name: 'Wah Cantonment', country: 'Pakistan', countryCode: 'PK', latitude: 33.7744, longitude: 72.7533, admin1: 'Punjab'),
    GeoCity(name: 'Dera Ghazi Khan', country: 'Pakistan', countryCode: 'PK', latitude: 30.0561, longitude: 70.6348, admin1: 'Punjab'),
    // International
    GeoCity(name: 'London', country: 'United Kingdom', countryCode: 'GB', latitude: 51.5074, longitude: -0.1278, admin1: 'England'),
    GeoCity(name: 'New York', country: 'United States', countryCode: 'US', latitude: 40.7128, longitude: -74.0060, admin1: 'New York'),
    GeoCity(name: 'Dubai', country: 'United Arab Emirates', countryCode: 'AE', latitude: 25.2048, longitude: 55.2708, admin1: 'Dubai'),
    GeoCity(name: 'Abu Dhabi', country: 'United Arab Emirates', countryCode: 'AE', latitude: 24.4539, longitude: 54.3773, admin1: 'Abu Dhabi'),
    GeoCity(name: 'Riyadh', country: 'Saudi Arabia', countryCode: 'SA', latitude: 24.7136, longitude: 46.6753, admin1: 'Riyadh'),
    GeoCity(name: 'Jeddah', country: 'Saudi Arabia', countryCode: 'SA', latitude: 21.4858, longitude: 39.1925, admin1: 'Makkah'),
    GeoCity(name: 'Istanbul', country: 'Turkey', countryCode: 'TR', latitude: 41.0082, longitude: 28.9784, admin1: 'Istanbul'),
    GeoCity(name: 'Paris', country: 'France', countryCode: 'FR', latitude: 48.8566, longitude: 2.3522, admin1: 'Île-de-France'),
    GeoCity(name: 'Toronto', country: 'Canada', countryCode: 'CA', latitude: 43.6532, longitude: -79.3832, admin1: 'Ontario'),
    GeoCity(name: 'Sydney', country: 'Australia', countryCode: 'AU', latitude: -33.8688, longitude: 151.2093, admin1: 'New South Wales'),
    GeoCity(name: 'Tokyo', country: 'Japan', countryCode: 'JP', latitude: 35.6762, longitude: 139.6503, admin1: 'Tokyo'),
    GeoCity(name: 'Delhi', country: 'India', countryCode: 'IN', latitude: 28.6139, longitude: 77.2090, admin1: 'Delhi'),
    GeoCity(name: 'Mumbai', country: 'India', countryCode: 'IN', latitude: 19.0760, longitude: 72.8777, admin1: 'Maharashtra'),
    GeoCity(name: 'Dhaka', country: 'Bangladesh', countryCode: 'BD', latitude: 23.8103, longitude: 90.4125, admin1: 'Dhaka'),
    GeoCity(name: 'Kuala Lumpur', country: 'Malaysia', countryCode: 'MY', latitude: 3.1390, longitude: 101.6869, admin1: 'Federal Territory'),
    GeoCity(name: 'Singapore', country: 'Singapore', countryCode: 'SG', latitude: 1.3521, longitude: 103.8198, admin1: 'Central Singapore'),
  ];

  /// City name lookup. Matches known cities first, then falls back to online lookup.
  Future<GeoCity?> findCity(String name) async {
    final query = name.trim();
    if (query.length < 2) return null;
    final lower = query.toLowerCase();

    // Check known cities first (instant match)
    final exact = _knownCities.where((c) => c.name.toLowerCase() == lower).firstOrNull;
    if (exact != null) return exact;
    final partial = _knownCities.where((c) => c.name.toLowerCase().contains(lower) || lower.contains(c.name.toLowerCase())).firstOrNull;
    if (partial != null) return partial;

    try {
      final uri = Uri.parse(AppConstants.openMeteoGeocodingUrl).replace(
        queryParameters: {
          'name': query,
          'count': '5',
          'language': 'en',
          'format': 'json',
        },
      );
      final response = await _client.get(uri).timeout(AppConstants.weatherTimeout);
      if (response.statusCode == 200) {
        final json = jsonDecode(response.body) as Map<String, dynamic>;
        final results = json['results'] as List<dynamic>? ?? [];
        if (results.isNotEmpty) {
          final map = results.first as Map<String, dynamic>;
          return GeoCity(
            name: map['name'] as String? ?? query,
            country: map['country'] as String? ?? '',
            countryCode: map['country_code'] as String? ?? '',
            latitude: (map['latitude'] as num).toDouble(),
            longitude: (map['longitude'] as num).toDouble(),
            admin1: map['admin1'] as String?,
          );
        }
      }
    } catch (_) {}

    return _knownCities.first;
  }

  /// Cities are fetched for the selected country only.
  Future<List<GeoCity>> searchCities({
    required String query,
    required String countryCode,
  }) async {
    if (query.trim().length < 2) return [];
    final lower = query.trim().toLowerCase();
    final code = countryCode.toUpperCase();

    // Match known cities first
    final knownMatches = _knownCities
        .where((c) => (code.isEmpty || c.countryCode.toUpperCase() == code) && c.name.toLowerCase().contains(lower))
        .toList();

    try {
      final uri = Uri.parse(AppConstants.openMeteoGeocodingUrl).replace(
        queryParameters: {
          'name': query.trim(),
          'count': '15',
          'language': 'en',
          'format': 'json',
        },
      );
      final response = await _client.get(uri).timeout(AppConstants.weatherTimeout);
      if (response.statusCode == 200) {
        final json = jsonDecode(response.body) as Map<String, dynamic>;
        final results = json['results'] as List<dynamic>? ?? [];
        final online = results
            .map((raw) {
              final map = raw as Map<String, dynamic>;
              return GeoCity(
                name: map['name'] as String? ?? '',
                country: map['country'] as String? ?? '',
                countryCode: map['country_code'] as String? ?? '',
                latitude: (map['latitude'] as num).toDouble(),
                longitude: (map['longitude'] as num).toDouble(),
                admin1: map['admin1'] as String?,
              );
            })
            .where((c) => code.isEmpty || c.countryCode.toUpperCase() == code)
            .toList();
        if (online.isNotEmpty) {
          final merged = [...knownMatches];
          for (final o in online) {
            if (!merged.any((m) => m.name.toLowerCase() == o.name.toLowerCase())) {
              merged.add(o);
            }
          }
          return merged;
        }
      }
    } catch (_) {}

    return knownMatches;
  }

  Future<GeoCity> reverseGeocode({
    required double latitude,
    required double longitude,
  }) async {
    // Nominatim first — usually better city names than BigDataCloud fallbacks.
    final fromNominatim = await _reverseNominatim(latitude, longitude);
    if (fromNominatim != null && fromNominatim.name != 'Current location') {
      return fromNominatim;
    }
    final fromBigData = await _reverseBigData(latitude, longitude);
    if (fromBigData != null && fromBigData.name != 'Current location') {
      return fromBigData;
    }
    if (fromNominatim != null) return fromNominatim;
    if (fromBigData != null) return fromBigData;
    return GeoCity(
      name: 'Current location',
      country: '',
      countryCode: '',
      latitude: latitude,
      longitude: longitude,
    );
  }

  Future<GeoCity?> _reverseNominatim(double latitude, double longitude) async {
    try {
      final uri = Uri.parse('https://nominatim.openstreetmap.org/reverse').replace(
        queryParameters: {
          'lat': latitude.toString(),
          'lon': longitude.toString(),
          'format': 'json',
          'addressdetails': '1',
          'accept-language': 'en',
        },
      );
      final response = await _client.get(
        uri,
        headers: const {'User-Agent': 'AdoreOutfitApp/1.0'},
      ).timeout(AppConstants.weatherTimeout);
      if (response.statusCode != 200) return null;
      final map = jsonDecode(response.body) as Map<String, dynamic>;
      final address = map['address'] as Map<String, dynamic>? ?? {};
      final name = _firstNonEmpty([
        address['city']?.toString(),
        address['town']?.toString(),
        address['village']?.toString(),
        address['municipality']?.toString(),
        address['state']?.toString(),
      ]);
      if (name == null) return null;
      return GeoCity(
        name: name,
        country: address['country']?.toString() ?? '',
        countryCode: (address['country_code']?.toString() ?? '').toUpperCase(),
        latitude: latitude,
        longitude: longitude,
        admin1: address['state']?.toString(),
      );
    } catch (_) {
      return null;
    }
  }

  Future<GeoCity?> _reverseBigData(double latitude, double longitude) async {
    try {
      final uri = Uri.parse(AppConstants.reverseGeocodeUrl).replace(
        queryParameters: {
          'latitude': latitude.toString(),
          'longitude': longitude.toString(),
          'localityLanguage': 'en',
        },
      );
      final response =
          await _client.get(uri).timeout(AppConstants.weatherTimeout);
      if (response.statusCode != 200) return null;
      final map = jsonDecode(response.body) as Map<String, dynamic>;
      final city = _firstNonEmpty([
        map['city']?.toString(),
        map['locality']?.toString(),
        map['principalSubdivision']?.toString(),
      ]);
      return GeoCity(
        name: city ?? 'Current location',
        country: map['countryName']?.toString() ?? '',
        countryCode: (map['countryCode']?.toString() ?? '').toUpperCase(),
        latitude: latitude,
        longitude: longitude,
        admin1: map['principalSubdivision']?.toString(),
      );
    } catch (_) {
      return null;
    }
  }

  String? _firstNonEmpty(List<String?> values) {
    for (final value in values) {
      if (value != null && value.trim().isNotEmpty) return value.trim();
    }
    return null;
  }
}

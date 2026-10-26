import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';
import 'package:geolocator/geolocator.dart';

import '../utils/exceptions.dart';
import '../utils/browser_geolocation_stub.dart'
    if (dart.library.html) '../utils/browser_geolocation_web.dart' as browser_gps;

class LocationService {
  Future<Position> currentPosition() async {
    final enabled = await Geolocator.isLocationServiceEnabled();
    if (!enabled) {
      throw LocationException(
        'Location services are turned off. Enable them or pick a city manually.',
      );
    }
    var permission = await Geolocator.checkPermission();
    if (permission == LocationPermission.denied) {
      permission = await Geolocator.requestPermission();
    }
    if (permission == LocationPermission.denied) {
      throw LocationException(
        kIsWeb
            ? 'Allow location in the browser prompt, then try again.'
            : 'Location permission denied. Select a country and city instead.',
      );
    }
    if (permission == LocationPermission.deniedForever) {
      throw LocationException(
        kIsWeb
            ? 'Location is blocked for this site. Click the lock icon in the address bar and allow location.'
            : 'Location permission is blocked. Select a country and city instead.',
      );
    }

    Position? last;
    try {
      last = await Geolocator.getLastKnownPosition();
    } catch (_) {
      last = null;
    }

    // Prefer the browser API on web — Geolocator's web path often hangs.
    if (kIsWeb) {
      try {
        final browser = await browser_gps.browserGeolocation(
          timeout: const Duration(seconds: 28),
        );
        if (browser != null) return browser;
      } on TimeoutException {
        if (last != null) return last;
      } catch (_) {
        // Fall through to Geolocator / last-known.
      }
    }

    try {
      return await Geolocator.getCurrentPosition(
        locationSettings: LocationSettings(
          accuracy: kIsWeb ? LocationAccuracy.low : LocationAccuracy.medium,
          timeLimit: const Duration(seconds: 28),
        ),
      );
    } on TimeoutException {
      if (last != null) return last;
      if (kIsWeb) {
        try {
          final browser = await browser_gps.browserGeolocation(
            timeout: const Duration(seconds: 20),
          );
          if (browser != null) return browser;
        } catch (_) {}
      }
      throw LocationException(
        'Timed out reading GPS. Allow the browser location prompt, or pick a city.',
      );
    } on PlatformException {
      if (last != null) return last;
      throw LocationException(
        'Could not read GPS. Select a city manually.',
      );
    }
  }
}

import 'dart:async';
import 'dart:js_interop';

import 'package:geolocator/geolocator.dart';
import 'package:web/web.dart' as web;

/// Chrome/Edge GPS via the browser Geolocation API (more reliable than
/// Geolocator alone on Flutter web).
Future<Position?> browserGeolocation({
  Duration timeout = const Duration(seconds: 25),
}) async {
  final completer = Completer<Position?>();
  Timer? watchdog;

  void finish(Position? value, [Object? error]) {
    if (completer.isCompleted) return;
    watchdog?.cancel();
    if (error != null) {
      completer.completeError(error);
    } else {
      completer.complete(value);
    }
  }

  watchdog = Timer(timeout, () {
    finish(null, TimeoutException('Browser geolocation timed out'));
  });

  try {
    final geo = web.window.navigator.geolocation;
    geo.getCurrentPosition(
      (web.GeolocationPosition pos) {
        final coords = pos.coords;
        finish(
          Position(
            longitude: coords.longitude.toDouble(),
            latitude: coords.latitude.toDouble(),
            timestamp: DateTime.now(),
            accuracy: coords.accuracy.toDouble(),
            altitude: coords.altitude?.toDouble() ?? 0,
            altitudeAccuracy: coords.altitudeAccuracy?.toDouble() ?? 0,
            heading: coords.heading?.toDouble() ?? 0,
            headingAccuracy: 0,
            speed: coords.speed?.toDouble() ?? 0,
            speedAccuracy: 0,
          ),
        );
      }.toJS,
      (web.GeolocationPositionError error) {
        finish(null, StateError(error.message));
      }.toJS,
      web.PositionOptions(
        enableHighAccuracy: false,
        timeout: timeout.inMilliseconds,
        maximumAge: 120000,
      ),
    );
  } catch (e) {
    finish(null, e);
  }

  return completer.future;
}

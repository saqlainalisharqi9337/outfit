import 'package:geolocator/geolocator.dart';

/// Non-web stub — browser GPS is unused.
Future<Position?> browserGeolocation({
  Duration timeout = const Duration(seconds: 25),
}) async {
  return null;
}

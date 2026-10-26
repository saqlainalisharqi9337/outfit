import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../providers/auth_provider.dart';
import '../providers/recommendation_provider.dart';
import '../providers/wardrobe_provider.dart';
import '../providers/weather_provider.dart';
import '../screens/weather/weather_location_screen.dart';
import '../theme/app_theme.dart';
import 'exceptions.dart';

Future<void> refreshWeatherAndLooks(BuildContext context) async {
  final user = context.read<AuthProvider>().profile;
  final weather = context.read<WeatherProvider>();
  if (user == null) return;
  await weather.loadForProfile(user, force: true);
  if (!context.mounted || weather.weather == null) return;
  await context.read<RecommendationProvider>().generate(
        user: user,
        wardrobe: context.read<WardrobeProvider>().items,
        weather: weather.weather!,
        refresh: true,
      );
}

void openLocationPicker(BuildContext context) {
  Navigator.push(
    context,
    MaterialPageRoute(builder: (_) => const WeatherLocationScreen()),
  );
}

/// Choose live GPS **or** manual country → city.
Future<void> showLocationChoices(
  BuildContext context, {
  required Future<void> Function() onLiveLocation,
}) async {
  final choice = await showModalBottomSheet<String>(
    context: context,
    showDragHandle: true,
    builder: (ctx) {
      return SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(16, 0, 16, 24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const Text(
                'Set weather location',
                style: TextStyle(fontWeight: FontWeight.w700, fontSize: 16),
              ),
              const SizedBox(height: 4),
              const Text(
                'Use GPS for live weather, or pick a country and city yourself.',
                style: TextStyle(color: AppColors.muted, height: 1.35),
              ),
              const SizedBox(height: 12),
              ListTile(
                leading:
                    const Icon(Icons.my_location, color: AppColors.primary),
                title: const Text('Use live location'),
                subtitle: const Text('Ask the browser/device for GPS'),
                onTap: () => Navigator.pop(ctx, 'live'),
              ),
              ListTile(
                leading: const Icon(Icons.public, color: AppColors.primary),
                title: const Text('Choose country & city'),
                subtitle: const Text('Manual search for any place'),
                onTap: () => Navigator.pop(ctx, 'manual'),
              ),
            ],
          ),
        ),
      );
    },
  );
  if (!context.mounted || choice == null) return;
  if (choice == 'manual') {
    openLocationPicker(context);
    return;
  }
  await onLiveLocation();
}

Future<bool> applyDeviceLocation(BuildContext context) async {
  final auth = context.read<AuthProvider>();
  final weather = context.read<WeatherProvider>();
  final user = auth.profile;
  if (user == null) return false;
  final city = await weather.fromDevice();
  if (!context.mounted) return false;
  await weather.loadForCity(city, force: true);
  if (!context.mounted) return false;
  final updated = user.copyWith(
    country: city.country,
    countryCode: city.countryCode,
    city: city.name,
    latitude: city.latitude,
    longitude: city.longitude,
  );
  await auth.saveProfile(updated);
  if (!context.mounted || weather.weather == null) return true;
  await context.read<RecommendationProvider>().generate(
        user: updated,
        wardrobe: context.read<WardrobeProvider>().items,
        weather: weather.weather!,
        refresh: true,
      );
  return true;
}

Future<void> promptAndApplyLiveLocation(BuildContext context) async {
  try {
    await applyDeviceLocation(context);
    if (!context.mounted) return;
    final w = context.read<WeatherProvider>().weather;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
          w == null
              ? 'Location saved.'
              : 'Live weather for ${w.city}, ${w.country}: ${w.temperature.round()}°C',
        ),
      ),
    );
  } on AppException catch (e) {
    if (!context.mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(e.message)),
    );
    openLocationPicker(context);
  } catch (_) {
    if (!context.mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text(
          'Could not read live location. Pick a country and city instead.',
        ),
      ),
    );
    openLocationPicker(context);
  }
}

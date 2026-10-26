import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../providers/auth_provider.dart';
import '../../providers/recommendation_provider.dart';
import '../../providers/wardrobe_provider.dart';
import '../../providers/weather_provider.dart';
import '../../models/weather_model.dart';
import '../../theme/app_theme.dart';
import '../../utils/exceptions.dart';
import '../../widgets/common.dart';
import '../../widgets/weather_card.dart';

class WeatherLocationScreen extends StatefulWidget {
  const WeatherLocationScreen({super.key});

  @override
  State<WeatherLocationScreen> createState() => _WeatherLocationScreenState();
}

class _WeatherLocationScreenState extends State<WeatherLocationScreen> {
  CountryOption? _country;
  final _cityQuery = TextEditingController();
  bool _locating = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) async {
      final weather = context.read<WeatherProvider>();
      await weather.loadCountries();
      if (!mounted) return;
      _syncCountryFromProfile();
    });
  }

  @override
  void dispose() {
    _cityQuery.dispose();
    super.dispose();
  }

  void _syncCountryFromProfile() {
    final user = context.read<AuthProvider>().profile;
    final countries = context.read<WeatherProvider>().countries;
    if (user?.countryCode == null || countries.isEmpty) return;
    final match = countries.where(
      (c) => c.code.toUpperCase() == user!.countryCode!.toUpperCase(),
    );
    if (match.isEmpty) return;
    setState(() => _country = match.first);
  }

  void _hideCityNames() {
    _cityQuery.clear();
    context.read<WeatherProvider>().clearCityResults();
    FocusManager.instance.primaryFocus?.unfocus();
  }

  Future<void> _apply(GeoCity city) async {
    _hideCityNames();
    final auth = context.read<AuthProvider>();
    final user = auth.profile;
    if (user == null) return;
    setState(() {
      if (city.countryCode.isNotEmpty) {
        final match = context.read<WeatherProvider>().countries.where(
              (c) => c.code.toUpperCase() == city.countryCode.toUpperCase(),
            );
        if (match.isNotEmpty) _country = match.first;
      }
    });
    await context.read<WeatherProvider>().loadForCity(city, force: true);
    if (!mounted) return;
    final updated = user.copyWith(
      country: city.country,
      countryCode: city.countryCode,
      city: city.name,
      latitude: city.latitude,
      longitude: city.longitude,
    );
    await auth.saveProfile(updated);
    if (!mounted) return;
    final weather = context.read<WeatherProvider>().weather;
    if (weather != null) {
      await context.read<RecommendationProvider>().generate(
            user: updated,
            wardrobe: context.read<WardrobeProvider>().items,
            weather: weather,
          );
    }
  }

  @override
  Widget build(BuildContext context) {
    final weather = context.watch<WeatherProvider>();
    return Scaffold(
      appBar: AppBar(title: const Text('Weather & location')),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          if (weather.weather != null)
            WeatherCard(
              weather: weather.weather!,
              locating: _locating,
              onRefresh: () {
                final user = context.read<AuthProvider>().profile;
                if (user != null) {
                  weather.loadForProfile(user, force: true);
                }
              },
              onUseLiveLocation: _locating
                  ? null
                  : () async {
                      setState(() => _locating = true);
                      try {
                        final city = await weather.fromDevice();
                        if (!mounted) return;
                        await _apply(city);
                        if (!mounted) return;
                        ScaffoldMessenger.of(context).showSnackBar(
                          SnackBar(
                            content: Text(
                              'Live weather for ${city.name}, ${city.country}',
                            ),
                          ),
                        );
                      } on AppException catch (e) {
                        if (mounted) {
                          ScaffoldMessenger.of(context).showSnackBar(
                            SnackBar(content: Text(e.message)),
                          );
                        }
                      } finally {
                        if (mounted) setState(() => _locating = false);
                      }
                    },
              onPickLocation: () {
                // Already on this screen — scroll focus to country field.
                FocusScope.of(context).unfocus();
              },
            ),
          if (weather.loading) const LoadingView(message: 'Loading live weather…'),
          if (weather.error != null)
            ErrorView(
              message: weather.error!,
              onRetry: () {
                final user = context.read<AuthProvider>().profile;
                if (user != null) {
                  weather.loadForProfile(user, force: true);
                }
              },
            ),
          const SizedBox(height: 16),
          FilledButton.tonal(
            onPressed: _locating
                ? null
                : () async {
                    setState(() => _locating = true);
                    try {
                      final city = await weather.fromDevice();
                      if (!mounted) return;
                      await _apply(city);
                      if (!mounted) return;
                      ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(
                          content: Text(
                            'Live weather for ${city.name}, ${city.country}',
                          ),
                        ),
                      );
                    } on AppException catch (e) {
                      if (mounted) {
                        ScaffoldMessenger.of(context).showSnackBar(
                          SnackBar(content: Text(e.message)),
                        );
                      }
                    } finally {
                      if (mounted) setState(() => _locating = false);
                    }
                  },
            child: Text(
              _locating
                  ? 'Reading live location…'
                  : 'Use live GPS location',
            ),
          ),
          const SizedBox(height: 8),
          const Text(
            'Or select a country, then search a city in that country.',
            style: TextStyle(color: AppColors.muted),
          ),
          const SizedBox(height: 12),
          DropdownButtonFormField<CountryOption>(
            key: ValueKey(_country?.code),
            initialValue: _country,
            isExpanded: true,
            decoration: const InputDecoration(labelText: 'Country'),
            items: [
              for (final c in weather.countries)
                DropdownMenuItem(value: c, child: Text(c.name)),
            ],
            onChanged: (c) {
              setState(() => _country = c);
              _hideCityNames();
            },
          ),
          const SizedBox(height: 8),
          TextField(
            controller: _cityQuery,
            enabled: _country != null,
            decoration: const InputDecoration(
              labelText: 'Search city (filtered by country)',
              hintText: 'Type at least 2 letters',
            ),
            onChanged: (q) {
              if (_country != null) weather.searchCities(q, _country!.code);
            },
          ),
          if (weather.weather != null)
            Padding(
              padding: const EdgeInsets.only(top: 12),
              child: Text(
                'Selected: ${weather.weather!.city}',
                style: const TextStyle(fontWeight: FontWeight.w600),
              ),
            ),
          if (weather.cityResults.isEmpty &&
              _country != null &&
              _cityQuery.text.isEmpty)
            const Padding(
              padding: EdgeInsets.only(top: 12),
              child: Text(
                'Type at least 2 letters. Cities come from Open-Meteo for the selected country.',
                style: TextStyle(color: AppColors.muted),
              ),
            ),
          ...weather.cityResults.map(
            (c) => ListTile(
              title: Text(c.displayName),
              subtitle: Text(c.country),
              onTap: () => _apply(c),
            ),
          ),
        ],
      ),
    );
  }
}

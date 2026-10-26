import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../models/weather_model.dart';
import '../../providers/auth_provider.dart';
import '../../providers/weather_provider.dart';
import '../../services/storage_service.dart';
import '../../theme/app_theme.dart';
import '../../utils/clothing_catalog.dart';
import '../../utils/enums.dart';
import '../../utils/exceptions.dart';
import '../../utils/photo_picker.dart';
import '../../widgets/skin_tone_picker.dart';

class ProfileSetupScreen extends StatefulWidget {
  const ProfileSetupScreen({super.key});

  @override
  State<ProfileSetupScreen> createState() => _ProfileSetupScreenState();
}

class _ProfileSetupScreenState extends State<ProfileSetupScreen> {
  final _page = PageController();
  int _index = 0;
  bool _busy = false;
  bool _locating = false;
  String? _error;

  Gender? _gender;
  BodyType? _bodyType;
  Culture? _culture;
  bool _modest = false;
  bool _overrideCulture = false;
  SkinTone? _skinTone;
  final _favoriteColors = <String>{};
  final _styles = <String>{};
  final _occasions = <Occasion>{Occasion.casualDayOut};
  CountryOption? _country;
  GeoCity? _city;
  final _cityQuery = TextEditingController();
  Uint8List? _avatarBytes;
  String? _skinMessage;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<WeatherProvider>().loadCountries();
    });
  }

  @override
  void dispose() {
    _page.dispose();
    _cityQuery.dispose();
    super.dispose();
  }

  void _hideCityNames() {
    _cityQuery.clear();
    context.read<WeatherProvider>().clearCityResults();
    FocusManager.instance.primaryFocus?.unfocus();
  }

  Future<void> _next() async {
    if (_index == 4) {
      await _save();
      return;
    }
    await _page.nextPage(
      duration: const Duration(milliseconds: 280),
      curve: Curves.easeOut,
    );
  }

  Future<void> _pickAvatar() async {
    final bytes = await PhotoPicker.pickWithSheet(context, selfie: true);
    if (bytes == null) return;
    setState(() => _avatarBytes = bytes);
  }

  Future<void> _save() async {
    final auth = context.read<AuthProvider>();
    final existing = auth.profile;
    if (existing == null) return;
    if (_gender == null ||
        _culture == null ||
        _skinTone == null ||
        _country == null ||
        _city == null) {
      setState(() => _error = 'Please complete every step before continuing.');
      return;
    }
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      var imageUrl = existing.profileImageUrl;
      if (_avatarBytes != null) {
        imageUrl = await context.read<StorageService>().uploadProfileImage(
              uid: existing.id,
              bytes: _avatarBytes!,
            );
      }
      final updated = existing.copyWith(
        profileImageUrl: imageUrl,
        gender: _gender,
        bodyType: _bodyType,
        culture: _culture,
        skinTone: _skinTone,
        country: _country!.name,
        countryCode: _country!.code,
        city: _city!.name,
        latitude: _city!.latitude,
        longitude: _city!.longitude,
        onboardingComplete: true,
        preferences: existing.preferences.copyWith(
          modestPreference: _modest,
          overrideCultureDefaults: _overrideCulture,
          favoriteColors: _favoriteColors.toList(),
          preferredStyles: _styles.toList(),
          preferredOccasions: _occasions.toList(),
        ),
      );
      await auth.saveProfile(updated);
    } on AppException catch (e) {
      setState(() => _error = e.message);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final weather = context.watch<WeatherProvider>();
    return Scaffold(
      appBar: AppBar(
        title: Text('Profile setup  ${_index + 1}/5'),
      ),
      body: Column(
        children: [
          LinearProgressIndicator(value: (_index + 1) / 5),
          if (_error != null)
            Padding(
              padding: const EdgeInsets.all(12),
              child: Text(_error!, style: const TextStyle(color: AppColors.danger)),
            ),
          Expanded(
            child: PageView(
              controller: _page,
              physics: const NeverScrollableScrollPhysics(),
              onPageChanged: (i) => setState(() => _index = i),
              children: [
                _genderStep(),
                _cultureStep(),
                _skinStep(),
                _prefsStep(),
                _locationStep(weather),
              ],
            ),
          ),
          Padding(
            padding: const EdgeInsets.all(16),
            child: Row(
              children: [
                if (_index > 0)
                  Expanded(
                    child: OutlinedButton(
                      onPressed: () => _page.previousPage(
                        duration: const Duration(milliseconds: 280),
                        curve: Curves.easeOut,
                      ),
                      child: const Text('Back'),
                    ),
                  ),
                if (_index > 0) const SizedBox(width: 12),
                Expanded(
                  child: FilledButton(
                    onPressed: _busy ? null : _next,
                    child: Text(_index == 4 ? 'Finish' : 'Continue'),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _genderStep() {
    return ListView(
      padding: const EdgeInsets.all(20),
      children: [
        const Text('Tell us about you'),
        const SizedBox(height: 12),
        OutlinedButton.icon(
          onPressed: _pickAvatar,
          icon: const Icon(Icons.photo_camera_front_outlined),
          label: Text(_avatarBytes == null ? 'Add profile photo' : 'Change photo'),
        ),
        const SizedBox(height: 16),
        for (final g in Gender.values)
          RadioListTile<Gender>(
            title: Text(g.label),
            value: g,
            groupValue: _gender,
            onChanged: (v) => setState(() => _gender = v),
          ),
        const SizedBox(height: 8),
        const Text('Body type (used in outfit scoring)'),
        const SizedBox(height: 4),
        for (final b in BodyType.values)
          RadioListTile<BodyType>(
            title: Text(b.label),
            subtitle: Text(b.hint),
            value: b,
            groupValue: _bodyType,
            onChanged: (v) => setState(() => _bodyType = v),
          ),
      ],
    );
  }

  Widget _cultureStep() {
    return ListView(
      padding: const EdgeInsets.all(20),
      children: [
        const Text(
          'Culture influences recommended silhouettes. You can override this later.',
        ),
        const SizedBox(height: 8),
        for (final c in Culture.values)
          RadioListTile<Culture>(
            title: Text(c.label),
            value: c,
            groupValue: _culture,
            onChanged: (v) => setState(() => _culture = v),
          ),
        SwitchListTile(
          title: const Text('Prefer modest / conservative clothing'),
          value: _modest,
          onChanged: (v) => setState(() => _modest = v),
        ),
        SwitchListTile(
          title: const Text('Override cultural clothing defaults'),
          subtitle: const Text(
            'Use only the styles you pick on the next screens.',
          ),
          value: _overrideCulture,
          onChanged: (v) => setState(() => _overrideCulture = v),
        ),
      ],
    );
  }

  Widget _skinStep() {
    return ListView(
      padding: const EdgeInsets.all(20),
      children: [
        SkinTonePicker(
          value: _skinTone,
          busy: _busy,
          message: _skinMessage,
          onChanged: (tone) => setState(() => _skinTone = tone),
          onBusy: (v) => setState(() => _busy = v),
          onMessage: (v) => setState(() => _skinMessage = v),
        ),
      ],
    );
  }

  Widget _prefsStep() {
    return ListView(
      padding: const EdgeInsets.all(20),
      children: [
        const Text('Favorite colors'),
        Wrap(
          spacing: 8,
          children: [
            for (final c in ClothingCatalog.colors)
              FilterChip(
                label: Text(c),
                selected: _favoriteColors.contains(c),
                onSelected: (v) => setState(() {
                  if (v) {
                    _favoriteColors.add(c);
                  } else {
                    _favoriteColors.remove(c);
                  }
                }),
              ),
          ],
        ),
        const SizedBox(height: 16),
        const Text('Preferred styles / item types'),
        Wrap(
          spacing: 8,
          children: [
            for (final s in ClothingCatalog.styles)
              FilterChip(
                label: Text(s),
                selected: _styles.contains(s),
                onSelected: (v) => setState(() {
                  if (v) {
                    _styles.add(s);
                  } else {
                    _styles.remove(s);
                  }
                }),
              ),
          ],
        ),
        const SizedBox(height: 16),
        const Text('Preferred occasions'),
        Wrap(
          spacing: 8,
          children: [
            for (final o in Occasion.values)
              FilterChip(
                label: Text(o.label),
                selected: _occasions.contains(o),
                onSelected: (v) => setState(() {
                  if (v) {
                    _occasions.add(o);
                  } else {
                    _occasions.remove(o);
                  }
                }),
              ),
          ],
        ),
      ],
    );
  }

  Widget _locationStep(WeatherProvider weather) {
    return ListView(
      padding: const EdgeInsets.all(20),
      children: [
        const Text('Weather uses the city you select, not a fake forecast.'),
        const SizedBox(height: 12),
        DropdownButtonFormField<CountryOption>(
          key: ValueKey(_country?.code),
          initialValue: _country,
          isExpanded: true,
          decoration: const InputDecoration(labelText: 'Country'),
          items: weather.countries
              .map(
                (c) => DropdownMenuItem(value: c, child: Text(c.name)),
              )
              .toList(),
          onChanged: (c) {
            setState(() {
              _country = c;
              _city = null;
            });
            _hideCityNames();
          },
        ),
        const SizedBox(height: 12),
        TextField(
          controller: _cityQuery,
          enabled: _country != null,
          decoration: const InputDecoration(
            labelText: 'Search city in selected country',
          ),
          onChanged: (q) {
            if (_country != null) {
              weather.searchCities(q, _country!.code);
            }
          },
        ),
        const SizedBox(height: 8),
        FilledButton.tonal(
          onPressed: _locating
              ? null
              : () async {
                  setState(() {
                    _locating = true;
                    _error = null;
                  });
                  try {
                    final city = await weather.fromDevice();
                    if (!mounted) return;
                    setState(() {
                      _city = city;
                      if (city.countryCode.isNotEmpty) {
                        final match = weather.countries.where(
                          (c) =>
                              c.code.toUpperCase() ==
                              city.countryCode.toUpperCase(),
                        );
                        if (match.isNotEmpty) _country = match.first;
                      }
                    });
                    _hideCityNames();
                  } on AppException catch (e) {
                    setState(() => _error = e.message);
                  } finally {
                    if (mounted) setState(() => _locating = false);
                  }
                },
          child: Text(
            _locating
                ? 'Reading live location…'
                : 'Use current device location',
          ),
        ),
        if (weather.error != null)
          Padding(
            padding: const EdgeInsets.only(top: 8),
            child: Text(weather.error!, style: const TextStyle(color: AppColors.danger)),
          ),
        if (_city != null)
          Padding(
            padding: const EdgeInsets.only(top: 8),
            child: Text('Selected: ${_city!.displayName}'),
          ),
        ...weather.cityResults.map(
          (c) => ListTile(
            title: Text(c.displayName),
            subtitle: Text(c.country),
            onTap: () {
              setState(() => _city = c);
              _hideCityNames();
            },
          ),
        ),
      ],
    );
  }
}

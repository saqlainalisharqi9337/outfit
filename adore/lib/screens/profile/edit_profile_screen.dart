import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../providers/auth_provider.dart';
import '../../theme/app_theme.dart';
import '../../utils/clothing_catalog.dart';
import '../../utils/enums.dart';
import '../../widgets/skin_tone_picker.dart';

class EditProfileScreen extends StatefulWidget {
  const EditProfileScreen({super.key});

  @override
  State<EditProfileScreen> createState() => _EditProfileScreenState();
}

class _EditProfileScreenState extends State<EditProfileScreen> {
  late Set<String> _colors;
  late Set<String> _excluded;
  late bool _modest;
  late bool _override;
  late Culture? _culture;
  late BodyType? _body;
  late SkinTone? _skin;
  bool _skinBusy = false;
  String? _skinMessage;

  @override
  void initState() {
    super.initState();
    final user = context.read<AuthProvider>().profile!;
    _colors = {...user.preferences.favoriteColors};
    _excluded = {...user.preferences.excludedItemTypes};
    _modest = user.preferences.modestPreference;
    _override = user.preferences.overrideCultureDefaults;
    _culture = user.culture;
    _body = user.bodyType;
    _skin = user.skinTone;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Preferences')),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          DropdownButtonFormField<Culture>(
            initialValue: _culture,
            decoration: const InputDecoration(labelText: 'Culture'),
            items: [
              for (final c in Culture.values)
                DropdownMenuItem(value: c, child: Text(c.label)),
            ],
            onChanged: (v) => setState(() => _culture = v),
          ),
          const SizedBox(height: 16),
          DropdownButtonFormField<BodyType>(
            initialValue: _body,
            decoration: const InputDecoration(labelText: 'Body type'),
            items: [
              for (final b in BodyType.values)
                DropdownMenuItem(value: b, child: Text(b.label)),
            ],
            onChanged: (v) => setState(() => _body = v),
          ),
          if (_body != null)
            Padding(
              padding: const EdgeInsets.only(top: 8, bottom: 8),
              child: Text(
                _body!.hint,
                style: const TextStyle(color: AppColors.muted),
              ),
            ),
          const SizedBox(height: 16),
          SkinTonePicker(
            value: _skin,
            busy: _skinBusy,
            message: _skinMessage,
            onChanged: (tone) => setState(() => _skin = tone),
            onBusy: (v) => setState(() => _skinBusy = v),
            onMessage: (v) => setState(() => _skinMessage = v),
          ),
          SwitchListTile(
            title: const Text('Modest clothing preference'),
            value: _modest,
            onChanged: (v) => setState(() => _modest = v),
          ),
          SwitchListTile(
            title: const Text('Override cultural defaults'),
            value: _override,
            onChanged: (v) => setState(() => _override = v),
          ),
          const Text('Favorite colors'),
          Wrap(
            spacing: 8,
            children: [
              for (final c in ClothingCatalog.colors)
                FilterChip(
                  label: Text(c),
                  selected: _colors.contains(c),
                  onSelected: (v) => setState(() {
                    if (v) {
                      _colors.add(c);
                    } else {
                      _colors.remove(c);
                    }
                  }),
                ),
            ],
          ),
          const SizedBox(height: 12),
          const Text('Excluded item types (hard filter)'),
          Wrap(
            spacing: 8,
            children: [
              for (final s in ClothingCatalog.subcategories.values.expand((e) => e))
                FilterChip(
                  label: Text(s),
                  selected: _excluded.contains(s),
                  onSelected: (v) => setState(() {
                    if (v) {
                      _excluded.add(s);
                    } else {
                      _excluded.remove(s);
                    }
                  }),
                ),
            ],
          ),
          const SizedBox(height: 16),
          FilledButton(
            onPressed: () async {
              final auth = context.read<AuthProvider>();
              final user = auth.profile!;
              await auth.saveProfile(
                user.copyWith(
                  culture: _culture,
                  bodyType: _body,
                  skinTone: _skin,
                  preferences: user.preferences.copyWith(
                    favoriteColors: _colors.toList(),
                    excludedItemTypes: _excluded.toList(),
                    modestPreference: _modest,
                    overrideCultureDefaults: _override,
                  ),
                ),
              );
              if (context.mounted) Navigator.pop(context);
            },
            child: const Text('Save preferences'),
          ),
        ],
      ),
    );
  }
}

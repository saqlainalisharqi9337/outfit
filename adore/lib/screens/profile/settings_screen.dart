import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../providers/auth_provider.dart';
import '../../theme/app_theme.dart';
import '../../widgets/motion.dart';

class SettingsScreen extends StatelessWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthProvider>();
    final user = auth.profile;
    return Scaffold(
      appBar: AppBar(title: const Text('Settings')),
      body: SoftBackdrop(
        child: ListView(
        children: [
          SwitchListTile(
            title: const Text('Notifications'),
            subtitle: const Text('Preference only — no push provider is configured.'),
            value: user?.notificationsEnabled ?? true,
            onChanged: user == null
                ? null
                : (v) => auth.saveProfile(user.copyWith(notificationsEnabled: v)),
          ),
          const ListTile(
            title: Text('Account'),
            subtitle: Text('Email/password is managed by Supabase Authentication.'),
          ),
          const Padding(
            padding: EdgeInsets.all(16),
            child: Text(
              'Weather keys are not stored in the app. Open-Meteo is used directly. '
              'The clothing AI URL is set with --dart-define=ML_SERVICE_URL=...',
              style: TextStyle(color: AppColors.muted),
            ),
          ),
          ListTile(
            title: const Text('Log out'),
            leading: const Icon(Icons.logout, color: AppColors.danger),
            onTap: () {
              Navigator.popUntil(context, (r) => r.isFirst);
              auth.logout();
            },
          ),
        ],
      ),
      ),
    );
  }
}

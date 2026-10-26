import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../config/supabase_config.dart';
import '../../theme/app_theme.dart';

/// Shown only when Supabase.initialize fails. Tables themselves are applied
/// via SQL in the dashboard — see SUPABASE_SETUP.md.
class BackendSetupScreen extends StatelessWidget {
  const BackendSetupScreen({super.key});

  static const _sqlHint = 'supabase/SETUP_ALL.sql';

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: ListView(
            children: [
              Text(
                'Connect Adore to Supabase',
                style: GoogleFonts.playfairDisplay(fontSize: 28),
              ),
              const SizedBox(height: 12),
              const Text(
                'The app is already coded to save profile, body type, pattern, '
                'and wardrobe to your Supabase project. You only need to create '
                'the database tables once.',
              ),
              const SizedBox(height: 20),
              Text('Project', style: Theme.of(context).textTheme.titleMedium),
              SelectableText(SupabaseConfig.url),
              const SizedBox(height: 16),
              Text('Steps', style: Theme.of(context).textTheme.titleMedium),
              const SizedBox(height: 8),
              const Text(
                '1. Open https://supabase.com/dashboard → your project '
                'jpjxjggxheafpyyxpftx',
              ),
              const Text('2. Go to SQL Editor → New query'),
              Text('3. Paste the full contents of $_sqlHint and click Run'),
              const Text(
                '4. Auth → Providers → Email: turn OFF “Confirm email” for FYP demos',
              ),
              const Text(
                '5. Restart the Flutter app, tap Register (not Local Demo), '
                'complete onboarding including body type',
              ),
              const Text(
                '6. Add a clothing item and set Pattern — both should appear '
                'in Table Editor → profiles / wardrobe_items',
              ),
              const SizedBox(height: 16),
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: AppColors.cardBorder.withValues(alpha: 0.35),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: const Text(
                  'Important: “Local Demo” / ayesha@adore.test stores data only '
                  'in memory. Use Register with a real email so body type, '
                  'pattern, and wardrobe are written to Supabase.',
                ),
              ),
              const SizedBox(height: 20),
              FilledButton.icon(
                onPressed: () async {
                  await Clipboard.setData(
                    const ClipboardData(text: SupabaseConfig.url),
                  );
                  if (context.mounted) {
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(content: Text('Project URL copied')),
                    );
                  }
                },
                icon: const Icon(Icons.copy),
                label: const Text('Copy project URL'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

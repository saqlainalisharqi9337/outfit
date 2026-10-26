import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../config/demo_account.dart';
import '../../providers/auth_provider.dart';
import '../../theme/app_theme.dart';
import '../../utils/exceptions.dart';
import '../../widgets/common.dart';
import 'forgot_password_screen.dart';
import 'register_screen.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  static const route = '/login';

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _form = GlobalKey<FormState>();
  final _email = TextEditingController();
  final _password = TextEditingController();
  bool _busy = false;
  bool _showSignIn = false;
  String? _error;

  @override
  void dispose() {
    _email.dispose();
    _password.dispose();
    super.dispose();
  }

  Future<void> _submit({bool demo = false}) async {
    if (!demo && !_form.currentState!.validate()) return;
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final auth = context.read<AuthProvider>();
      if (demo) {
        await auth.loginDemo();
      } else {
        await auth.login(
          email: _email.text,
          password: _password.text,
        );
      }
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e is AppException
            ? e.message
            : 'Could not log in. ${e.toString()}';
      });
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Theme.of(context).scaffoldBackgroundColor,
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(24),
          children: [
            if (_showSignIn)
              Align(
                alignment: Alignment.centerLeft,
                child: TextButton.icon(
                  onPressed: _busy ? null : () => setState(() => _showSignIn = false),
                  icon: const Icon(Icons.arrow_back),
                  label: const Text('Back'),
                ),
              ),
            DecoratedBox(
              decoration: BoxDecoration(
                color: Theme.of(context).colorScheme.surface,
                borderRadius: BorderRadius.circular(40),
                border: Border.all(color: AppColors.cardBorder),
                boxShadow: AppShadows.lift,
              ),
              child: Padding(
                padding: const EdgeInsets.all(28),
                child: _showSignIn ? _signInForm(context) : _welcome(context),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _welcome(BuildContext context) {
    return Column(
      children: [
        Container(
          height: 160,
          width: double.infinity,
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(24),
            gradient: const LinearGradient(
              colors: [Color(0x26E8395A), Color(0x267C6AF5)],
            ),
          ),
          child: const Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Text('👗', style: TextStyle(fontSize: 36)),
              SizedBox(width: 18),
              Text('🧢', style: TextStyle(fontSize: 48)),
              SizedBox(width: 18),
              Text('👠', style: TextStyle(fontSize: 36)),
            ],
          ),
        ),
        const SizedBox(height: 20),
        Text(
          'Find the Perfect',
          textAlign: TextAlign.center,
          style: Theme.of(context).textTheme.headlineMedium,
        ),
        const Text(
          'Outfit, Every Day.',
          textAlign: TextAlign.center,
          style: TextStyle(
            fontSize: 28,
            fontWeight: FontWeight.w700,
            color: AppColors.primary,
          ),
        ),
        const SizedBox(height: 18),
        const _FeatureRow(icon: Icons.cloud_outlined, color: AppColors.primary, text: 'Weather-based outfit suggestions'),
        const SizedBox(height: 10),
        const _FeatureRow(icon: Icons.person_outline, color: AppColors.secondary, text: 'Personalized style for you'),
        const SizedBox(height: 10),
        const _FeatureRow(icon: Icons.auto_awesome_outlined, color: AppColors.accent, text: 'Smart style tips & insights'),
        const SizedBox(height: 22),
        SizedBox(
          width: double.infinity,
          child: DecoratedBox(
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(40),
              gradient: const LinearGradient(colors: [AppColors.primary, AppColors.secondary]),
            ),
            child: TextButton(
              onPressed: () => Navigator.pushNamed(context, RegisterScreen.route),
              style: TextButton.styleFrom(
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(vertical: 16),
              ),
              child: const Text('Create Account', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600)),
            ),
          ),
        ),
        const SizedBox(height: 10),
        SizedBox(
          width: double.infinity,
          child: OutlinedButton(
            onPressed: () => setState(() => _showSignIn = true),
            style: OutlinedButton.styleFrom(
              padding: const EdgeInsets.symmetric(vertical: 16),
              shape: const StadiumBorder(),
            ),
            child: const Text('Sign In'),
          ),
        ),
        TextButton(
          onPressed: _busy ? null : () => _submit(demo: true),
          child: const Text('Continue as guest →'),
        ),
      ],
    );
  }

  Widget _signInForm(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text('Sign in', style: Theme.of(context).textTheme.headlineMedium),
        const SizedBox(height: 6),
        const Text(
          'Your wardrobe, weather, and outfits stay on your account.',
          style: TextStyle(color: AppColors.muted),
        ),
        const SizedBox(height: 18),
        Form(
          key: _form,
          child: Column(
            children: [
              TextFormField(
                controller: _email,
                keyboardType: TextInputType.emailAddress,
                decoration: const InputDecoration(labelText: 'Email'),
                validator: (v) => v != null && v.contains('@') ? null : 'Enter a valid email',
              ),
              const SizedBox(height: 12),
              TextFormField(
                controller: _password,
                obscureText: true,
                decoration: const InputDecoration(labelText: 'Password'),
                validator: (v) => v != null && v.length >= 6 ? null : 'Minimum 6 characters',
              ),
            ],
          ),
        ),
        Align(
          alignment: Alignment.centerRight,
          child: TextButton(
            onPressed: () => Navigator.pushNamed(context, ForgotPasswordScreen.route),
            child: const Text('Forgot password?'),
          ),
        ),
        if (_error != null) ...[
          StatusBanner(message: _error!),
          const SizedBox(height: 12),
        ],
        FilledButton(
          onPressed: _busy ? null : () => _submit(),
          child: _busy
              ? const SizedBox(
                  height: 18,
                  width: 18,
                  child: CircularProgressIndicator(strokeWidth: 2, color: AppColors.onPrimary),
                )
              : const Text('Sign In'),
        ),
        const SizedBox(height: 8),
        Text(
          'Guest demo: ${DemoAccount.email}',
          textAlign: TextAlign.center,
          style: const TextStyle(color: AppColors.muted, fontSize: 12),
        ),
      ],
    );
  }
}

class _FeatureRow extends StatelessWidget {
  const _FeatureRow({required this.icon, required this.color, required this.text});

  final IconData icon;
  final Color color;
  final String text;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        CircleAvatar(
          radius: 18,
          backgroundColor: color.withValues(alpha: 0.12),
          child: Icon(icon, color: color, size: 18),
        ),
        const SizedBox(width: 12),
        Expanded(child: Text(text, style: const TextStyle(fontWeight: FontWeight.w500))),
      ],
    );
  }
}

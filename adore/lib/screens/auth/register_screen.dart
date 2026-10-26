import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../config/demo_account.dart';
import '../../providers/auth_provider.dart';
import '../../theme/app_theme.dart';
import '../../utils/exceptions.dart';
import '../../widgets/common.dart';
import '../../widgets/motion.dart';

class RegisterScreen extends StatefulWidget {
  const RegisterScreen({super.key});

  static const route = '/register';

  @override
  State<RegisterScreen> createState() => _RegisterScreenState();
}

class _RegisterScreenState extends State<RegisterScreen> {
  final _form = GlobalKey<FormState>();
  final _name = TextEditingController();
  final _email = TextEditingController();
  final _password = TextEditingController();
  final _confirm = TextEditingController();
  bool _busy = false;
  String? _error;

  @override
  void dispose() {
    _name.dispose();
    _email.dispose();
    _password.dispose();
    _confirm.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_form.currentState!.validate()) return;
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await context.read<AuthProvider>().register(
            name: _name.text,
            email: _email.text,
            password: _password.text,
          );
      if (mounted) Navigator.pop(context);
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e is AppException
            ? e.message
            : 'Could not create the account. ${e.toString()}';
      });
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Create account')),
      body: SoftBackdrop(
        child: ListView(
        padding: const EdgeInsets.all(24),
        children: [
          Form(
            key: _form,
            child: Column(
              children: [
                TextFormField(
                  controller: _name,
                  decoration: const InputDecoration(labelText: 'Name'),
                  validator: (v) =>
                      v != null && v.trim().length >= 2 ? null : 'Enter your name',
                ),
                const SizedBox(height: 12),
                TextFormField(
                  controller: _email,
                  keyboardType: TextInputType.emailAddress,
                  decoration: const InputDecoration(labelText: 'Email'),
                  validator: (v) =>
                      v != null && v.contains('@') ? null : 'Enter a valid email',
                ),
                const SizedBox(height: 12),
                TextFormField(
                  controller: _password,
                  obscureText: true,
                  decoration: const InputDecoration(labelText: 'Password'),
                  validator: (v) =>
                      v != null && v.length >= 6 ? null : 'Minimum 6 characters',
                ),
                const SizedBox(height: 12),
                TextFormField(
                  controller: _confirm,
                  obscureText: true,
                  decoration:
                      const InputDecoration(labelText: 'Confirm password'),
                  validator: (v) =>
                      v == _password.text ? null : 'Passwords do not match',
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          if (_error != null)
            Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: StatusBanner(message: _error!),
            ),
          FilledButton(
            onPressed: _busy ? null : _submit,
            child: _busy
                ? const SizedBox(
                    height: 18,
                    width: 18,
                    child: CircularProgressIndicator(
                      strokeWidth: 2,
                      color: AppColors.onPrimary,
                    ),
                  )
                : const Text('Register'),
          ),
          const SizedBox(height: 12),
          OutlinedButton(
            onPressed: _busy
                ? null
                : () async {
                    try {
                      await context.read<AuthProvider>().loginDemo();
                      if (mounted) Navigator.pop(context);
                    } on AppException catch (e) {
                      setState(() => _error = e.message);
                    }
                  },
            child: const Text('Use demo profile instead'),
          ),
          const SizedBox(height: 16),
          Text(
            'New signups send a confirmation email. The free Supabase plan rate-limits '
            'those after a few tries. Demo: ${DemoAccount.email} / ${DemoAccount.password}',
            style: const TextStyle(color: AppColors.muted, height: 1.4),
          ),
        ],
      ),
      ),
    );
  }
}

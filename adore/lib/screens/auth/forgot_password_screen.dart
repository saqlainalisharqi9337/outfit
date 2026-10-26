import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../config/demo_account.dart';
import '../../providers/auth_provider.dart';
import '../../theme/app_theme.dart';
import '../../utils/exceptions.dart';
import '../../widgets/common.dart';
import '../../widgets/motion.dart';

class ForgotPasswordScreen extends StatefulWidget {
  const ForgotPasswordScreen({super.key});

  static const route = '/forgot';

  @override
  State<ForgotPasswordScreen> createState() => _ForgotPasswordScreenState();
}

class _ForgotPasswordScreenState extends State<ForgotPasswordScreen> {
  final _email = TextEditingController(text: DemoAccount.email);
  String? _message;
  String? _error;
  bool _busy = false;

  @override
  void dispose() {
    _email.dispose();
    super.dispose();
  }

  Future<void> _send() async {
    setState(() {
      _busy = true;
      _error = null;
      _message = null;
    });
    try {
      final note = await context.read<AuthProvider>().forgotPassword(_email.text);
      setState(() => _message = note);
    } on AppException catch (e) {
      setState(() => _error = e.message);
    } finally {
      setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Forgot password')),
      body: SoftBackdrop(
        child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          children: [
            Text(
              'Reset emails are rate-limited on the free plan. For the demo account, '
              'tap Send and the app will show the password instead of emailing Supabase.',
              style: TextStyle(color: AppColors.muted, height: 1.4),
            ),
            const SizedBox(height: 16),
            TextField(
              controller: _email,
              keyboardType: TextInputType.emailAddress,
              decoration: const InputDecoration(labelText: 'Email'),
            ),
            const SizedBox(height: 16),
            if (_error != null) StatusBanner(message: _error!),
            if (_message != null)
              StatusBanner(message: _message!, tone: StatusTone.success),
            const SizedBox(height: 12),
            FilledButton(
              onPressed: _busy ? null : _send,
              child: _busy
                  ? const SizedBox(
                      height: 18,
                      width: 18,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        color: AppColors.onPrimary,
                      ),
                    )
                  : const Text('Send reset link'),
            ),
          ],
        ),
      ),
      ),
    );
  }
}

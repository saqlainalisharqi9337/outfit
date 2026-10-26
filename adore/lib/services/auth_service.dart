import 'package:supabase_flutter/supabase_flutter.dart';

import '../config/demo_account.dart';
import '../utils/exceptions.dart' as app;
import '../utils/transient_retry.dart';

class AuthService {
  AuthService({SupabaseClient? client})
      : _client = client ?? Supabase.instance.client;

  final SupabaseClient _client;

  Stream<User?> authStateChanges() {
    return _client.auth.onAuthStateChange.map((event) => event.session?.user);
  }

  User? get currentUser => _client.auth.currentUser;

  Future<User> register({
    required String name,
    required String email,
    required String password,
  }) async {
    try {
      return await retryTransient(() => _registerOnce(
            name: name,
            email: email,
            password: password,
          ));
    } on app.AuthException {
      rethrow;
    } on AuthException catch (e) {
      throw app.AuthException(_messageFor(e.message, email: email));
    } catch (e) {
      throw app.AuthException(_messageFor(e.toString(), email: email));
    }
  }

  Future<User> _registerOnce({
    required String name,
    required String email,
    required String password,
  }) async {
    final response = await _client.auth.signUp(
      email: email.trim(),
      password: password,
      data: {'name': name.trim()},
    );
    final user = response.user;
    if (user == null) {
      throw app.AuthException('Registration failed.');
    }
    if (response.session == null) {
      throw app.AuthException(
        'Account created, but email confirmation is still enabled. '
        'In Supabase → Authentication → Providers → Email, turn off Confirm email, then log in.',
      );
    }
    return user;
  }

  Future<User> login({
    required String email,
    required String password,
  }) async {
    try {
      return await retryTransient(
        () => _loginOnce(email: email, password: password),
      );
    } on app.AuthException {
      rethrow;
    } on AuthException catch (e) {
      throw app.AuthException(_messageFor(e.message, email: email));
    } catch (e) {
      throw app.AuthException(_messageFor(e.toString(), email: email));
    }
  }

  Future<User> _loginOnce({
    required String email,
    required String password,
  }) async {
    final response = await _client.auth
        .signInWithPassword(
          email: email.trim(),
          password: password,
        )
        .timeout(
          const Duration(seconds: 25),
          onTimeout: () => throw app.AuthException(
            'Login timed out. Check the phone internet and try again.',
          ),
        );
    final user = response.user;
    if (user == null) {
      throw app.AuthException('Login failed.');
    }
    return user;
  }

  Future<String> sendPasswordReset(String email) async {
    if (DemoAccount.matchesEmail(email)) {
      return 'This is the FYP demo account. Password is ${DemoAccount.password}. '
          'No reset email is sent, so it does not hit the Supabase email rate limit.';
    }
    try {
      await retryTransient(
        () => _client.auth.resetPasswordForEmail(email.trim()),
      );
      return 'Password reset email sent if the account exists.';
    } on AuthException catch (e) {
      throw app.AuthException(_messageFor(e.message, email: email));
    } catch (e) {
      throw app.AuthException(_messageFor(e.toString(), email: email));
    }
  }

  Future<void> logout() => _client.auth.signOut();

  String _messageFor(String message, {String? email}) {
    final lower = message.toLowerCase();
    if (lower.contains('jwt issued at future') || lower.contains('pgrst303')) {
      return 'The account was reached, but the phone clock does not match the server. '
          'Turn on automatic date and time, wait a minute, then try again.';
    }
    if (lower.contains('bad gateway')) {
      return 'The account server is waking up. Wait a minute, then try again.';
    }
    if (lower.contains('failed host lookup') ||
        lower.contains('socketexception') ||
        lower.contains('no address associated') ||
        lower.contains('network is unreachable') ||
        lower.contains('connection refused') ||
        lower.contains('connection errored')) {
      return 'The phone cannot reach the account server, so sign up, sign in, '
          'and password reset all stop here. Check the phone’s internet, then '
          'open the Supabase dashboard and restore the project if it is paused. '
          'Until that server is back, use Continue as guest.';
    }
    if (lower.contains('rate limit') ||
        lower.contains('over_email_send_rate_limit') ||
        lower.contains('email rate')) {
      return 'Supabase free plan only sends a few emails per hour, so register and '
          'forgot-password are blocked right now. Use the demo login instead: '
          '${DemoAccount.email} / ${DemoAccount.password}';
    }
    if (lower.contains('already registered')) {
      return 'An account already exists for that email.';
    }
    if (lower.contains('invalid login') ||
        lower.contains('invalid credentials') ||
        lower.contains('invalid_grant')) {
      if (email != null && DemoAccount.matchesEmail(email)) {
        return 'Demo profile is not in the database yet. In the Supabase SQL Editor, '
            'paste and run the contents of 20260830010000_demo_test_profile.sql, then tap Log in.';
      }
      return 'Incorrect email or password. Try the demo account: '
          '${DemoAccount.email} / ${DemoAccount.password}';
    }
    if (lower.contains('password should be')) {
      return 'Password should be at least 6 characters.';
    }
    if (message.trim().isEmpty) {
      return 'Could not log in. If you are using the demo account, run the demo SQL script first.';
    }
    return message;
  }
}

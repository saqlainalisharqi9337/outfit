import 'package:flutter/foundation.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import '../config/demo_account.dart';
import '../models/user_model.dart';
import '../services/auth_service.dart';
import '../services/demo_store.dart';
import '../services/user_service.dart';
import '../utils/exceptions.dart';

class AuthProvider extends ChangeNotifier {
  AuthProvider({
    required AuthService authService,
    required UserService userService,
  })  : _authService = authService,
        _userService = userService {
    final current = _authService.currentUser;
    if (current != null) {
      _onAuth(current);
    } else {
      initializing = false;
      loading = false;
    }
    _authService.authStateChanges().listen(_onAuth);
  }

  final AuthService _authService;
  final UserService _userService;

  User? sessionUser;
  UserModel? profile;
  bool initializing = true;
  bool loading = true;
  bool demoMode = false;
  String? error;

  bool get isLoggedIn => demoMode || sessionUser != null;
  bool get needsOnboarding =>
      isLoggedIn && (profile == null || !profile!.onboardingComplete);

  Future<void> _onAuth(User? user) async {
    if (demoMode) return;
    sessionUser = user;
    if (user == null) {
      profile = null;
      initializing = false;
      loading = false;
      notifyListeners();
      return;
    }
    initializing = false;
    notifyListeners();
    try {
      profile = await _userService
          .getUser(user.id)
          .timeout(const Duration(seconds: 8));
    } catch (e) {
      error = e.toString();
      profile = null;
    }
    profile ??= UserModel(
      id: user.id,
      name: (user.userMetadata?['name'] as String?)?.trim().isNotEmpty == true
          ? user.userMetadata!['name'] as String
          : (user.email ?? 'User'),
      email: user.email ?? '',
      createdAt: DateTime.now(),
    );
    loading = false;
    notifyListeners();
  }

  Future<void> enterLocalDemo() async {
    DemoStore.instance.start();
    demoMode = true;
    sessionUser = null;
    profile = DemoStore.instance.profile;
    initializing = false;
    loading = false;
    error = null;
    notifyListeners();
  }

  Future<void> refreshProfile() async {
    if (demoMode) {
      profile = DemoStore.instance.profile;
      notifyListeners();
      return;
    }
    final uid = sessionUser?.id;
    if (uid == null) return;
    profile = await _userService.getUser(uid);
    notifyListeners();
  }

  Future<void> register({
    required String name,
    required String email,
    required String password,
  }) async {
    error = null;
    notifyListeners();
    try {
      final user = await _authService.register(
        name: name,
        email: email,
        password: password,
      );
      sessionUser = user;
      try {
        await _userService.createUser(
          UserModel(
            id: user.id,
            name: name.trim(),
            email: email.trim(),
            createdAt: DateTime.now(),
          ),
        );
      } on DatabaseException {
        // Auth already created the account, and the database trigger may
        // already have written the profile. Keep going so sign-in can finish.
      }
      try {
        await refreshProfile();
      } catch (_) {
        profile ??= UserModel(
          id: user.id,
          name: name.trim(),
          email: email.trim(),
          createdAt: DateTime.now(),
        );
        notifyListeners();
      }
    } on AppException catch (e) {
      error = e.message;
      rethrow;
    }
  }

  Future<void> login({required String email, required String password}) async {
    error = null;
    notifyListeners();
    if (DemoAccount.matchesEmail(email) &&
        password.trim() == DemoAccount.password) {
      await enterLocalDemo();
      return;
    }
    try {
      await _authService.login(email: email, password: password);
    } on AppException catch (e) {
      error = e.message;
      rethrow;
    }
  }

  Future<void> loginDemo() => enterLocalDemo();

  Future<String> forgotPassword(String email) =>
      _authService.sendPasswordReset(email);

  Future<void> logout() async {
    if (demoMode) {
      DemoStore.instance.stop();
      demoMode = false;
      sessionUser = null;
      profile = null;
      error = null;
      notifyListeners();
      return;
    }
    await _authService.logout();
  }

  Future<void> saveProfile(UserModel user) async {
    if (demoMode) {
      DemoStore.instance.profile = user;
      profile = user;
      notifyListeners();
      return;
    }
    await _userService.updateUser(user);
    profile = user;
    notifyListeners();
  }
}

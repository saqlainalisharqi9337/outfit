import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'providers/auth_provider.dart';
import 'providers/theme_controller.dart';
import 'screens/auth/forgot_password_screen.dart';
import 'screens/auth/login_screen.dart';
import 'screens/auth/register_screen.dart';
import 'screens/onboarding/profile_setup_screen.dart';
import 'screens/setup/backend_setup_screen.dart';
import 'screens/shell/app_shell.dart';
import 'screens/splash/splash_screen.dart';
import 'theme/app_theme.dart';
import 'utils/constants.dart';

class AdoreApp extends StatelessWidget {
  const AdoreApp({super.key, required this.backendReady});

  final bool backendReady;

  @override
  Widget build(BuildContext context) {
    final theme = context.watch<ThemeController>();
    return MaterialApp(
      title: AppConstants.appName,
      debugShowCheckedModeBanner: false,
      theme: AppTheme.light,
      darkTheme: AppTheme.dark,
      themeMode: theme.mode,
      scrollBehavior: const MaterialScrollBehavior().copyWith(
        physics: const BouncingScrollPhysics(),
      ),
      home: backendReady ? const RootGate() : const BackendSetupScreen(),
      routes: {
        LoginScreen.route: (_) => const LoginScreen(),
        RegisterScreen.route: (_) => const RegisterScreen(),
        ForgotPasswordScreen.route: (_) => const ForgotPasswordScreen(),
      },
    );
  }
}

class RootGate extends StatelessWidget {
  const RootGate({super.key});

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthProvider>();
    if (auth.initializing) return const SplashScreen();
    if (!auth.isLoggedIn) return const LoginScreen();
    if (auth.needsOnboarding) return const ProfileSetupScreen();
    return const AppShell();
  }
}

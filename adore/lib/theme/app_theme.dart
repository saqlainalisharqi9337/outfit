import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

/// Brand: wine + warm cream. Direction: **soft layered editorial** —
/// cream surfaces, 8px grid, restrained shadows. Not glass, not flat Material.
class AppColors {
  /// Matches the Outfit Recommendation App prototype.
  static const Color background = Color(0xFFF8F6F3);
  static const Color surface = Color(0xFFFFFFFF);
  static const Color surfaceMuted = Color(0xFFF3F1EE);
  static const Color primary = Color(0xFFE8395A);
  static const Color primaryDark = Color(0xFF18172B);
  static const Color primarySoft = Color(0x14E8395A);
  static const Color secondary = Color(0xFF7C6AF5);
  static const Color accent = Color(0xFFF5A623);
  static const Color blush = Color(0xFFFFD6DE);
  static const Color ink = Color(0xFF18172B);
  static const Color muted = Color(0xFF716C85);
  static const Color success = Color(0xFF2F6B4F);
  static const Color warning = Color(0xFFA86418);
  static const Color danger = Color(0xFF9B1C1C);
  static const Color cardBorder = Color(0x1418172B);
  static const Color onPrimary = Color(0xFFFFFFFF);
  static const Color overlay = Color(0x14000000);
  static const Color nav = Color(0xF7101328);

  static const Color darkBackground = Color(0xFF080B1A);
  static const Color darkSurface = Color(0xFF101328);
  static const Color darkInk = Color(0xFFEDE9F4);
  static const Color darkMuted = Color(0xFF8B87A8);
  static const Color darkBorder = Color(0x14FFFFFF);
}

class AppSpace {
  static const double xs = 4;
  static const double sm = 8;
  static const double md = 12;
  static const double lg = 16;
  static const double xl = 24;
  static const double xxl = 32;
  static const double page = 20;
  static const double touch = 44;
  static const double maxContent = 880;
}

/// Space needed so the last item sits above the floating bottom bar.
double bottomNavClearance(BuildContext context) {
  final inset = MediaQuery.paddingOf(context).bottom;
  const barAboveSystemInset = 88.0;
  if (inset >= barAboveSystemInset) return inset + 12;
  return inset + barAboveSystemInset;
}

class AppRadius {
  static const double sm = 12;
  static const double md = 16;
  static const double lg = 20;
  static const double xl = 24;
}

class AppDuration {
  static const Duration fast = Duration(milliseconds: 160);
  static const Duration medium = Duration(milliseconds: 260);
  static const Duration enter = Duration(milliseconds: 280);
}

class AppShadows {
  static List<BoxShadow> get soft => [
        BoxShadow(
          color: AppColors.primaryDark.withValues(alpha: 0.07),
          blurRadius: 20,
          offset: const Offset(0, 8),
        ),
      ];

  static List<BoxShadow> get lift => [
        BoxShadow(
          color: AppColors.primaryDark.withValues(alpha: 0.12),
          blurRadius: 28,
          offset: const Offset(0, 12),
        ),
      ];

  static List<BoxShadow> get nav => [
        BoxShadow(
          color: AppColors.primaryDark.withValues(alpha: 0.08),
          blurRadius: 18,
          offset: const Offset(0, -4),
        ),
      ];
}

class _FadeSlideTransitionsBuilder extends PageTransitionsBuilder {
  const _FadeSlideTransitionsBuilder();

  @override
  Widget buildTransitions<T>(
    PageRoute<T> route,
    BuildContext context,
    Animation<double> animation,
    Animation<double> secondaryAnimation,
    Widget child,
  ) {
    final curved = CurvedAnimation(parent: animation, curve: Curves.easeOutCubic);
    return FadeTransition(
      opacity: curved,
      child: SlideTransition(
        position: Tween<Offset>(
          begin: const Offset(0, 0.03),
          end: Offset.zero,
        ).animate(curved),
        child: child,
      ),
    );
  }
}

class AppTheme {
  static const pageTransitions = PageTransitionsTheme(
    builders: {
      TargetPlatform.android: _FadeSlideTransitionsBuilder(),
      TargetPlatform.iOS: _FadeSlideTransitionsBuilder(),
      TargetPlatform.windows: _FadeSlideTransitionsBuilder(),
      TargetPlatform.macOS: _FadeSlideTransitionsBuilder(),
      TargetPlatform.linux: _FadeSlideTransitionsBuilder(),
      TargetPlatform.fuchsia: _FadeSlideTransitionsBuilder(),
    },
  );

  static TextTheme _textTheme(TextTheme base, Color body, Color display) {
    final sans = GoogleFonts.dmSansTextTheme(base);
    final displayFace = GoogleFonts.playfairDisplay;
    return sans
        .copyWith(
          displayLarge: displayFace(
            fontSize: 40,
            fontWeight: FontWeight.w600,
            height: 1.15,
            color: display,
          ),
          displayMedium: displayFace(
            fontSize: 32,
            fontWeight: FontWeight.w600,
            height: 1.2,
            color: display,
          ),
          headlineLarge: displayFace(
            fontSize: 26,
            fontWeight: FontWeight.w600,
            color: display,
          ),
          headlineMedium: displayFace(
            fontSize: 22,
            fontWeight: FontWeight.w600,
            color: display,
          ),
          titleLarge: sans.titleLarge?.copyWith(
            fontSize: 18,
            fontWeight: FontWeight.w700,
            color: body,
          ),
          titleMedium: sans.titleMedium?.copyWith(
            fontSize: 16,
            fontWeight: FontWeight.w600,
            color: body,
          ),
          bodyLarge: sans.bodyLarge?.copyWith(
            fontSize: 16,
            height: 1.45,
            color: body,
          ),
          bodyMedium: sans.bodyMedium?.copyWith(
            fontSize: 14,
            height: 1.45,
            color: body,
          ),
          bodySmall: sans.bodySmall?.copyWith(
            fontSize: 12,
            height: 1.4,
            color: AppColors.muted,
          ),
          labelLarge: sans.labelLarge?.copyWith(
            fontSize: 14,
            fontWeight: FontWeight.w700,
            letterSpacing: 0.2,
          ),
        )
        .apply(bodyColor: body, displayColor: display);
  }

  static ThemeData get light {
    final scheme = ColorScheme.fromSeed(
      seedColor: AppColors.primary,
      brightness: Brightness.light,
      primary: AppColors.primary,
      onPrimary: AppColors.onPrimary,
      secondary: AppColors.secondary,
      onSecondary: AppColors.primaryDark,
      tertiary: AppColors.accent,
      surface: AppColors.surface,
      onSurface: AppColors.ink,
      error: AppColors.danger,
    );
    final base = ThemeData(
      useMaterial3: true,
      colorScheme: scheme,
      brightness: Brightness.light,
    );
    return _decorate(base, light: true);
  }

  static ThemeData get dark {
    final scheme = ColorScheme.fromSeed(
      seedColor: AppColors.primary,
      brightness: Brightness.dark,
      primary: AppColors.primary,
      onPrimary: AppColors.onPrimary,
      secondary: AppColors.secondary,
      surface: AppColors.darkSurface,
      onSurface: AppColors.darkInk,
      error: const Color(0xFFFF8A80),
    );
    final base = ThemeData(
      useMaterial3: true,
      colorScheme: scheme,
      brightness: Brightness.dark,
    );
    return _decorate(base, light: false);
  }

  static ThemeData _decorate(ThemeData base, {required bool light}) {
    final ink = light ? AppColors.ink : AppColors.darkInk;
    final surface = light ? AppColors.surface : AppColors.darkSurface;
    final bg = light ? AppColors.background : AppColors.darkBackground;
    final border = light ? AppColors.cardBorder : AppColors.darkBorder;
    final muted = light ? AppColors.muted : AppColors.darkMuted;

    return base.copyWith(
      scaffoldBackgroundColor: bg,
      textTheme: _textTheme(base.textTheme, ink, ink),
      appBarTheme: AppBarTheme(
        backgroundColor: Colors.transparent,
        foregroundColor: ink,
        elevation: 0,
        scrolledUnderElevation: 0,
        centerTitle: false,
        toolbarHeight: 56,
        titleTextStyle: GoogleFonts.playfairDisplay(
          fontSize: 24,
          fontWeight: FontWeight.w600,
          color: ink,
        ),
        iconTheme: IconThemeData(color: ink, size: 22),
      ),
      cardTheme: CardThemeData(
        color: surface,
        elevation: 0,
        margin: EdgeInsets.zero,
        shadowColor: AppColors.primaryDark.withValues(alpha: 0.1),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppRadius.lg),
          side: BorderSide(color: border),
        ),
      ),
      chipTheme: ChipThemeData(
        backgroundColor: surface,
        selectedColor: AppColors.primarySoft,
        labelStyle: TextStyle(color: ink, fontWeight: FontWeight.w600, fontSize: 13),
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        side: BorderSide(color: border),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: surface,
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
        hintStyle: TextStyle(color: muted),
        labelStyle: TextStyle(color: muted),
        errorStyle: const TextStyle(color: AppColors.danger, height: 1.3),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppRadius.md),
          borderSide: BorderSide(color: border),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppRadius.md),
          borderSide: BorderSide(color: border),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppRadius.md),
          borderSide: const BorderSide(color: AppColors.primary, width: 1.5),
        ),
        errorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppRadius.md),
          borderSide: const BorderSide(color: AppColors.danger),
        ),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          backgroundColor: AppColors.primary,
          foregroundColor: AppColors.onPrimary,
          disabledBackgroundColor: AppColors.primary.withValues(alpha: 0.38),
          disabledForegroundColor: AppColors.onPrimary.withValues(alpha: 0.7),
          minimumSize: const Size(AppSpace.touch, 52),
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
          elevation: 0,
          textStyle: const TextStyle(fontWeight: FontWeight.w700, fontSize: 15),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(AppRadius.md),
          ),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: AppColors.primary,
          minimumSize: const Size(AppSpace.touch, 52),
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
          side: const BorderSide(color: AppColors.primary, width: 1.2),
          textStyle: const TextStyle(fontWeight: FontWeight.w700, fontSize: 15),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(AppRadius.md),
          ),
        ),
      ),
      textButtonTheme: TextButtonThemeData(
        style: TextButton.styleFrom(
          foregroundColor: AppColors.primary,
          minimumSize: const Size(AppSpace.touch, AppSpace.touch),
          textStyle: const TextStyle(fontWeight: FontWeight.w600),
        ),
      ),
      iconButtonTheme: IconButtonThemeData(
        style: IconButton.styleFrom(
          minimumSize: const Size(AppSpace.touch, AppSpace.touch),
          foregroundColor: ink,
        ),
      ),
      floatingActionButtonTheme: FloatingActionButtonThemeData(
        backgroundColor: AppColors.primary,
        foregroundColor: AppColors.onPrimary,
        elevation: 3,
        highlightElevation: 6,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppRadius.lg),
        ),
      ),
      listTileTheme: ListTileThemeData(
        iconColor: AppColors.primary,
        minVerticalPadding: 12,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppRadius.md),
        ),
      ),
      snackBarTheme: SnackBarThemeData(
        behavior: SnackBarBehavior.floating,
        backgroundColor: AppColors.primaryDark,
        contentTextStyle: const TextStyle(color: AppColors.onPrimary),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppRadius.md),
        ),
      ),
      progressIndicatorTheme: const ProgressIndicatorThemeData(
        color: AppColors.primary,
        circularTrackColor: AppColors.blush,
      ),
      dividerTheme: DividerThemeData(color: border, space: 1, thickness: 1),
      navigationBarTheme: NavigationBarThemeData(
        backgroundColor: surface.withValues(alpha: 0.97),
        elevation: 0,
        height: 72,
        indicatorColor: AppColors.primarySoft,
        indicatorShape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppRadius.md),
        ),
        iconTheme: WidgetStateProperty.resolveWith((states) {
          return IconThemeData(
            size: 22,
            color: states.contains(WidgetState.selected)
                ? AppColors.primary
                : muted,
          );
        }),
        labelTextStyle: WidgetStateProperty.resolveWith((states) {
          return TextStyle(
            fontSize: 11,
            fontWeight: states.contains(WidgetState.selected)
                ? FontWeight.w700
                : FontWeight.w500,
            color: states.contains(WidgetState.selected)
                ? AppColors.primary
                : muted,
          );
        }),
      ),
      pageTransitionsTheme: pageTransitions,
    );
  }
}

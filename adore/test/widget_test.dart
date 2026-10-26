import 'package:adore/screens/splash/splash_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:google_fonts/google_fonts.dart';

void main() {
  setUpAll(() {
    // Without this the splash screen's Playfair Display request opens a real
    // HTTP fetch, whose timer outlives the widget tree and trips the test
    // framework's pending-timer assertion.
    GoogleFonts.config.allowRuntimeFetching = false;
  });

  testWidgets('splash branding is visible', (tester) async {
    await tester.pumpWidget(const MaterialApp(home: SplashScreen()));
    // FadeSlideIn schedules its reveal with a zero-delay future, so the fake
    // clock has to actually advance before teardown or that timer is still
    // pending. pumpAndSettle cannot be used here: SoftBackdrop animations linger.
    await tester.pump(const Duration(milliseconds: 600));
    expect(find.text('Adore'), findsOneWidget);
    expect(find.byType(Image), findsWidgets);
  });
}

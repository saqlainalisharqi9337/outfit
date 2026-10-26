import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import 'app.dart';
import 'config/supabase_config.dart';
import 'providers/app_navigation.dart';
import 'providers/theme_controller.dart';
import 'providers/auth_provider.dart';
import 'providers/event_provider.dart';
import 'providers/recommendation_provider.dart';
import 'providers/shop_provider.dart';
import 'providers/wardrobe_provider.dart';
import 'providers/weather_provider.dart';
import 'services/auth_service.dart';
import 'services/event_service.dart';
import 'services/feedback_service.dart';
import 'services/geocoding_service.dart';
import 'services/image_analysis_service.dart';
import 'services/location_service.dart';
import 'services/recommendation_service.dart';
import 'services/shopping_service.dart';
import 'services/storage_service.dart';
import 'services/trends_service.dart';
import 'services/user_service.dart';
import 'services/wardrobe_service.dart';
import 'services/weather_service.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  var ready = true;
  try {
    await Supabase.initialize(
      url: SupabaseConfig.url,
      publishableKey: SupabaseConfig.publishableKey,
    );
  } catch (_) {
    ready = false;
  }

  final theme = ThemeController();
  await theme.load();

  if (!ready) {
    runApp(
      ChangeNotifierProvider.value(
        value: theme,
        child: const AdoreApp(backendReady: false),
      ),
    );
    return;
  }

  runApp(
    MultiProvider(
      providers: [
        ChangeNotifierProvider.value(value: theme),
        ChangeNotifierProvider(create: (_) => AppNavigation()),
        Provider(create: (_) => ImageAnalysisService()),
        Provider(create: (_) => StorageService()),
        ChangeNotifierProvider(
          create: (_) => AuthProvider(
            authService: AuthService(),
            userService: UserService(),
          ),
        ),
        ChangeNotifierProvider(
          create: (_) => WeatherProvider(
            weatherService: WeatherService(),
            geocodingService: GeocodingService(),
            locationService: LocationService(),
          ),
        ),
        ChangeNotifierProvider(
          create: (_) => WardrobeProvider(
            wardrobeService: WardrobeService(),
            storageService: StorageService(),
          ),
        ),
        ChangeNotifierProvider(
          create: (_) => RecommendationProvider(
            recommendationService: RecommendationService(),
            feedbackService: FeedbackService(),
            shoppingService: ShoppingService(),
            trendsService: TrendsService(),
          ),
        ),
        ChangeNotifierProvider(
          create: (_) => ShopProvider(
            shoppingService: ShoppingService(),
            trendsService: TrendsService(),
          ),
        ),
        ChangeNotifierProvider(
          create: (_) => EventProvider(eventService: EventService()),
        ),
      ],
      child: const AdoreApp(backendReady: true),
    ),
  );
}

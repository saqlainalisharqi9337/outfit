import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';

import '../../providers/app_navigation.dart';
import '../../providers/auth_provider.dart';
import '../../providers/event_provider.dart';
import '../../providers/recommendation_provider.dart';
import '../../providers/shop_provider.dart';
import '../../providers/wardrobe_provider.dart';
import '../../providers/weather_provider.dart';
import '../../theme/app_theme.dart';
import '../../utils/enums.dart';
import '../../utils/weather_actions.dart';
import '../../widgets/common.dart';
import '../../widgets/motion.dart';
import '../../widgets/outfit_card.dart';
import '../../widgets/weather_card.dart';
import '../calendar/calendar_screen.dart';
import '../outfit/outfit_screen.dart';
import '../tryon/try_on_screen.dart';
import '../trends/trends_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  bool _locating = false;

  Future<void> _useCurrentLocation() async {
    if (_locating) return;
    setState(() => _locating = true);
    try {
      await promptAndApplyLiveLocation(context);
    } finally {
      if (mounted) setState(() => _locating = false);
    }
  }

  void _openOutfit() {
    final user = context.read<AuthProvider>().profile;
    final liveWeather = context.read<WeatherProvider>().weather;
    final wardrobe = context.read<WardrobeProvider>().items;
    final rec = context.read<RecommendationProvider>();

    rec.clearEventContext();
    if (user != null && liveWeather != null) {
      rec.generate(
        user: user,
        wardrobe: wardrobe,
        weather: liveWeather,
        refresh: true,
      );
    }
    Navigator.push(
      context,
      MaterialPageRoute(builder: (_) => const OutfitScreen()),
    );
  }

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthProvider>();
    final weather = context.watch<WeatherProvider>();
    final rec = context.watch<RecommendationProvider>();
    final wardrobe = context.watch<WardrobeProvider>();
    final events = context.watch<EventProvider>();
    final user = auth.profile;
    final hour = DateTime.now().hour;
    final hello = hour < 12
        ? 'Good morning'
        : hour < 17
            ? 'Good afternoon'
            : 'Good evening';

    return Scaffold(
      extendBodyBehindAppBar: false,
      appBar: AppBar(
        automaticallyImplyLeading: false,
        leading: IconButton(
          tooltip: 'Wardrobe',
          onPressed: () => context.read<AppNavigation>().goTo(AppNavigation.adroble),
          icon: const Icon(Icons.search),
        ),
        actions: [
          IconButton(
            tooltip: 'Notifications',
            onPressed: () {
              showDialog<void>(
                context: context,
                builder: (context) => AlertDialog(
                  title: const Text('Notifications'),
                  content: const Text(
                    'A new outfit suggestion is ready from your wardrobe and today’s weather.',
                  ),
                  actions: [
                    TextButton(
                      onPressed: () => Navigator.pop(context),
                      child: const Text('Close'),
                    ),
                  ],
                ),
              );
            },
            icon: const Icon(Icons.notifications_none),
          ),
          IconButton(
            tooltip: 'Profile',
            onPressed: () => context.read<AppNavigation>().goTo(AppNavigation.profile),
            icon: const Icon(Icons.person_outline),
          ),
        ],
      ),
      body: SoftBackdrop(
        child: RefreshIndicator(
        onRefresh: () async {
          if (user != null) {
            await weather.loadForProfile(user, force: true);
            if (weather.weather != null) {
              await rec.generate(
                user: user,
                wardrobe: wardrobe.items,
                weather: weather.weather!,
                refresh: true,
              );
            }
          }
        },
        child: ListView(
          padding: const EdgeInsets.all(20),
          children: [
            Text(
              'Find Your Perfect Outfit Today',
              style: GoogleFonts.playfairDisplay(
                fontSize: 28,
                fontWeight: FontWeight.w600,
                color: Theme.of(context).colorScheme.onSurface,
              ),
            ),
            if (user != null)
              Padding(
                padding: const EdgeInsets.only(top: 6),
                child: Text(
                  '$hello, ${user.name.split(' ').first}',
                  style: const TextStyle(color: AppColors.muted),
                ),
              ),
            const SizedBox(height: 16),
            Builder(
              builder: (context) {
                final dark = Theme.of(context).brightness == Brightness.dark;
                final lightRose = Color.alphaBlend(
                  AppColors.primary.withValues(alpha: dark ? 0.28 : 0.20),
                  Colors.white,
                );
                final lightLilac = Color.alphaBlend(
                  AppColors.secondary.withValues(alpha: dark ? 0.32 : 0.22),
                  Colors.white,
                );
                return DecoratedBox(
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(20),
                    gradient: LinearGradient(colors: [lightRose, lightLilac]),
                    border: Border.all(
                      color: AppColors.primary.withValues(alpha: dark ? 0.45 : 0.28),
                    ),
                  ),
                  child: SizedBox(
                    width: double.infinity,
                    child: TextButton(
                      onPressed: _openOutfit,
                      style: TextButton.styleFrom(
                        foregroundColor: AppColors.primary,
                        padding: const EdgeInsets.symmetric(vertical: 16),
                      ),
                      child: const Text(
                        'Get Outfit Suggestions',
                        style: TextStyle(fontSize: 18, fontWeight: FontWeight.w600),
                      ),
                    ),
                  ),
                );
              },
            ),
            const SizedBox(height: 12),
            const TryOnHomeCard(),
            const SizedBox(height: 16),
            if (weather.loading)
              const LoadingView(message: 'Fetching weather…', skeleton: true),
            if (weather.error != null)
              ErrorView(
                message: weather.error!,
                onRetry: () {
                  if (user != null) weather.loadForProfile(user, force: true);
                },
              ),
            if (weather.weather == null && !weather.loading)
              Card(
                child: Column(
                  children: [
                    ListTile(
                      leading: const Icon(Icons.my_location),
                      title: const Text('Use live location'),
                      subtitle: const Text(
                        'Allow GPS to load live weather for your city.',
                      ),
                      onTap:
                          user == null || _locating ? null : _useCurrentLocation,
                    ),
                    const Divider(height: 1),
                    ListTile(
                      leading: const Icon(Icons.public),
                      title: const Text('Choose country & city'),
                      subtitle: const Text(
                        'Pick a place manually if GPS is unavailable.',
                      ),
                      onTap: user == null ? null : () => openLocationPicker(context),
                    ),
                  ],
                ),
              ),
            if (weather.weather != null)
              WeatherCard(
                weather: weather.weather!,
                locating: _locating,
                onRefresh: () {
                  refreshWeatherAndLooks(context);
                },
                onUseLiveLocation: _useCurrentLocation,
                onPickLocation: () => openLocationPicker(context),
              ),
            const SizedBox(height: 22),
            FadeSlideIn(
              delay: const Duration(milliseconds: 80),
              child: SectionHeader(
              "Today's outfit",
              action: 'See all',
              onAction: _openOutfit,
              ),
            ),
            if (rec.loading) const LoadingView(message: 'Styling your look…'),
            if (rec.error != null)
              ErrorView(
                message: rec.error!,
                onRetry: () {
                  if (user != null && weather.weather != null) {
                    rec.generate(
                      user: user,
                      wardrobe: wardrobe.items,
                      weather: weather.weather!,
                    );
                  }
                },
              ),
            if (!rec.loading && rec.selected != null)
              FadeSlideIn(
                delay: const Duration(milliseconds: 140),
                child: OutfitCard(
                  outfit: rec.selected!,
                  onTap: _openOutfit,
                ),
              ),
            if (!rec.loading && rec.result == null && weather.weather != null)
              EmptyView(
                title: 'No outfit yet',
                message: 'Generate a recommendation from your wardrobe and weather.',
                actionLabel: 'Recommend outfit',
                onAction: () {
                  if (user != null) {
                    rec.generate(
                      user: user,
                      wardrobe: wardrobe.items,
                      weather: weather.weather!,
                    );
                  }
                },
              ),
            const SizedBox(height: 18),
            FadeSlideIn(
              delay: const Duration(milliseconds: 180),
              child: SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: Row(
                  children: [
                    ShortcutTile(
                      label: 'Adorable',
                      icon: Icons.checkroom_outlined,
                      onTap: () => context
                          .read<AppNavigation>()
                          .goTo(AppNavigation.adroble),
                    ),
                    const SizedBox(width: 10),
                    ShortcutTile(
                      label: 'Calendar',
                      icon: Icons.calendar_today_outlined,
                      onTap: () => context
                          .read<AppNavigation>()
                          .goTo(AppNavigation.calendar),
                    ),
                    const SizedBox(width: 10),
                    ShortcutTile(
                      label: 'Try on',
                      icon: Icons.accessibility_new_outlined,
                      onTap: () => Navigator.push(
                        context,
                        MaterialPageRoute(builder: (_) => const TryOnScreen()),
                      ),
                    ),
                    const SizedBox(width: 10),
                    ShortcutTile(
                      label: 'Trends',
                      icon: Icons.local_fire_department_outlined,
                      onTap: () => Navigator.push(
                        context,
                        MaterialPageRoute(builder: (_) => const TrendsScreen()),
                      ),
                    ),
                    const SizedBox(width: 10),
                    ShortcutTile(
                      label: 'Shop  ${context.watch<ShopProvider>().products.length}',
                      icon: Icons.storefront_outlined,
                      onTap: () =>
                          context.read<AppNavigation>().goTo(AppNavigation.shop),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 22),
            FadeSlideIn(
              delay: const Duration(milliseconds: 220),
              child: const SectionHeader('Upcoming events'),
            ),
            if (events.items.isEmpty)
              const Padding(
                padding: EdgeInsets.only(top: 8),
                child: EmptyView(
                  title: 'No events yet',
                  message: 'Add one from Calendar so outfits can match the occasion.',
                  icon: Icons.event_outlined,
                ),
              ),
            ...events.items.take(3).map(
                  (e) => FadeSlideIn(
                    delay: const Duration(milliseconds: 260),
                    child: Card(
                      margin: const EdgeInsets.only(top: 10),
                      child: ListTile(
                        title: Text(e.name),
                        subtitle: Text(
                          '${DateFormat.MMMd().add_jm().format(e.dateTime)} · ${e.occasion.label}',
                        ),
                        trailing: const Icon(Icons.chevron_right),
                        onTap: () => Navigator.push(
                          context,
                          MaterialPageRoute(
                            builder: (_) => EventDetailScreen(event: e),
                          ),
                        ),
                      ),
                    ),
                  ),
                ),
            const SizedBox(height: 110),
          ],
        ),
        ),
      ),
    );
  }
}

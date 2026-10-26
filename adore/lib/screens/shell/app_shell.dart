import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../providers/app_navigation.dart';
import '../../providers/auth_provider.dart';
import '../../providers/event_provider.dart';
import '../../providers/recommendation_provider.dart';
import '../../providers/shop_provider.dart';
import '../../providers/wardrobe_provider.dart';
import '../../providers/weather_provider.dart';
import '../../theme/app_theme.dart';
import '../calendar/calendar_screen.dart';
import '../home/home_screen.dart';
import '../profile/profile_screen.dart';
import '../shop/shop_screen.dart';
import '../wardrobe/wardrobe_screen.dart';

class AppShell extends StatefulWidget {
  const AppShell({super.key});

  @override
  State<AppShell> createState() => _AppShellState();
}

class _AppShellState extends State<AppShell> {
  bool _bound = false;
  bool _autoRecommendStarted = false;
  WeatherProvider? _weather;
  WardrobeProvider? _wardrobe;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_bound) return;
    final user = context.read<AuthProvider>().profile;
    if (user == null) return;
    _bound = true;
    _weather = context.read<WeatherProvider>();
    _wardrobe = context.read<WardrobeProvider>();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      _wardrobe!.bind(user.id);
      context.read<EventProvider>().bind(user.id);
      context.read<ShopProvider>().bindCart(user.id);
      context.read<ShopProvider>().loadCatalog(user);
      _weather!.loadForProfile(user).whenComplete(_maybeRecommend);
      _weather!.addListener(_maybeRecommend);
      _wardrobe!.addListener(_maybeRecommend);
    });
  }

  @override
  void dispose() {
    _weather?.removeListener(_maybeRecommend);
    _wardrobe?.removeListener(_maybeRecommend);
    super.dispose();
  }

  void _maybeRecommend() {
    if (!mounted || _autoRecommendStarted) return;
    final user = context.read<AuthProvider>().profile;
    final weather = context.read<WeatherProvider>().weather;
    final rec = context.read<RecommendationProvider>();
    final wardrobe = context.read<WardrobeProvider>();
    if (user == null || weather == null || rec.loading || rec.result != null) {
      return;
    }
    _autoRecommendStarted = true;
    rec.generate(
      user: user,
      wardrobe: wardrobe.items,
      weather: weather,
    );
  }

  @override
  Widget build(BuildContext context) {
    final nav = context.watch<AppNavigation>();
    const pages = [
      HomeScreen(),
      CalendarScreen(),
      AdorableScreen(),
      ShopScreen(),
      ProfileScreen(),
    ];
    const items = [
      (Icons.home_outlined, 'Home'),
      (Icons.calendar_today_outlined, 'Calendar'),
      (Icons.checkroom_outlined, 'Wardrobe'),
      (Icons.favorite_border, 'Shop'),
      (Icons.person_outline, 'Profile'),
    ];
    return Scaffold(
      extendBody: true,
      body: IndexedStack(
        index: nav.index.clamp(0, pages.length - 1),
        children: pages,
      ),
      bottomNavigationBar: SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(16, 0, 16, 12),
          child: DecoratedBox(
            decoration: BoxDecoration(
              color: AppColors.nav,
              borderRadius: BorderRadius.circular(40),
              border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
              boxShadow: const [
                BoxShadow(
                  color: Color(0x8C080B1A),
                  blurRadius: 32,
                  offset: Offset(0, 8),
                ),
              ],
            ),
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 8),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  for (var i = 0; i < items.length; i++)
                    Expanded(
                      child: _NavPill(
                        icon: items[i].$1,
                        label: items[i].$2,
                        selected: nav.index == i,
                        onTap: () => nav.goTo(i),
                      ),
                    ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _NavPill extends StatelessWidget {
  const _NavPill({
    required this.icon,
    required this.label,
    required this.selected,
    required this.onTap,
  });

  final IconData icon;
  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(28),
      child: AnimatedContainer(
        duration: AppDuration.fast,
        height: 48,
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(28),
          gradient: selected
              ? const LinearGradient(
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                  colors: [Color(0xFFFF4D6D), Color(0xFF9B8BF4)],
                )
              : null,
        ),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(icon, size: 20, color: selected ? Colors.white : const Color(0xFF8B87A8)),
            if (selected)
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 2),
                child: FittedBox(
                  fit: BoxFit.scaleDown,
                  child: Text(
                    label,
                    maxLines: 1,
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 9,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }
}

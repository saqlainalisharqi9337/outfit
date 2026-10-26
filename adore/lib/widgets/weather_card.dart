import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:intl/intl.dart';

import '../models/weather_model.dart';
import '../theme/app_theme.dart';

class WeatherCard extends StatelessWidget {
  const WeatherCard({
    super.key,
    required this.weather,
    this.title,
    this.subtitle,
    this.onPickLocation,
    this.onUseLiveLocation,
    this.onRefresh,
    this.locating = false,
  });

  final WeatherModel weather;
  final String? title;
  final String? subtitle;
  final VoidCallback? onPickLocation;
  final VoidCallback? onUseLiveLocation;
  final VoidCallback? onRefresh;
  final bool locating;

  @override
  Widget build(BuildContext context) {
    final dark = Theme.of(context).brightness == Brightness.dark;
    final ink = dark ? AppColors.darkInk : AppColors.primaryDark;
    final muted = dark ? AppColors.darkMuted : AppColors.muted;
    final rose = Color.alphaBlend(
      AppColors.primary.withValues(alpha: dark ? 0.34 : 0.16),
      dark ? AppColors.darkSurface : Colors.white,
    );
    final lilac = Color.alphaBlend(
      AppColors.secondary.withValues(alpha: dark ? 0.28 : 0.14),
      dark ? AppColors.darkSurface : Colors.white,
    );
    final stats = <String>[
      'Feels ${weather.feelsLike.round()}°',
      if (weather.dailyHigh != null && weather.dailyLow != null)
        'H ${weather.dailyHigh!.round()}°  L ${weather.dailyLow!.round()}°',
      'Rain ${weather.precipitationProbability?.round() ?? 0}%',
      if (weather.humidity != null) 'Humidity ${weather.humidity!.round()}%',
      if (weather.windSpeed != null) 'Wind ${weather.windSpeed!.round()} km/h',
      if (weather.uvIndex != null) 'UV ${weather.uvIndex!.toStringAsFixed(1)}',
      if (weather.sunrise != null)
        'Sunrise ${DateFormat.Hm().format(weather.sunrise!.toLocal())}',
      if (weather.sunset != null)
        'Sunset ${DateFormat.Hm().format(weather.sunset!.toLocal())}',
    ];

    return Container(
      padding: const EdgeInsets.fromLTRB(14, 12, 8, 12),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [rose, lilac],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(22),
        border: Border.all(
          color: AppColors.primary.withValues(alpha: dark ? 0.35 : 0.18),
        ),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Row(
            children: [
              _WeatherBadge(code: weather.weatherCode, dark: dark),
              const SizedBox(width: 12),
              Expanded(
                child: InkWell(
                  onTap: onPickLocation,
                  borderRadius: BorderRadius.circular(10),
                  child: Padding(
                    padding: const EdgeInsets.symmetric(vertical: 2),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        if (title != null && title!.isNotEmpty) ...[
                          Text(
                            title!,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(
                              color: AppColors.primary,
                              fontWeight: FontWeight.w700,
                              fontSize: 12,
                            ),
                          ),
                          const SizedBox(height: 1),
                        ],
                        Row(
                          children: [
                            Flexible(
                              child: Text(
                                weather.city,
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                                style: TextStyle(
                                  color: ink,
                                  fontWeight: FontWeight.w700,
                                  fontSize: 15,
                                ),
                              ),
                            ),
                            if (onPickLocation != null) ...[
                              const SizedBox(width: 4),
                              Icon(Icons.edit_location_alt_outlined, size: 14, color: muted),
                            ],
                          ],
                        ),
                        Text(
                          subtitle ?? weather.condition,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: TextStyle(color: muted, fontSize: 12),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
              Text(
                '${weather.temperature.round()}°',
                style: GoogleFonts.playfairDisplay(
                  color: AppColors.primary,
                  fontSize: 34,
                  height: 1,
                  fontWeight: FontWeight.w600,
                ),
              ),
              if (onRefresh != null)
                _Action(
                  tooltip: 'Refresh weather',
                  onPressed: locating ? null : onRefresh,
                  icon: Icons.refresh,
                  color: ink,
                ),
              if (onUseLiveLocation != null)
                _Action(
                  tooltip: 'Use live GPS location',
                  onPressed: locating ? null : onUseLiveLocation,
                  color: ink,
                  icon: locating ? null : Icons.my_location,
                  child: locating
                      ? SizedBox(
                          width: 16,
                          height: 16,
                          child: CircularProgressIndicator(strokeWidth: 2, color: ink),
                        )
                      : null,
                ),
            ],
          ),
          const SizedBox(height: 10),
          SizedBox(
            height: 28,
            child: ListView.separated(
              scrollDirection: Axis.horizontal,
              itemCount: stats.length,
              separatorBuilder: (_, _) => const SizedBox(width: 6),
              itemBuilder: (context, index) => _Pill(text: stats[index], dark: dark, ink: ink),
            ),
          ),
          if (weather.forecast.length > 1) ...[
            const SizedBox(height: 8),
            SizedBox(
              height: 52,
              child: ListView.separated(
                scrollDirection: Axis.horizontal,
                itemCount: weather.forecast.length,
                separatorBuilder: (_, _) => const SizedBox(width: 6),
                itemBuilder: (context, index) {
                  final day = weather.forecast[index];
                  return _DayTile(
                    label: DateFormat.E().format(day.date),
                    range: '${day.low.round()}–${day.high.round()}°',
                    code: _codeForCondition(day.condition),
                    dark: dark,
                    ink: ink,
                    muted: muted,
                  );
                },
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _WeatherBadge extends StatelessWidget {
  const _WeatherBadge({required this.code, required this.dark});

  final int code;
  final bool dark;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: dark ? 0.08 : 0.72),
        shape: BoxShape.circle,
      ),
      child: SizedBox(
        width: 42,
        height: 42,
        child: Icon(_iconForCode(code), color: AppColors.primary, size: 22),
      ),
    );
  }
}

class _Action extends StatelessWidget {
  const _Action({
    required this.tooltip,
    required this.onPressed,
    required this.color,
    this.icon,
    this.child,
  });

  final String tooltip;
  final VoidCallback? onPressed;
  final Color color;
  final IconData? icon;
  final Widget? child;

  @override
  Widget build(BuildContext context) {
    return IconButton(
      tooltip: tooltip,
      visualDensity: VisualDensity.compact,
      padding: EdgeInsets.zero,
      constraints: const BoxConstraints(minWidth: 32, minHeight: 32),
      onPressed: onPressed,
      icon: child ?? Icon(icon, size: 18, color: color),
    );
  }
}

class _Pill extends StatelessWidget {
  const _Pill({required this.text, required this.dark, required this.ink});

  final String text;
  final bool dark;
  final Color ink;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: dark ? 0.08 : 0.7),
        borderRadius: BorderRadius.circular(20),
      ),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 10),
        child: Center(
          child: Text(text, style: TextStyle(color: ink, fontSize: 11, fontWeight: FontWeight.w600)),
        ),
      ),
    );
  }
}

class _DayTile extends StatelessWidget {
  const _DayTile({
    required this.label,
    required this.range,
    required this.code,
    required this.dark,
    required this.ink,
    required this.muted,
  });

  final String label;
  final String range;
  final int code;
  final bool dark;
  final Color ink;
  final Color muted;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: dark ? 0.08 : 0.7),
        borderRadius: BorderRadius.circular(14),
      ),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 10),
        child: Row(
          children: [
            Icon(_iconForCode(code), size: 16, color: AppColors.secondary),
            const SizedBox(width: 6),
            Column(
              mainAxisAlignment: MainAxisAlignment.center,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(label, style: TextStyle(color: muted, fontSize: 10, height: 1.1)),
                Text(range, style: TextStyle(color: ink, fontSize: 12, fontWeight: FontWeight.w700, height: 1.2)),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

IconData _iconForCode(int code) {
  if (code == 0) return Icons.wb_sunny_rounded;
  if (code <= 3) return Icons.wb_cloudy_rounded;
  if (code == 45 || code == 48) return Icons.cloud_rounded;
  if (code >= 71 && code <= 77) return Icons.ac_unit_rounded;
  if (code >= 95) return Icons.thunderstorm_rounded;
  if (code >= 51) return Icons.grain_rounded;
  return Icons.cloud_queue_rounded;
}

int _codeForCondition(String condition) {
  final text = condition.toLowerCase();
  if (text.contains('thunder')) return 95;
  if (text.contains('snow')) return 71;
  if (text.contains('rain') || text.contains('drizzle') || text.contains('shower')) return 61;
  if (text.contains('fog') || text.contains('mist')) return 45;
  if (text.contains('cloud')) return 2;
  if (text.contains('clear') || text.contains('sun')) return 0;
  return 2;
}

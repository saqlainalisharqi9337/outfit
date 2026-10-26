import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:intl/intl.dart';
import 'package:share_plus/share_plus.dart';

import '../../models/outfit_model.dart';
import '../../models/weather_model.dart';
import '../../providers/app_navigation.dart';
import '../../providers/auth_provider.dart';
import '../../providers/recommendation_provider.dart';
import '../../providers/shop_provider.dart';
import '../../providers/wardrobe_provider.dart';
import '../../providers/weather_provider.dart';
import '../../services/nlp_request_parser.dart';
import '../../theme/app_theme.dart';
import '../../utils/enums.dart';
import '../../utils/weather_actions.dart';
import '../../widgets/common.dart';
import '../../widgets/motion.dart';
import '../../widgets/outfit_card.dart';
import '../../widgets/weather_card.dart';
import '../shop/product_detail_screen.dart';

class OutfitScreen extends StatefulWidget {
  const OutfitScreen({
    super.key,
    this.eventWeather,
    this.eventTitle,
    this.eventSubtitle,
  });

  final WeatherModel? eventWeather;
  final String? eventTitle;
  final String? eventSubtitle;

  @override
  State<OutfitScreen> createState() => _OutfitScreenState();
}

class _OutfitScreenState extends State<OutfitScreen> {
  WeatherModel? _customWeather;
  String? _customTitle;
  String? _customSubtitle;

  Future<void> _handleNlpSubmit({
    required NlpOutfitRequest nlp,
    required dynamic user,
    required List<dynamic> wardrobeItems,
    required WeatherModel fallbackWeather,
  }) async {
    final rec = context.read<RecommendationProvider>();
    final weatherProv = context.read<WeatherProvider>();

    WeatherModel targetWeather = fallbackWeather;
    String? targetTitle;
    String? targetSubtitle;

    if (nlp.targetDate != null) {
      final city = targetWeather.city.isNotEmpty
          ? targetWeather.city
          : (user.city?.toString().trim().isNotEmpty == true ? user.city.toString() : 'Lahore');
      final forecast = await weatherProv.forecastForEvent(
        city: city,
        date: nlp.targetDate!,
      );
      if (forecast.weather != null) {
        targetWeather = forecast.weather!;
        final timeStr = DateFormat.MMMd().format(nlp.targetDate!);
        targetTitle = nlp.dateLabel != null ? '${nlp.dateLabel} · $timeStr' : timeStr;
        targetSubtitle = '${targetWeather.condition} · ${targetWeather.temperature.round()}°C';
      }
    } else if (widget.eventWeather == null) {
      // General request (e.g. from Home or current day): strictly use live today's weather
      targetWeather = weatherProv.weather ?? fallbackWeather;
      targetTitle = null;
      targetSubtitle = targetWeather.condition;
    } else {
      // Event-specific request: retain the event context
      targetWeather = widget.eventWeather!;
      targetTitle = widget.eventTitle;
      targetSubtitle = widget.eventSubtitle;
    }

    if (mounted) {
      setState(() {
        _customWeather = targetWeather;
        _customTitle = targetTitle;
        _customSubtitle = targetSubtitle;
      });
    }

    await rec.generate(
      user: user,
      wardrobe: wardrobeItems.cast(),
      weather: targetWeather,
      refresh: true,
      nlp: nlp,
      eventTitle: targetTitle,
      eventSubtitle: targetSubtitle,
    );
  }

  @override
  Widget build(BuildContext context) {
    final rec = context.watch<RecommendationProvider>();
    final weather = context.watch<WeatherProvider>();
    final auth = context.watch<AuthProvider>();
    final wardrobe = context.watch<WardrobeProvider>();
    final user = auth.profile;

    final isEvent = widget.eventWeather != null;
    final displayWeather = _customWeather ??
        widget.eventWeather ??
        (isEvent ? rec.activeWeather : (weather.weather ?? rec.activeWeather));
    final displayTitle = _customTitle ??
        widget.eventTitle ??
        (isEvent ? rec.activeEventTitle : null);
    final displaySubtitle = _customSubtitle ??
        widget.eventSubtitle ??
        (isEvent ? rec.activeEventSubtitle : null) ??
        displayWeather?.condition;

    return Scaffold(
      appBar: AppBar(
        title: Text(displayTitle != null ? 'Event Outfit' : 'Outfit'),
        actions: [
          PopupMenuButton<Occasion>(
            onSelected: (o) {
              if (user != null && displayWeather != null) {
                rec.generate(
                  user: user,
                  wardrobe: wardrobe.items,
                  weather: displayWeather,
                  occasionOverride: o,
                  refresh: true,
                  eventTitle: displayTitle,
                  eventSubtitle: displaySubtitle,
                );
              }
            },
            itemBuilder: (_) => [
              for (final o in Occasion.values)
                PopupMenuItem(value: o, child: Text(o.label)),
            ],
            icon: const Icon(Icons.event_outlined),
          ),
        ],
      ),
      body: Column(
        children: [
          if (user != null && displayWeather != null)
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 8, 20, 0),
              child: _OutfitRequestField(
                enabled: !rec.loading,
                onSubmit: (nlp) => _handleNlpSubmit(
                  nlp: nlp,
                  user: user,
                  wardrobeItems: wardrobe.items,
                  fallbackWeather: displayWeather,
                ),
              ),
            ),
          Expanded(
            child: rec.loading
                ? const LoadingView(message: 'Building complete outfits…')
                : rec.error != null
                    ? ErrorView(
                        message: rec.error!,
                        onRetry: () {
                          if (user != null && displayWeather != null) {
                            rec.generate(
                              user: user,
                              wardrobe: wardrobe.items,
                              weather: displayWeather,
                              eventTitle: displayTitle,
                              eventSubtitle: displaySubtitle,
                            );
                          }
                        },
                      )
                    : rec.result == null
                        ? EmptyView(
                            title: 'No recommendation yet',
                            message: displayWeather == null
                                ? 'Load weather first, then describe what you need and tap Go.'
                                : 'Describe what you need above, or tap generate.',
                            actionLabel: 'Generate',
                            onAction: user == null || displayWeather == null
                                ? null
                                : () => rec.generate(
                                      user: user,
                                      wardrobe: wardrobe.items,
                                      weather: displayWeather,
                                      eventTitle: displayTitle,
                                      eventSubtitle: displaySubtitle,
                                    ),
                          )
                        : SoftBackdrop(
                            child: ListView(
                              padding: EdgeInsets.fromLTRB(20, 20, 20, bottomNavClearance(context)),
                              children: [
                                if (displayWeather != null)
                                  WeatherCard(
                                    weather: displayWeather,
                                    title: displayTitle,
                                    subtitle: displaySubtitle,
                                    onPickLocation: widget.eventWeather != null
                                        ? null
                                        : () => openLocationPicker(context),
                                    onUseLiveLocation: widget.eventWeather != null
                                        ? null
                                        : () => promptAndApplyLiveLocation(context),
                                  ),
                                const SizedBox(height: 12),
                                Text('Occasion: ${rec.occasion.label}'),
                                if (rec.result!.emptyWardrobe)
                                  Padding(
                                    padding:
                                        const EdgeInsets.symmetric(vertical: 8),
                                    child: TextButton(
                                      onPressed: () => context
                                          .read<AppNavigation>()
                                          .goTo(AppNavigation.adroble),
                                      child: const Text(
                                        'Your wardrobe is empty — add clothes',
                                      ),
                                    ),
                                  ),
                                const SizedBox(height: 8),
                                ...rec.result!.outfits.asMap().entries.map(
                                      (entry) => FadeSlideIn(
                                        delay: Duration(
                                          milliseconds: 80 * entry.key,
                                        ),
                                        child: Padding(
                                          padding:
                                              const EdgeInsets.only(bottom: 14),
                                          child: OutfitCard(
                                            outfit: entry.value,
                                            onTap: () {
                                              rec.select(entry.value);
                                              Navigator.push(
                                                context,
                                                MaterialPageRoute(
                                                  builder: (_) =>
                                                      OutfitDetailScreen(
                                                    outfit: entry.value,
                                                  ),
                                                ),
                                              );
                                            },
                                          ),
                                        ),
                                      ),
                                    ),
                              ],
                            ),
                          ),
          ),
        ],
      ),
    );
  }
}

class OutfitDetailScreen extends StatelessWidget {
  const OutfitDetailScreen({super.key, required this.outfit});

  final OutfitRecommendation outfit;

  @override
  Widget build(BuildContext context) {
    final rec = context.read<RecommendationProvider>();
    final uid = context.read<AuthProvider>().profile?.id;
    final shop = context.read<ShopProvider>();
    return Scaffold(
      appBar: AppBar(title: Text(outfit.title)),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          Text(
            outfit.fromWardrobe ? 'FROM YOUR WARDROBE' : 'NEW CLOTHING RECOMMENDATIONS',
            style: const TextStyle(
              letterSpacing: 1.1,
              color: AppColors.muted,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 12),
          ...outfit.slots.map((slot) {
            final item = slot.item;
            final missing = slot.missingSuggestion;
            return Card(
              child: ListTile(
                leading: NetworkImageView(
                  url: item?.imageUrl ?? missing?.matchedProduct?.imageUrl ?? '',
                  height: 72,
                  width: 72,
                  fit: BoxFit.contain,
                  openOnTap: true,
                ),
                title: Text(
                  item?.subcategory ?? missing?.title ?? slot.category.label,
                ),
                subtitle: Text(
                  item != null
                      ? '${item.color} · ${item.formality.label}'
                      : missing?.reason ?? 'Missing from wardrobe',
                ),
                trailing: missing?.matchedProduct == null
                    ? null
                    : TextButton(
                        onPressed: () => Navigator.push(
                          context,
                          MaterialPageRoute(
                            builder: (_) => ProductDetailScreen(
                              product: missing!.matchedProduct!,
                            ),
                          ),
                        ),
                        child: const Text('View product'),
                      ),
              ),
            );
          }),
          const SizedBox(height: 16),
          Text('Score ${outfit.breakdown.percent}%',
              style: Theme.of(context).textTheme.titleMedium),
          _bar('Weather', outfit.breakdown.weather),
          _bar('Culture', outfit.breakdown.culture),
          _bar('Occasion', outfit.breakdown.occasion),
          _bar('Color / skin tone', outfit.breakdown.color),
          _bar('Preference', outfit.breakdown.preference),
          _bar('Wardrobe', outfit.breakdown.wardrobe),
          _bar('Body type', outfit.breakdown.bodyType),
          const SizedBox(height: 16),
          const Text('Why we recommend this'),
          ...outfit.explanations.map(
            (e) => ListTile(
              dense: true,
              leading: const Icon(Icons.check_circle, color: AppColors.success),
              title: Text(e),
            ),
          ),
          const SizedBox(height: 12),
          Wrap(
            spacing: 8,
            children: [
              FilledButton.tonal(
                onPressed: uid == null
                    ? null
                    : () => rec.sendFeedback(uid, FeedbackType.like),
                child: const Text('Like'),
              ),
              FilledButton.tonal(
                onPressed: uid == null
                    ? null
                    : () => rec.sendFeedback(uid, FeedbackType.dislike),
                child: const Text('Dislike'),
              ),
              FilledButton.tonal(
                onPressed: uid == null
                    ? null
                    : () => rec.sendFeedback(uid, FeedbackType.save),
                child: const Text('Save'),
              ),
              FilledButton.tonal(
                onPressed: () => SharePlus.instance.share(
                  ShareParams(
                    text:
                        '${outfit.title}\n${outfit.explanations.join('\n')}\nShared from Adore',
                    title: outfit.title,
                  ),
                ),
                child: const Text('Share'),
              ),
            ],
          ),
          const SizedBox(height: 12),
          if (outfit.missingItems.isNotEmpty)
            FilledButton(
              onPressed: () async {
                final product = outfit.missingItems.first.matchedProduct;
                if (product != null && uid != null) {
                  await shop.addToCart(uid, product);
                  if (context.mounted) {
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(content: Text('Added missing item to cart')),
                    );
                  }
                }
              },
              child: const Text('Add missing item to cart'),
            ),
        ],
      ),
    );
  }

  Widget _bar(String label, double value) {
    return Padding(
      padding: const EdgeInsets.only(top: 8),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('$label ${(value * 100).round()}%'),
          LinearProgressIndicator(value: value.clamp(0, 1)),
        ],
      ),
    );
  }
}

class _OutfitRequestField extends StatefulWidget {
  const _OutfitRequestField({required this.onSubmit, this.enabled = true});

  final void Function(NlpOutfitRequest request) onSubmit;
  final bool enabled;

  @override
  State<_OutfitRequestField> createState() => _OutfitRequestFieldState();
}

class _OutfitRequestFieldState extends State<_OutfitRequestField> {
  final _controller = TextEditingController();
  String? _hint;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  void _run() {
    final text = _controller.text.trim();
    if (text.isEmpty) {
      setState(() {
        _hint = 'Describe what you need, e.g. usual clothes, or a jacket with a shirt.';
      });
      return;
    }
    final parsed = const NlpRequestParser().parse(text);
    final details = <String>[
      if (parsed.dateLabel != null) 'Day: ${parsed.dateLabel}',
      if (parsed.occasion != null) 'Event: ${parsed.occasion!.label}',
      if (parsed.everyday && parsed.occasion == Occasion.casualDayOut) 'Everyday wear',
      if (parsed.style != null) 'Style: ${parsed.style}',
      if (parsed.garmentHints.isNotEmpty) 'Clothes: ${parsed.garmentHints.join(', ')}',
      if (parsed.weatherBand != null) 'Weather: ${parsed.weatherBand!.label}',
      if (parsed.rainy) 'Rain',
      if (parsed.modest == true) 'Modest',
      if (parsed.colors.isNotEmpty) 'Colors: ${parsed.colors.join(', ')}',
    ];
    setState(() {
      _hint = details.isEmpty
          ? 'No event type found. Name one, such as wedding, office, party, or interview. Your profile and weather are still used.'
          : details.join(' · ');
    });
    widget.onSubmit(parsed);
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(
              child: TextField(
                controller: _controller,
                enabled: widget.enabled,
                minLines: 1,
                maxLines: 3,
                textInputAction: TextInputAction.send,
                decoration: const InputDecoration(
                  labelText: 'Describe what you need',
                  hintText:
                      'Usual clothes to wear, or a shirt with a jacket for the office',
                ),
                onSubmitted: widget.enabled ? (_) => _run() : null,
              ),
            ),
            const SizedBox(width: 8),
            Padding(
              padding: const EdgeInsets.only(top: 6),
              child: FilledButton(
                onPressed: widget.enabled ? _run : null,
                child: const Text('Go'),
              ),
            ),
          ],
        ),
        if (_hint != null)
          Padding(
            padding: const EdgeInsets.only(top: 6),
            child: Text(_hint!, style: const TextStyle(color: AppColors.muted)),
          ),
      ],
    );
  }
}

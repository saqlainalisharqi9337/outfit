import 'package:flutter/foundation.dart';

import '../models/outfit_model.dart';
import '../models/product_model.dart';
import '../models/user_model.dart';
import '../models/wardrobe_item.dart';
import '../models/weather_model.dart';
import '../services/feedback_service.dart';
import '../services/nlp_request_parser.dart';
import '../services/recommendation_service.dart';
import '../services/shopping_service.dart';
import '../services/trends_service.dart';
import '../utils/enums.dart';

class RecommendationProvider extends ChangeNotifier {
  RecommendationProvider({
    required RecommendationService recommendationService,
    required FeedbackService feedbackService,
    required ShoppingService shoppingService,
    required TrendsService trendsService,
  })  : _recommendationService = recommendationService,
        _feedbackService = feedbackService,
        _shoppingService = shoppingService,
        _trendsService = trendsService;

  final RecommendationService _recommendationService;
  final FeedbackService _feedbackService;
  final ShoppingService _shoppingService;
  final TrendsService _trendsService;

  RecommendationResult? result;
  WeatherModel? activeWeather;
  String? activeEventTitle;
  String? activeEventSubtitle;
  bool loading = false;
  String? error;
  Occasion occasion = Occasion.casualDayOut;
  OutfitRecommendation? selected;
  int _rotation = 0;
  final _shownIds = <String>[];

  void clearEventContext() {
    activeEventTitle = null;
    activeEventSubtitle = null;
    activeWeather = null;
  }

  Future<void> generate({
    required UserModel user,
    required List<WardrobeItem> wardrobe,
    required WeatherModel weather,
    Occasion? occasionOverride,
    bool refresh = false,
    NlpOutfitRequest? nlp,
    String? eventTitle,
    String? eventSubtitle,
  }) async {
    if (loading) return;
    activeWeather = weather;
    activeEventTitle = eventTitle;
    activeEventSubtitle = eventSubtitle;
    occasion = nlp?.occasion ??
        occasionOverride ??
        (user.preferences.preferredOccasions.isNotEmpty
            ? user.preferences.preferredOccasions.first
            : occasion);
    // Profile gender always wins. NLP "for her" / "for him" is ignored when
    // the user already set male or female.
    var scoringUser = user;
    if ((user.gender == null || user.gender == Gender.preferNotToSay) &&
        nlp?.gender != null) {
      scoringUser = user.copyWith(gender: nlp!.gender);
    }
    if (refresh) {
      _rotation = DateTime.now().microsecondsSinceEpoch;
    }
    loading = true;
    error = null;
    notifyListeners();
    try {
      List<OutfitFeedback> feedback = const [];
      try {
        feedback = await _feedbackService.list(user.id);
      } catch (_) {}
      final products = await _shoppingService.loadProducts();
      final trends = _trendsService.forUser(
        await _trendsService.loadTrends(),
        user,
      );
      result = await _recommendationService.recommend(
        user: scoringUser,
        wardrobe: wardrobe,
        weather: weather,
        occasion: occasion,
        feedback: feedback,
        trends: trends,
        products: products,
        rotation: _rotation,
        excludeIds: refresh ? _shownIds.toSet() : const {},
        weatherBandOverride: nlp?.weatherBand,
        rainyOverride: nlp == null ? null : nlp.rainy ? true : null,
        modestOverride: nlp?.modest,
        extraFavoriteColors: nlp?.colors ?? const [],
        styleHint: nlp?.style,
        wantsOuterwear: nlp?.wantsOuterwear ?? false,
        garmentHints: nlp?.garmentHints ?? const [],
      );
      selected = result!.outfits.isEmpty ? null : result!.outfits.first;
      _shownIds.addAll(result!.outfits.map((o) => o.id));
      if (_shownIds.length > 40) {
        _shownIds.removeRange(0, _shownIds.length - 40);
      }
    } catch (e) {
      error = 'Could not generate outfits. Please retry.';
      result = null;
    } finally {
      loading = false;
      notifyListeners();
    }
  }

  void select(OutfitRecommendation outfit) {
    selected = outfit;
    notifyListeners();
  }

  Future<void> sendFeedback(String uid, FeedbackType type) async {
    final outfit = selected;
    if (outfit == null) return;
    try {
      await _feedbackService.record(uid: uid, outfit: outfit, type: type);
    } catch (_) {}
  }
}

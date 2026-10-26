import 'dart:async';

import '../config/demo_account.dart';
import '../models/product_model.dart';
import '../models/user_model.dart';
import '../models/wardrobe_item.dart';
import '../utils/enums.dart';

/// In-app FYP session used when Supabase Auth cannot create/sign-in users
/// (email rate limit, missing SQL, confirm-email). Weather still uses Open-Meteo.
class DemoStore {
  DemoStore._();
  static final DemoStore instance = DemoStore._();

  static const String userId = '11111111-1111-4111-8111-111111111111';

  bool active = false;
  late UserModel profile;
  final List<WardrobeItem> wardrobe = [];
  final List<EventModel> events = [];
  final List<CartItem> cart = [];
  final List<OrderModel> orders = [];
  final List<OutfitFeedback> feedback = [];
  final List<Map<String, dynamic>> favorites = [];

  final StreamController<List<WardrobeItem>> wardrobeCtrl =
      StreamController<List<WardrobeItem>>.broadcast();
  final StreamController<List<EventModel>> eventsCtrl =
      StreamController<List<EventModel>>.broadcast();
  final StreamController<List<CartItem>> cartCtrl =
      StreamController<List<CartItem>>.broadcast();

  Stream<List<WardrobeItem>> watchWardrobe() async* {
    yield List.of(wardrobe);
    yield* wardrobeCtrl.stream;
  }

  Stream<List<EventModel>> watchEvents() async* {
    yield List.of(events);
    yield* eventsCtrl.stream;
  }

  Stream<List<CartItem>> watchCart() async* {
    yield List.of(cart);
    yield* cartCtrl.stream;
  }

  void start() {
    active = true;
    profile = UserModel(
      id: userId,
      name: DemoAccount.name,
      email: DemoAccount.email,
      gender: Gender.female,
      culture: Culture.pakistani,
      skinTone: SkinTone.medium,
      bodyType: BodyType.hourglass,
      country: 'Pakistan',
      countryCode: 'PK',
      city: 'Muzaffarabad',
      latitude: 34.3704,
      longitude: 73.4707,
      onboardingComplete: true,
      notificationsEnabled: true,
      createdAt: DateTime.now(),
      preferences: const UserPreferences(
        preferredStyles: ['kurta', 'trousers', 'dupatta', 'shirt', 'sneakers'],
        favoriteColors: ['navy', 'cream', 'white', 'maroon'],
        preferredOccasions: [
          Occasion.university,
          Occasion.casualDayOut,
          Occasion.office,
          Occasion.religiousEvent,
        ],
        modestPreference: true,
        weatherPreference: 'mild',
      ),
    );
    wardrobe
      ..clear()
      ..addAll(_seedWardrobe());
    events
      ..clear()
      ..addAll(_seedEvents());
    cart.clear();
    orders.clear();
    feedback.clear();
    favorites.clear();
    wardrobeCtrl.add(List.of(wardrobe));
    eventsCtrl.add(List.of(events));
    cartCtrl.add(List.of(cart));
  }

  void stop() {
    active = false;
    wardrobe.clear();
    events.clear();
    cart.clear();
    orders.clear();
    feedback.clear();
    favorites.clear();
  }

  void emitWardrobe() => wardrobeCtrl.add(List.of(wardrobe));
  void emitEvents() => eventsCtrl.add(List.of(events));
  void emitCart() => cartCtrl.add(List.of(cart));

  List<WardrobeItem> _seedWardrobe() {
    WardrobeItem make({
      required String id,
      required String imageUrl,
      required ClothingCategory category,
      required String subcategory,
      required String color,
      Formality formality = Formality.casual,
      String style = 'casual',
    }) {
      return WardrobeItem.inferred(
        itemId: id,
        userId: userId,
        imageUrl: imageUrl,
        category: category,
        subcategory: subcategory,
        color: color,
        culture: Culture.pakistani,
      ).copyWith(formality: formality, style: style);
    }

    return [
      make(
        id: 'w1',
        imageUrl:
            'https://images.unsplash.com/photo-1603252109303-2751441dd157?auto=format&fit=crop&w=800&q=80',
        category: ClothingCategory.upperwear,
        subcategory: 'kurta',
        color: 'cream',
        formality: Formality.smartCasual,
        style: 'traditional',
      ),
      make(
        id: 'w2',
        imageUrl:
            'https://images.unsplash.com/photo-1594938291221-94d21d8d7c30?auto=format&fit=crop&w=800&q=80',
        category: ClothingCategory.lowerwear,
        subcategory: 'shalwar',
        color: 'white',
        style: 'traditional',
      ),
      make(
        id: 'w3',
        imageUrl:
            'https://images.unsplash.com/photo-1520975954732-6080389a1a0d?auto=format&fit=crop&w=800&q=80',
        category: ClothingCategory.accessories,
        subcategory: 'dupatta',
        color: 'beige',
        formality: Formality.religious,
        style: 'modest',
      ),
      make(
        id: 'w4',
        imageUrl:
            'https://images.unsplash.com/photo-1473966968600-fa801b869a1a?auto=format&fit=crop&w=800&q=80',
        category: ClothingCategory.lowerwear,
        subcategory: 'trousers',
        color: 'navy',
        formality: Formality.smartCasual,
        style: 'smart',
      ),
      make(
        id: 'w5',
        imageUrl:
            'https://images.unsplash.com/photo-1596755094514-f87e34085b2c?auto=format&fit=crop&w=800&q=80',
        category: ClothingCategory.upperwear,
        subcategory: 'shirt',
        color: 'blue',
        formality: Formality.smartCasual,
        style: 'smart',
      ),
      make(
        id: 'w6',
        imageUrl:
            'https://images.unsplash.com/photo-1542291026-7eec264c27ff?auto=format&fit=crop&w=800&q=80',
        category: ClothingCategory.footwear,
        subcategory: 'sneakers',
        color: 'white',
      ),
      make(
        id: 'w7',
        imageUrl:
            'https://images.unsplash.com/photo-1591047139829-d91aecb6caea?auto=format&fit=crop&w=800&q=80',
        category: ClothingCategory.upperwear,
        subcategory: 'jacket',
        color: 'black',
      ),
      make(
        id: 'w8',
        imageUrl:
            'https://images.unsplash.com/photo-1541099649105-f69ad21f3246?auto=format&fit=crop&w=800&q=80',
        category: ClothingCategory.lowerwear,
        subcategory: 'jeans',
        color: 'blue',
      ),
      make(
        id: 'w9',
        imageUrl:
            'https://images.unsplash.com/photo-1520903920243-00d33943e400?auto=format&fit=crop&w=800&q=80',
        category: ClothingCategory.accessories,
        subcategory: 'scarf',
        color: 'maroon',
      ),
      make(
        id: 'w10',
        imageUrl:
            'https://images.unsplash.com/photo-1556821840-3a63f95609a7?auto=format&fit=crop&w=800&q=80',
        category: ClothingCategory.upperwear,
        subcategory: 'hoodie',
        color: 'olive',
        style: 'streetwear',
      ),
    ];
  }

  List<EventModel> _seedEvents() {
    return [
      EventModel(
        id: 'e1',
        name: 'CS lecture',
        dateTime: DateTime.now().add(const Duration(days: 1)),
        occasion: Occasion.university,
        location: 'UAJ&K Muzaffarabad',
        notes: 'Smart-casual, modest university look.',
      ),
      EventModel(
        id: 'e2',
        name: 'Family gathering',
        dateTime: DateTime.now().add(const Duration(days: 3)),
        occasion: Occasion.religiousEvent,
        location: 'Home, Muzaffarabad',
        notes: 'Kurta, shalwar, and dupatta.',
      ),
      EventModel(
        id: 'e3',
        name: 'Department presentation',
        dateTime: DateTime.now().add(const Duration(days: 6)),
        occasion: Occasion.office,
        location: 'Faculty of Engineering',
        notes: 'Navy trousers and blue shirt.',
      ),
    ];
  }
}

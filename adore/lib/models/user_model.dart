import '../utils/clothing_catalog.dart';
import '../utils/enums.dart';
import '../utils/json_helpers.dart';

class UserPreferences {
  const UserPreferences({
    this.preferredStyles = const [],
    this.favoriteColors = const [],
    this.preferredOccasions = const [],
    this.excludedItemTypes = const [],
    this.excludedStyles = const [],
    this.modestPreference = false,
    this.weatherPreference,
    this.overrideCultureDefaults = false,
    this.clothingSize,
    this.braSize,
  });

  final List<String> preferredStyles;
  final List<String> favoriteColors;
  final List<Occasion> preferredOccasions;
  final List<String> excludedItemTypes;
  final List<String> excludedStyles;
  final bool modestPreference;
  final String? weatherPreference;
  final bool overrideCultureDefaults;
  final String? clothingSize;
  final String? braSize;

  factory UserPreferences.fromMap(Map<String, dynamic>? map) {
    if (map == null) return const UserPreferences();
    return UserPreferences(
      preferredStyles: stringList(pick(map, 'preferred_styles', 'preferredStyles')),
      favoriteColors: stringList(pick(map, 'favorite_colors', 'favoriteColors')),
      preferredOccasions: stringList(pick(map, 'preferred_occasions', 'preferredOccasions'))
          .map((e) => enumFromString(Occasion.values, e, Occasion.casualDayOut))
          .toList(),
      excludedItemTypes: stringList(pick(map, 'excluded_item_types', 'excludedItemTypes')),
      excludedStyles: stringList(pick(map, 'excluded_styles', 'excludedStyles')),
      modestPreference: pick(map, 'modest_preference', 'modestPreference') == true,
      weatherPreference: pick(map, 'weather_preference', 'weatherPreference') as String?,
      overrideCultureDefaults:
          pick(map, 'override_culture_defaults', 'overrideCultureDefaults') == true,
      clothingSize: pick(map, 'clothing_size', 'clothingSize') as String?,
      braSize: pick(map, 'bra_size', 'braSize') as String?,
    );
  }

  Map<String, dynamic> toMap() => {
        'preferred_styles': preferredStyles,
        'favorite_colors': favoriteColors,
        'preferred_occasions': preferredOccasions.map((e) => e.name).toList(),
        'excluded_item_types': excludedItemTypes,
        'excluded_styles': excludedStyles,
        'modest_preference': modestPreference,
        'weather_preference': weatherPreference,
        'override_culture_defaults': overrideCultureDefaults,
        'clothing_size': clothingSize,
        'bra_size': braSize,
      };

  UserPreferences copyWith({
    List<String>? preferredStyles,
    List<String>? favoriteColors,
    List<Occasion>? preferredOccasions,
    List<String>? excludedItemTypes,
    List<String>? excludedStyles,
    bool? modestPreference,
    String? weatherPreference,
    bool? overrideCultureDefaults,
    String? clothingSize,
    String? braSize,
    bool clearBraSize = false,
  }) {
    return UserPreferences(
      preferredStyles: preferredStyles ?? this.preferredStyles,
      favoriteColors: favoriteColors ?? this.favoriteColors,
      preferredOccasions: preferredOccasions ?? this.preferredOccasions,
      excludedItemTypes: excludedItemTypes ?? this.excludedItemTypes,
      excludedStyles: excludedStyles ?? this.excludedStyles,
      modestPreference: modestPreference ?? this.modestPreference,
      weatherPreference: weatherPreference ?? this.weatherPreference,
      overrideCultureDefaults:
          overrideCultureDefaults ?? this.overrideCultureDefaults,
      clothingSize: clothingSize ?? this.clothingSize,
      braSize: clearBraSize ? null : (braSize ?? this.braSize),
    );
  }
}

class UserModel {
  const UserModel({
    required this.id,
    required this.name,
    required this.email,
    this.profileImageUrl,
    this.gender,
    this.culture,
    this.skinTone,
    this.bodyType,
    this.country,
    this.countryCode,
    this.city,
    this.latitude,
    this.longitude,
    this.preferences = const UserPreferences(),
    this.onboardingComplete = false,
    this.notificationsEnabled = true,
    this.createdAt,
  });

  final String id;
  final String name;
  final String email;
  final String? profileImageUrl;
  final Gender? gender;
  final Culture? culture;
  final SkinTone? skinTone;
  final BodyType? bodyType;
  final String? country;
  final String? countryCode;
  final String? city;
  final double? latitude;
  final double? longitude;
  final UserPreferences preferences;
  final bool onboardingComplete;
  final bool notificationsEnabled;
  final DateTime? createdAt;

  factory UserModel.fromMap(String id, Map<String, dynamic> data) {
    return UserModel(
      id: (pick(data, 'id') as String?) ?? id,
      name: pick(data, 'name') as String? ?? '',
      email: pick(data, 'email') as String? ?? '',
      profileImageUrl:
          pick(data, 'profile_image_url', 'profileImageUrl') as String?,
      gender: pick(data, 'gender') == null
          ? null
          : enumFromString(Gender.values, pick(data, 'gender') as String?, Gender.preferNotToSay),
      culture: pick(data, 'culture') == null
          ? null
          : enumFromString(Culture.values, pick(data, 'culture') as String?, Culture.other),
      skinTone: pick(data, 'skin_tone', 'skinTone') == null
          ? null
          : enumFromString(
              SkinTone.values,
              pick(data, 'skin_tone', 'skinTone') as String?,
              SkinTone.medium,
            ),
      bodyType: pick(data, 'body_type', 'bodyType') == null
          ? null
          : enumFromString(
              BodyType.values,
              pick(data, 'body_type', 'bodyType') as String?,
              BodyType.rectangle,
            ),
      country: pick(data, 'country') as String?,
      countryCode: pick(data, 'country_code', 'countryCode') as String?,
      city: pick(data, 'city') as String?,
      latitude: (pick(data, 'latitude') as num?)?.toDouble(),
      longitude: (pick(data, 'longitude') as num?)?.toDouble(),
      preferences: UserPreferences.fromMap(asStringKeyedMap(pick(data, 'preferences'))),
      onboardingComplete:
          pick(data, 'onboarding_complete', 'onboardingComplete') == true,
      notificationsEnabled:
          pick(data, 'notifications_enabled', 'notificationsEnabled') != false,
      createdAt: parseDate(pick(data, 'created_at', 'createdAt')),
    );
  }

  Map<String, dynamic> toRow() => {
        'id': id,
        'name': name,
        'email': email,
        'profile_image_url': profileImageUrl,
        'gender': gender?.name,
        'culture': culture?.name,
        'skin_tone': skinTone?.name,
        'body_type': bodyType?.name,
        'country': country,
        'country_code': countryCode,
        'city': city,
        'latitude': latitude,
        'longitude': longitude,
        'preferences': preferences.toMap(),
        'onboarding_complete': onboardingComplete,
        'notifications_enabled': notificationsEnabled,
        'updated_at': DateTime.now().toIso8601String(),
      };

  UserModel copyWith({
    String? name,
    String? profileImageUrl,
    Gender? gender,
    Culture? culture,
    SkinTone? skinTone,
    BodyType? bodyType,
    String? country,
    String? countryCode,
    String? city,
    double? latitude,
    double? longitude,
    UserPreferences? preferences,
    bool? onboardingComplete,
    bool? notificationsEnabled,
  }) {
    return UserModel(
      id: id,
      name: name ?? this.name,
      email: email,
      profileImageUrl: profileImageUrl ?? this.profileImageUrl,
      gender: gender ?? this.gender,
      culture: culture ?? this.culture,
      skinTone: skinTone ?? this.skinTone,
      bodyType: bodyType ?? this.bodyType,
      country: country ?? this.country,
      countryCode: countryCode ?? this.countryCode,
      city: city ?? this.city,
      latitude: latitude ?? this.latitude,
      longitude: longitude ?? this.longitude,
      preferences: preferences ?? this.preferences,
      onboardingComplete: onboardingComplete ?? this.onboardingComplete,
      notificationsEnabled: notificationsEnabled ?? this.notificationsEnabled,
      createdAt: createdAt,
    );
  }

  List<String> effectivePreferredSubcategories() {
    if (preferences.overrideCultureDefaults || culture == null) {
      final fallback = preferences.preferredStyles.isEmpty
          ? ClothingCatalog.subcategories.values.expand((e) => e)
          : preferences.preferredStyles;
      return ClothingCatalog.genderSafePreferred(
        gender: gender,
        subcategories: fallback,
        culture: culture,
      );
    }
    final cultural = ClothingCatalog.genderSafePreferred(
      gender: gender,
      subcategories: ClothingCatalog.preferredSubcategoriesFor(culture!),
      culture: culture,
    );
    final gendered = ClothingCatalog.preferredSubcategoriesForGender(gender);
    if (preferences.preferredStyles.isEmpty) {
      return {...cultural, ...gendered}.toList();
    }
    return {
      ...cultural,
      ...gendered,
      ...ClothingCatalog.genderSafePreferred(
        gender: gender,
        subcategories: preferences.preferredStyles,
        culture: culture,
      ),
    }.toList();
  }
}

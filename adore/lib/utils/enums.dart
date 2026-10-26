enum Gender { male, female, nonBinary, preferNotToSay }

enum Culture {
  pakistani,
  indian,
  western,
  middleEastern,
  eastAsian,
  african,
  other,
}

enum SkinTone { veryLight, light, medium, tan, brown, deep }

enum BodyType { rectangle, pear, invertedTriangle, hourglass, apple }

enum ClothingCategory { upperwear, lowerwear, footwear, accessories, dress }

enum Season { spring, summer, autumn, winter }

enum WeatherBand { veryCold, cold, mild, hot }

enum Formality { casual, smartCasual, formal, athletic, religious }

enum Occasion {
  casualDayOut,
  university,
  office,
  formalEvent,
  wedding,
  party,
  date,
  sports,
  travel,
  religiousEvent,
  outdoorActivity,
  other,
}

enum FeedbackType { like, dislike, save, ignore, purchase }

enum OrderStatus { pending, confirmed, demoCompleted, cancelled }

extension GenderLabel on Gender {
  String get label => switch (this) {
        Gender.male => 'Male',
        Gender.female => 'Female',
        Gender.nonBinary => 'Non-binary',
        Gender.preferNotToSay => 'Prefer not to say',
      };
}

extension CultureLabel on Culture {
  String get label => switch (this) {
        Culture.pakistani => 'Pakistani',
        Culture.indian => 'Indian',
        Culture.western => 'Western',
        Culture.middleEastern => 'Middle Eastern',
        Culture.eastAsian => 'East Asian',
        Culture.african => 'African',
        Culture.other => 'Other',
      };
}

extension BodyTypeLabel on BodyType {
  String get label => switch (this) {
        BodyType.rectangle => 'Rectangle',
        BodyType.pear => 'Triangle / Pear',
        BodyType.invertedTriangle => 'Inverted triangle',
        BodyType.hourglass => 'Hourglass',
        BodyType.apple => 'Oval / Apple',
      };

  String get hint => switch (this) {
        BodyType.rectangle =>
            'Shoulders, waist and hips similar. Straight cuts and defined waistlines both work.',
        BodyType.pear =>
            'Hips wider than shoulders. Balanced by structured tops and A-line or darker lowerwear.',
        BodyType.invertedTriangle =>
            'Shoulders wider than hips. Balanced by fuller skirts, wide trousers, and softer shoulders.',
        BodyType.hourglass =>
            'Defined waist with similar shoulder and hip width. Fitted and belted silhouettes suit this shape.',
        BodyType.apple =>
            'Fuller midsection. V-necks, empire lines, and structured layers keep the focus off the waist.',
      };
}

extension SkinToneLabel on SkinTone {
  String get label => switch (this) {
        SkinTone.veryLight => 'Very Light',
        SkinTone.light => 'Light',
        SkinTone.medium => 'Medium',
        SkinTone.tan => 'Tan',
        SkinTone.brown => 'Brown',
        SkinTone.deep => 'Deep',
      };
}

extension ClothingCategoryLabel on ClothingCategory {
  String get label => switch (this) {
        ClothingCategory.upperwear => 'Upperwear',
        ClothingCategory.lowerwear => 'Lowerwear',
        ClothingCategory.footwear => 'Footwear',
        ClothingCategory.accessories => 'Accessories',
        ClothingCategory.dress => 'Dress / One-piece',
      };
}

extension OccasionLabel on Occasion {
  String get label => switch (this) {
        Occasion.casualDayOut => 'Casual Day Out',
        Occasion.university => 'University',
        Occasion.office => 'Office',
        Occasion.formalEvent => 'Formal Event',
        Occasion.wedding => 'Wedding',
        Occasion.party => 'Party',
        Occasion.date => 'Date',
        Occasion.sports => 'Sports',
        Occasion.travel => 'Travel',
        Occasion.religiousEvent => 'Religious Event',
        Occasion.outdoorActivity => 'Outdoor Activity',
        Occasion.other => 'Other',
      };
}

extension SeasonLabel on Season {
  String get label => switch (this) {
        Season.spring => 'Spring',
        Season.summer => 'Summer',
        Season.autumn => 'Autumn',
        Season.winter => 'Winter',
      };
}

extension FormalityLabel on Formality {
  String get label => switch (this) {
        Formality.casual => 'Casual',
        Formality.smartCasual => 'Smart casual',
        Formality.formal => 'Formal',
        Formality.athletic => 'Athletic',
        Formality.religious => 'Religious / modest',
      };
}

extension WeatherBandLabel on WeatherBand {
  String get label => switch (this) {
        WeatherBand.veryCold => 'Very cold',
        WeatherBand.cold => 'Cold',
        WeatherBand.mild => 'Mild',
        WeatherBand.hot => 'Hot',
      };
}

T enumFromString<T extends Enum>(List<T> values, String? raw, T fallback) {
  if (raw == null) return fallback;
  for (final value in values) {
    if (value.name == raw) return value;
  }
  return fallback;
}

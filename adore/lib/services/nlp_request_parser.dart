import '../utils/clothing_catalog.dart';
import '../utils/enums.dart';

/// Converts a short natural-language outfit request into filters.
/// This is a keyword parser, not a trained language model.
class NlpOutfitRequest {
  const NlpOutfitRequest({
    required this.raw,
    this.occasion,
    this.weatherBand,
    this.rainy = false,
    this.modest,
    this.colors = const [],
    this.style,
    this.gender,
    this.wantsOuterwear = false,
    this.garmentHints = const [],
    this.everyday = false,
    this.targetDate,
    this.dateLabel,
  });

  final String raw;
  final Occasion? occasion;
  final WeatherBand? weatherBand;
  final bool rainy;
  final bool? modest;
  final List<String> colors;
  final String? style;
  final Gender? gender;
  final bool wantsOuterwear;
  final List<String> garmentHints;
  final bool everyday;
  final DateTime? targetDate;
  final String? dateLabel;

  bool get hasFilters =>
      occasion != null ||
      weatherBand != null ||
      rainy ||
      modest != null ||
      colors.isNotEmpty ||
      style != null ||
      gender != null ||
      wantsOuterwear ||
      garmentHints.isNotEmpty ||
      everyday ||
      targetDate != null;

  String get summary {
    final bits = <String>[
      ?dateLabel,
      if (everyday && occasion == Occasion.casualDayOut) 'everyday wear',
      if (occasion != null && !(everyday && occasion == Occasion.casualDayOut))
        occasion!.label,
      if (weatherBand != null) weatherBand!.label,
      if (rainy) 'rain',
      if (modest == true) 'modest',
      ...colors,
      ?style,
      if (wantsOuterwear) 'jacket / blazer layer',
      ...garmentHints,
    ];
    return bits.isEmpty ? 'your profile, weather, and wardrobe' : bits.join(' · ');
  }
}

class NlpRequestParser {
  const NlpRequestParser();

  NlpOutfitRequest parse(String raw) {
    final text = raw.toLowerCase();
    final everyday = _everyday(text);
    final occasion = _occasion(text) ?? (everyday ? Occasion.casualDayOut : null);
    final dateInfo = _parseTargetDate(text);
    return NlpOutfitRequest(
      raw: raw.trim(),
      occasion: occasion,
      weatherBand: _weather(text),
      rainy: _has(text, const ['rain', 'rainy', 'wet weather', 'drizzle']),
      modest: _modest(text),
      colors: _colors(text),
      style: _style(text) ?? (everyday ? 'casual' : null),
      gender: _gender(text),
      wantsOuterwear: _wantsOuterwear(text),
      garmentHints: _garments(text),
      everyday: everyday,
      targetDate: dateInfo.targetDate,
      dateLabel: dateInfo.dateLabel,
    );
  }

  bool _everyday(String text) {
    return _has(text, const [
      'usual',
      'everyday',
      'daily',
      'normal clothes',
      'regular clothes',
      'casual clothes',
      'what should i wear',
      'what to wear',
      'recommend an outfit',
      'recommend outfit',
      'clothes to wear',
      'something to wear',
      'for today',
      'day to day',
      'day-to-day',
    ]);
  }

  bool _wantsOuterwear(String text) {
    return _has(text, const [
      'jacket',
      'jackets',
      'blazer',
      'blazers',
      'lazer',
      'lazers',
      'layer',
      'layers',
      'layered',
      'overshirt',
      'coat',
    ]);
  }

  List<String> _garments(String text) {
    const names = [
      'shirt',
      'shirts',
      't-shirt',
      'tshirt',
      'jeans',
      'trousers',
      'pants',
      'dress',
      'sneakers',
      'heels',
      'kurta',
    ];
    final found = <String>[];
    for (final name in names) {
      if (_has(text, [name])) {
        final mapped = switch (name) {
          'shirts' => 'shirt',
          'tshirt' => 't-shirt',
          'pants' => 'trousers',
          'lazers' || 'lazer' => 'blazer',
          _ => name,
        };
        if (!found.contains(mapped)) found.add(mapped);
      }
    }
    return found;
  }

  Occasion? _occasion(String text) {
    if (_has(text, const [
      'wedding',
      'marriage',
      'nikah',
      'nikkah',
      'baraat',
      'shaadi',
      'walima',
      'mehndi',
      'engagement',
    ])) {
      return Occasion.wedding;
    }
    if (_has(text, const ['university', 'college', 'campus', 'lecture', 'class'])) {
      return Occasion.university;
    }
    if (_has(text, const ['office', 'work', 'meeting', 'interview', 'business', 'clients'])) {
      return Occasion.office;
    }
    if (_has(text, const ['mosque', 'church', 'temple', 'religious', 'eid', 'jummah'])) {
      return Occasion.religiousEvent;
    }
    if (_has(text, const ['gym', 'workout', 'sports', 'run', 'training'])) {
      return Occasion.sports;
    }
    if (_has(text, const ['hike', 'hiking', 'picnic', 'outdoor', 'beach', 'seaside'])) {
      return Occasion.outdoorActivity;
    }
    if (_has(text, const ['travel', 'airport', 'trip', 'flight'])) {
      return Occasion.travel;
    }
    if (_has(text, const ['family gathering', 'with my family', 'with family'])) {
      return Occasion.casualDayOut;
    }
    if (_has(text, const ['romantic dinner', 'date night', 'dinner date', 'date'])) {
      return Occasion.date;
    }
    if (_has(text, const ['party', 'birthday', 'club'])) {
      return Occasion.party;
    }
    if (_has(text, const ['formal', 'black tie', 'gala'])) {
      return Occasion.formalEvent;
    }
    if (_has(text, const ['casual', 'hang out', 'day out', 'weekend'])) {
      return Occasion.casualDayOut;
    }
    return null;
  }

  WeatherBand? _weather(String text) {
    if (_has(text, const ['freezing', 'very cold', 'snow', 'subzero'])) {
      return WeatherBand.veryCold;
    }
    if (_has(text, const ['cold', 'chilly', 'winter', 'cool'])) {
      return WeatherBand.cold;
    }
    if (_has(text, const [
      'hot',
      'warm',
      'humid',
      'heat',
      'scorching',
      'summer',
      'sunny',
      'warm weather',
      'warm time',
      'warm day',
    ])) {
      return WeatherBand.hot;
    }
    if (_has(text, const ['mild', 'pleasant', 'spring', 'breezy', 'moderate'])) {
      return WeatherBand.mild;
    }
    return null;
  }

  bool? _modest(String text) {
    if (_has(text, const ['modest', 'conservative', 'covered', 'hijab-friendly'])) {
      return true;
    }
    return null;
  }

  List<String> _colors(String text) {
    final found = <String>[];
    for (final color in ClothingCatalog.colors) {
      if (RegExp('\\b${RegExp.escape(color)}\\b').hasMatch(text)) {
        found.add(color);
      }
    }
    return found;
  }

  String? _style(String text) {
    for (final style in ClothingCatalog.styles) {
      if (text.contains(style)) return style;
    }
    if (_has(text, const ['sporty', 'athletic'])) return 'sporty';
    if (_has(text, const ['business', 'professional'])) return 'smart';
    if (_has(text, const ['streetwear', 'street'])) return 'streetwear';
    if (_has(text, const ['traditional', 'ethnic'])) return 'traditional';
    if (_has(text, const ['formal look', 'formal outfit'])) return 'formal';
    if (_has(text, const ['party look'])) return 'formal';
    return null;
  }

  Gender? _gender(String text) {
    if (_has(text, const ["men's", 'mens', 'for him', 'for a man', 'male'])) {
      return Gender.male;
    }
    if (_has(text, const ["women's", 'womens', 'for her', 'for a woman', 'female'])) {
      return Gender.female;
    }
    return null;
  }

  bool _has(String text, List<String> needles) {
    for (final needle in needles) {
      if (needle.contains(' ')) {
        if (text.contains(needle)) return true;
        continue;
      }
      final pattern = RegExp('\\b${RegExp.escape(needle)}\\b');
      if (pattern.hasMatch(text)) return true;
    }
    return false;
  }

  ({DateTime? targetDate, String? dateLabel}) _parseTargetDate(String text) {
    final now = DateTime.now();
    final today = DateTime(now.year, now.month, now.day, 12);

    if (_has(text, const ['today', 'for today', 'current day', 'now'])) {
      return (targetDate: today, dateLabel: 'Today');
    }
    if (_has(text, const ['day after tomorrow'])) {
      return (
        targetDate: today.add(const Duration(days: 2)),
        dateLabel: 'Day after tomorrow',
      );
    }
    if (_has(text, const ['tomorrow', 'for tomorrow', 'next day'])) {
      return (
        targetDate: today.add(const Duration(days: 1)),
        dateLabel: 'Tomorrow',
      );
    }

    const weekdays = {
      'monday': DateTime.monday,
      'tuesday': DateTime.tuesday,
      'wednesday': DateTime.wednesday,
      'thursday': DateTime.thursday,
      'friday': DateTime.friday,
      'saturday': DateTime.saturday,
      'sunday': DateTime.sunday,
    };

    for (final entry in weekdays.entries) {
      if (RegExp('\\b${entry.key}\\b').hasMatch(text)) {
        int diff = entry.value - today.weekday;
        if (diff <= 0) diff += 7;
        final target = today.add(Duration(days: diff));
        final capitalized = entry.key[0].toUpperCase() + entry.key.substring(1);
        return (targetDate: target, dateLabel: capitalized);
      }
    }

    final inDaysMatch = RegExp(r'\bin\s+(\d+)\s+days?\b').firstMatch(text);
    if (inDaysMatch != null) {
      final days = int.tryParse(inDaysMatch.group(1) ?? '');
      if (days != null && days > 0 && days <= 15) {
        return (
          targetDate: today.add(Duration(days: days)),
          dateLabel: 'In $days days',
        );
      }
    }

    return (targetDate: null, dateLabel: null);
  }
}

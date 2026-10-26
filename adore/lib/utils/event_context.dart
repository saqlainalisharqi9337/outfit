import '../services/nlp_request_parser.dart';
import 'enums.dart';

/// How an event description should affect the outfit occasion.
class EventContext {
  const EventContext({
    required this.primary,
    required this.extracted,
    required this.request,
  });

  /// Selected type when the description is empty or does not name an event.
  final Occasion primary;

  /// Occasion named by the description, when the wording is clear.
  final Occasion? extracted;
  final NlpOutfitRequest request;
}

EventContext resolveEventContext({
  required Occasion selected,
  required String description,
}) {
  final text = description.trim();
  if (text.isEmpty) {
    return EventContext(
      primary: selected,
      extracted: null,
      request: const NlpOutfitRequest(raw: ''),
    );
  }
  final request = NlpRequestParser().parse(text);
  final extracted = request.occasion;
  return EventContext(
    primary: extracted ?? selected,
    extracted: extracted,
    request: NlpOutfitRequest(
      raw: text,
      style: request.style,
      rainy: false,
      garmentHints: request.garmentHints,
      wantsOuterwear: request.wantsOuterwear,
      modest: request.modest,
      colors: request.colors,
      gender: request.gender,
      everyday: false,
    ),
  );
}

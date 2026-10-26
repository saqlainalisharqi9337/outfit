dynamic pick(Map<String, dynamic> data, String snake, [String? camel]) {
  if (data.containsKey(snake) && data[snake] != null) return data[snake];
  if (camel != null && data.containsKey(camel) && data[camel] != null) {
    return data[camel];
  }
  return data[snake] ?? (camel == null ? null : data[camel]);
}

DateTime? parseDate(dynamic value) {
  if (value == null) return null;
  if (value is DateTime) return value;
  return DateTime.tryParse(value.toString());
}

Map<String, dynamic>? asStringKeyedMap(dynamic value) {
  if (value == null) return null;
  if (value is Map<String, dynamic>) return value;
  if (value is Map) {
    return value.map((key, val) => MapEntry(key.toString(), val));
  }
  return null;
}

List<String> stringList(dynamic value) {
  if (value == null) return const [];
  if (value is List) {
    return value.map((e) => e.toString()).toList();
  }
  return const [];
}

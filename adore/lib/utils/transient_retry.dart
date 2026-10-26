/// Retries calls that fail because the phone briefly cannot reach Supabase.
Future<T> retryTransient<T>(Future<T> Function() action) async {
  Object? last;
  for (var attempt = 0; attempt < 3; attempt++) {
    try {
      return await action();
    } catch (e) {
      last = e;
      final text = e.toString().toLowerCase();
      final again = text.contains('failed host lookup') ||
          text.contains('socketexception') ||
          text.contains('no address associated') ||
          text.contains('bad gateway') ||
          text.contains('connection errored') ||
          text.contains('connection reset') ||
          text.contains('connection refused') ||
          text.contains('network is unreachable') ||
          text.contains('timed out') ||
          text.contains('jwt issued at future') ||
          text.contains('pgrst303');
      if (!again || attempt == 2) rethrow;
      await Future<void>.delayed(Duration(seconds: 2 * (attempt + 1)));
    }
  }
  throw last ?? StateError('Request failed.');
}

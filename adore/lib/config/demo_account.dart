/// FYP demo login. Created by SQL (no confirmation email), so it does not
/// hit the Supabase free-plan email rate limit.
class DemoAccount {
  static const String email = 'ayesha@adore.test';
  static const String password = 'AdoreDemo@24';
  static const String name = 'Ayesha Khan';

  static bool matchesEmail(String value) =>
      value.trim().toLowerCase() == email;
}

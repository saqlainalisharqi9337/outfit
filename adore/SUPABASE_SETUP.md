# Connect Adore to Supabase (save all data)

The Flutter app is **already connected** to project `jpjxjggxheafpyyxpftx`
via [lib/config/supabase_config.dart](lib/config/supabase_config.dart).

When you use a **real registered account** (not Local Demo), these are written
to Postgres:

| App data | Supabase table / columns |
|---|---|
| Name, email, gender, culture, skin tone | `profiles` |
| **Body type** | `profiles.body_type` |
| Location, preferences, modesty | `profiles` + `preferences` jsonb |
| Wardrobe items | `wardrobe_items` |
| **Pattern** | `wardrobe_items.pattern` |
| Pattern source / confidence | `pattern_source`, `pattern_confidence` |
| Photos | Storage buckets `avatars`, `wardrobe` |
| Events, cart, orders, favorites, feedback | matching tables |
| Products / trends | seeded tables |

## One-time database setup (required)

1. Open [Supabase Dashboard](https://supabase.com/dashboard) → project **jpjxjggxheafpyyxpftx**
2. **SQL Editor** → New query
3. Paste the entire file: [supabase/SETUP_ALL.sql](supabase/SETUP_ALL.sql)
4. Click **Run** (success = no red errors)
5. **Authentication → Providers → Email** → disable **Confirm email** (easier FYP demos)
6. Restart the Flutter app

### Verify columns exist

In **Table Editor**:

- `profiles` has a **`body_type`** column
- `wardrobe_items` has **`pattern`**, **`pattern_source`**, **`pattern_confidence`**

## How to use the app so data actually saves

1. Tap **Register** with a real email/password (Gmail etc.)
2. Complete onboarding and select **Body type**
3. Add clothing and choose **Pattern**
4. In Supabase Table Editor, refresh `profiles` and `wardrobe_items` — rows should appear

### Local Demo does NOT use Supabase

Login with `ayesha@adore.test` / `AdoreDemo@24` or “Local Demo” keeps data
**only in memory** (`DemoStore`). Log out and register a real account to persist.

## Code path (already implemented)

```
Onboarding / Edit profile
  → AuthProvider.saveProfile(user)
  → UserService.updateUser → profiles upsert (includes body_type)

Add clothing
  → WardrobeProvider.addItem
  → StorageService.upload (wardrobe bucket)
  → WardrobeService.upsert → wardrobe_items upsert (includes pattern)
```

## If save fails

| Error hint | Fix |
|---|---|
| tables / schema cache | Run `SETUP_ALL.sql` again, wait ~30s, restart app |
| missing `body_type` / pattern columns | Run `SETUP_ALL.sql` |
| row-level security | Confirm email off; use a logged-in real user |
| Demo account | Register a new account instead |

## Auth keys

URL and publishable key live in `lib/config/supabase_config.dart`.
Never put the **service role** or database password in the Flutter app.

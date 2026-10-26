-- Complete FYP demo user. Run this in the SQL Editor after the schema migration.
-- Email: ayesha@adore.test
-- Password: AdoreDemo@24
-- Confirmed in-database, so no auth email is sent.

do $$
declare
  uid uuid := '11111111-1111-4111-8111-111111111111';
  demo_email text := 'ayesha@adore.test';
  demo_password text := 'AdoreDemo@24';
begin
  if not exists (
    select 1
    from information_schema.tables
    where table_schema = 'public' and table_name = 'profiles'
  ) then
    raise exception 'Run 20260830000000_adore_schema.sql first, then run this script.';
  end if;

  delete from auth.users where email = demo_email or id = uid;

  insert into auth.users (
    instance_id,
    id,
    aud,
    role,
    email,
    encrypted_password,
    email_confirmed_at,
    recovery_sent_at,
    last_sign_in_at,
    raw_app_meta_data,
    raw_user_meta_data,
    created_at,
    updated_at,
    confirmation_token,
    email_change,
    email_change_token_new,
    recovery_token
  ) values (
    '00000000-0000-0000-0000-000000000000',
    uid,
    'authenticated',
    'authenticated',
    demo_email,
    extensions.crypt(demo_password, extensions.gen_salt('bf')),
    now(),
    now(),
    now(),
    '{"provider":"email","providers":["email"]}'::jsonb,
    '{"name":"Ayesha Khan"}'::jsonb,
    now(),
    now(),
    '',
    '',
    '',
    ''
  );

  insert into auth.identities (
    id,
    user_id,
    identity_data,
    provider,
    provider_id,
    last_sign_in_at,
    created_at,
    updated_at
  ) values (
    gen_random_uuid(),
    uid,
    jsonb_build_object('sub', uid::text, 'email', demo_email),
    'email',
    uid::text,
    now(),
    now(),
    now()
  );

  insert into public.profiles (
    id, name, email, gender, culture, skin_tone,
    country, country_code, city, latitude, longitude,
    preferences, onboarding_complete, notifications_enabled,
    created_at, updated_at
  ) values (
    uid,
    'Ayesha Khan',
    demo_email,
    'female',
    'pakistani',
    'medium',
    'Pakistan',
    'PK',
    'Muzaffarabad',
    34.3704,
    73.4707,
    jsonb_build_object(
      'preferred_styles', jsonb_build_array('kurta', 'trousers', 'dupatta', 'shirt', 'sneakers'),
      'favorite_colors', jsonb_build_array('navy', 'cream', 'white', 'maroon'),
      'preferred_occasions', jsonb_build_array('university', 'casualDayOut', 'office', 'religiousEvent'),
      'excluded_item_types', jsonb_build_array(),
      'excluded_styles', jsonb_build_array(),
      'modest_preference', true,
      'weather_preference', 'mild',
      'override_culture_defaults', false
    ),
    true,
    true,
    now(),
    now()
  )
  on conflict (id) do update set
    name = excluded.name,
    email = excluded.email,
    gender = excluded.gender,
    culture = excluded.culture,
    skin_tone = excluded.skin_tone,
    country = excluded.country,
    country_code = excluded.country_code,
    city = excluded.city,
    latitude = excluded.latitude,
    longitude = excluded.longitude,
    preferences = excluded.preferences,
    onboarding_complete = true,
    notifications_enabled = true,
    updated_at = now();

  delete from public.wardrobe_items where user_id = uid;
  insert into public.wardrobe_items (
    user_id, image_url, category, subcategory, color, pattern, material, style,
    season, formality, culture_compatibility, weather_suitability, occasion, ai_confidence
  ) values
  (uid, 'https://images.unsplash.com/photo-1603252109303-2751441dd157?auto=format&fit=crop&w=800&q=80', 'upperwear', 'kurta', 'cream', 'solid', 'cotton', 'traditional', array['spring','summer'], 'casual', array['pakistani','indian'], array['mild','hot'], array['university','casualDayOut','religiousEvent'], 0.94),
  (uid, 'https://images.unsplash.com/photo-1594938291221-94d21d8d7c30?auto=format&fit=crop&w=800&q=80', 'lowerwear', 'shalwar', 'white', 'solid', 'cotton', 'traditional', array['spring','summer','autumn','winter'], 'casual', array['pakistani','indian'], array['mild','hot','cold'], array['university','casualDayOut','religiousEvent'], 0.91),
  (uid, 'https://images.unsplash.com/photo-1520975954732-6080389a1a0d?auto=format&fit=crop&w=800&q=80', 'accessories', 'dupatta', 'beige', 'solid', 'cotton', 'modest', array['spring','summer','autumn','winter'], 'religious', array['pakistani','indian'], array['mild','hot','cold'], array['university','religiousEvent','formalEvent'], 0.90),
  (uid, 'https://images.unsplash.com/photo-1473966968600-fa801b869a1a?auto=format&fit=crop&w=800&q=80', 'lowerwear', 'trousers', 'navy', 'solid', 'cotton', 'smart', array['spring','summer','autumn','winter'], 'smartCasual', array['western','pakistani'], array['cold','mild','hot'], array['university','office','casualDayOut'], 0.88),
  (uid, 'https://images.unsplash.com/photo-1596755094514-f87e34085b2c?auto=format&fit=crop&w=800&q=80', 'upperwear', 'shirt', 'blue', 'solid', 'cotton', 'smart', array['spring','summer','autumn','winter'], 'smartCasual', array['western','pakistani'], array['mild','cold'], array['university','office'], 0.89),
  (uid, 'https://images.unsplash.com/photo-1542291026-7eec264c27ff?auto=format&fit=crop&w=800&q=80', 'footwear', 'sneakers', 'white', 'solid', 'canvas', 'casual', array['spring','summer','autumn'], 'casual', array['western','pakistani'], array['mild','hot','cold'], array['university','casualDayOut','travel'], 0.92),
  (uid, 'https://images.unsplash.com/photo-1591047139829-d91aecb6caea?auto=format&fit=crop&w=800&q=80', 'upperwear', 'jacket', 'black', 'solid', 'nylon', 'casual', array['autumn','winter','spring'], 'casual', array['western','pakistani'], array['cold','mild','veryCold'], array['university','travel','outdoorActivity'], 0.87),
  (uid, 'https://images.unsplash.com/photo-1541099649105-f69ad21f3246?auto=format&fit=crop&w=800&q=80', 'lowerwear', 'jeans', 'blue', 'solid', 'denim', 'casual', array['autumn','winter','spring'], 'casual', array['western'], array['cold','mild'], array['casualDayOut','university','travel'], 0.86),
  (uid, 'https://images.unsplash.com/photo-1520903920243-00d33943e400?auto=format&fit=crop&w=800&q=80', 'accessories', 'scarf', 'maroon', 'solid', 'wool', 'casual', array['autumn','winter'], 'casual', array['pakistani','western'], array['veryCold','cold'], array['university','travel','outdoorActivity'], 0.85),
  (uid, 'https://images.unsplash.com/photo-1556821840-3a63f95609a7?auto=format&fit=crop&w=800&q=80', 'upperwear', 'hoodie', 'olive', 'solid', 'cotton', 'streetwear', array['autumn','winter'], 'casual', array['western'], array['cold','veryCold'], array['university','casualDayOut','sports'], 0.84);

  delete from public.events where user_id = uid;
  insert into public.events (user_id, name, date_time, occasion, location, notes) values
  (uid, 'CS lecture', now() + interval '1 day', 'university', 'UAJ&K Muzaffarabad', 'Smart-casual, modest university look.'),
  (uid, 'Family gathering', now() + interval '3 days', 'religiousEvent', 'Home, Muzaffarabad', 'Kurta, shalwar, and dupatta.'),
  (uid, 'Department presentation', now() + interval '6 days', 'office', 'Faculty of Engineering', 'Navy trousers and blue shirt.');
end $$;

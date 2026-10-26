-- =============================================================================
-- Adore — paste this once in Supabase Dashboard → SQL Editor → Run
-- Project: jpjxjggxheafpyyxpftx
--
-- Safe to re-run: uses IF NOT EXISTS / DROP POLICY IF EXISTS where needed.
-- This creates all tables AND the body_type / pattern metadata columns.
-- =============================================================================

create extension if not exists "pgcrypto";

-- Profiles (user data: gender, culture, skin tone, BODY TYPE, location, prefs)
create table if not exists public.profiles (
  id uuid primary key references auth.users (id) on delete cascade,
  name text not null default '',
  email text,
  profile_image_url text,
  gender text,
  culture text,
  skin_tone text,
  body_type text,
  country text,
  country_code text,
  city text,
  latitude double precision,
  longitude double precision,
  preferences jsonb not null default '{}'::jsonb,
  onboarding_complete boolean not null default false,
  notifications_enabled boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.profiles add column if not exists body_type text;

-- Wardrobe (clothing items including PATTERN)
create table if not exists public.wardrobe_items (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id) on delete cascade,
  image_url text not null default '',
  category text not null,
  subcategory text not null,
  color text not null,
  secondary_color text,
  pattern text default 'solid',
  pattern_source text default 'user',
  pattern_confidence double precision,
  material text default 'unknown',
  style text default 'casual',
  season text[] not null default '{}',
  formality text default 'casual',
  culture_compatibility text[] not null default '{}',
  weather_suitability text[] not null default '{}',
  occasion text[] not null default '{}',
  ai_confidence double precision,
  created_at timestamptz not null default now()
);

alter table public.wardrobe_items add column if not exists pattern_source text default 'user';
alter table public.wardrobe_items add column if not exists pattern_confidence double precision;

create table if not exists public.events (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id) on delete cascade,
  name text not null,
  date_time timestamptz not null,
  occasion text not null,
  location text,
  notes text,
  created_at timestamptz not null default now()
);

create table if not exists public.favorites (
  id text primary key,
  user_id uuid not null references auth.users (id) on delete cascade,
  title text,
  score double precision,
  item_ids text[] not null default '{}',
  created_at timestamptz not null default now()
);

create table if not exists public.outfit_feedback (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id) on delete cascade,
  outfit_id text not null,
  type text not null,
  colors text[] not null default '{}',
  subcategories text[] not null default '{}',
  created_at timestamptz not null default now()
);

create table if not exists public.products (
  id text primary key,
  name text not null,
  description text not null default '',
  price numeric not null,
  currency text not null default 'PKR',
  image_url text not null default '',
  category text not null,
  subcategory text not null,
  color text not null,
  style text not null default 'casual',
  culture_tags text[] not null default '{}',
  weather_bands text[] not null default '{}',
  season_tags text[] not null default '{}'
);

create table if not exists public.trends (
  id text primary key,
  title text not null,
  subtitle text not null default '',
  description text not null default '',
  image_url text not null default '',
  culture_tags text[] not null default '{}',
  colors text[] not null default '{}',
  item_types text[] not null default '{}',
  season text not null default 'all',
  styling_idea text
);

create table if not exists public.cart_items (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id) on delete cascade,
  product_id text not null,
  name text,
  price numeric,
  image_url text,
  quantity int not null default 1,
  unique (user_id, product_id)
);

create table if not exists public.orders (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id) on delete cascade,
  items jsonb not null default '[]'::jsonb,
  total numeric not null default 0,
  status text not null default 'demoCompleted',
  note text,
  is_simulated_checkout boolean not null default true,
  created_at timestamptz not null default now()
);

alter table public.profiles enable row level security;
alter table public.wardrobe_items enable row level security;
alter table public.events enable row level security;
alter table public.favorites enable row level security;
alter table public.outfit_feedback enable row level security;
alter table public.cart_items enable row level security;
alter table public.orders enable row level security;
alter table public.products enable row level security;
alter table public.trends enable row level security;

drop policy if exists "profiles_own" on public.profiles;
create policy "profiles_own" on public.profiles
  for all using (auth.uid() = id) with check (auth.uid() = id);

drop policy if exists "wardrobe_own" on public.wardrobe_items;
create policy "wardrobe_own" on public.wardrobe_items
  for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

drop policy if exists "events_own" on public.events;
create policy "events_own" on public.events
  for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

drop policy if exists "favorites_own" on public.favorites;
create policy "favorites_own" on public.favorites
  for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

drop policy if exists "feedback_own" on public.outfit_feedback;
create policy "feedback_own" on public.outfit_feedback
  for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

drop policy if exists "cart_own" on public.cart_items;
create policy "cart_own" on public.cart_items
  for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

drop policy if exists "orders_own" on public.orders;
create policy "orders_own" on public.orders
  for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

drop policy if exists "products_read" on public.products;
create policy "products_read" on public.products
  for select using (auth.role() = 'authenticated');

drop policy if exists "trends_read" on public.trends;
create policy "trends_read" on public.trends
  for select using (auth.role() = 'authenticated');

create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.profiles (id, email, name)
  values (
    new.id,
    new.email,
    coalesce(new.raw_user_meta_data ->> 'name', '')
  )
  on conflict (id) do nothing;
  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

insert into storage.buckets (id, name, public)
values ('avatars', 'avatars', true), ('wardrobe', 'wardrobe', true)
on conflict (id) do nothing;

drop policy if exists "avatar_read" on storage.objects;
create policy "avatar_read" on storage.objects
  for select using (bucket_id = 'avatars');

drop policy if exists "wardrobe_read" on storage.objects;
create policy "wardrobe_read" on storage.objects
  for select using (bucket_id = 'wardrobe');

drop policy if exists "avatar_write_own" on storage.objects;
create policy "avatar_write_own" on storage.objects
  for insert with check (
    bucket_id = 'avatars'
    and auth.uid()::text = (storage.foldername(name))[1]
  );

drop policy if exists "wardrobe_write_own" on storage.objects;
create policy "wardrobe_write_own" on storage.objects
  for insert with check (
    bucket_id = 'wardrobe'
    and auth.uid()::text = (storage.foldername(name))[1]
  );

drop policy if exists "avatar_update_own" on storage.objects;
create policy "avatar_update_own" on storage.objects
  for update using (
    bucket_id = 'avatars'
    and auth.uid()::text = (storage.foldername(name))[1]
  );

drop policy if exists "wardrobe_update_own" on storage.objects;
create policy "wardrobe_update_own" on storage.objects
  for update using (
    bucket_id = 'wardrobe'
    and auth.uid()::text = (storage.foldername(name))[1]
  );

drop policy if exists "avatar_delete_own" on storage.objects;
create policy "avatar_delete_own" on storage.objects
  for delete using (
    bucket_id = 'avatars'
    and auth.uid()::text = (storage.foldername(name))[1]
  );

drop policy if exists "wardrobe_delete_own" on storage.objects;
create policy "wardrobe_delete_own" on storage.objects
  for delete using (
    bucket_id = 'wardrobe'
    and auth.uid()::text = (storage.foldername(name))[1]
  );

do $$
begin
  begin
    alter publication supabase_realtime add table public.wardrobe_items;
  exception when duplicate_object then null;
  end;
  begin
    alter publication supabase_realtime add table public.events;
  exception when duplicate_object then null;
  end;
  begin
    alter publication supabase_realtime add table public.cart_items;
  exception when duplicate_object then null;
  end;
  begin
    alter publication supabase_realtime add table public.profiles;
  exception when duplicate_object then null;
  end;
end $$;

insert into public.products (
  id, name, description, price, currency, image_url, category, subcategory, color, style, culture_tags, weather_bands, season_tags
) values
('p1','Black Lightweight Jacket','Light layering jacket for cold and mild weather. Useful when a wardrobe has no suitable outerwear.',4990,'PKR','https://images.unsplash.com/photo-1591047139829-d91aecb6caea?auto=format&fit=crop&w=800&q=80','upperwear','jacket','black','casual',array['western','pakistani','indian','other'],array['cold','mild','veryCold'],array['autumn','winter','spring']),
('p2','Ivory Cotton Kurta','Breathable kurta suitable for mild and hot weather and cultural everyday wear.',3290,'PKR','https://images.unsplash.com/photo-1603252109303-2751441dd157?auto=format&fit=crop&w=800&q=80','upperwear','kurta','cream','traditional',array['pakistani','indian'],array['mild','hot'],array['spring','summer']),
('p3','Navy Chino Trousers','Smart-casual trousers for university and office looks.',2890,'PKR','https://images.unsplash.com/photo-1473966968600-fa801b869a1a?auto=format&fit=crop&w=800&q=80','lowerwear','trousers','navy','smart',array['western','pakistani','other'],array['cold','mild','hot'],array['all']),
('p4','White Shalwar','Classic shalwar to complete a kurta or kameez outfit.',1890,'PKR','https://images.unsplash.com/photo-1594633312681-425c7b97ccd1?auto=format&fit=crop&w=800&q=80','lowerwear','shalwar','white','traditional',array['pakistani','indian'],array['mild','hot','cold'],array['all']),
('p5','Beige Dupatta','Light dupatta for modest and cultural outfits.',1290,'PKR','https://images.unsplash.com/photo-1601924994987-69e26d50dc26?auto=format&fit=crop&w=800&q=80','accessories','dupatta','beige','modest',array['pakistani','indian','middleEastern'],array['mild','hot','cold'],array['all']),
('p6','White Sneakers','Everyday sneakers for casual and travel outfits.',4590,'PKR','https://images.unsplash.com/photo-1542291026-7eec264c27ff?auto=format&fit=crop&w=800&q=80','footwear','sneakers','white','casual',array['western','eastAsian','other'],array['mild','hot','cold'],array['spring','summer','autumn']),
('p7','Leather Boots','Closed boots for rain and cold weather.',6990,'PKR','https://images.unsplash.com/photo-1520639888713-7851133b1ed0?auto=format&fit=crop&w=800&q=80','footwear','boots','brown','casual',array['western','other'],array['veryCold','cold'],array['autumn','winter']),
('p8','Wool Coat','Warm coat for very cold days when the wardrobe has no outerwear.',11990,'PKR','https://images.unsplash.com/photo-1539533018447-63fcce2678e3?auto=format&fit=crop&w=800&q=80','upperwear','coat','grey','formal',array['western','other'],array['veryCold','cold'],array['winter']),
('p9','Blue Oxford Shirt','Office-ready shirt that also works for university.',2590,'PKR','https://images.unsplash.com/photo-1596755094514-f87e34085b2c?auto=format&fit=crop&w=800&q=80','upperwear','shirt','blue','smart',array['western','pakistani','other'],array['mild','cold'],array['all']),
('p10','Straight Blue Jeans','Classic jeans for casual western looks.',3490,'PKR','https://images.unsplash.com/photo-1541099649105-f69ad21f3246?auto=format&fit=crop&w=800&q=80','lowerwear','jeans','blue','casual',array['western','other'],array['cold','mild'],array['all']),
('p11','Modest Navy Dress','Long modest dress suitable for formal and religious events.',5490,'PKR','https://images.unsplash.com/photo-1595777457583-95e059d581b8?auto=format&fit=crop&w=800&q=80','dress','modest dress','navy','modest',array['pakistani','middleEastern','african'],array['mild','cold'],array['autumn','spring']),
('p12','Maroon Scarf','Warm scarf for cold and rainy days.',990,'PKR','https://images.unsplash.com/photo-1520903920243-00d872a2d1c9?auto=format&fit=crop&w=800&q=80','accessories','scarf','maroon','casual',array['all'],array['veryCold','cold'],array['winter','autumn']),
('p13','Olive Hoodie','Casual hoodie for cold university days.',2790,'PKR','https://images.unsplash.com/photo-1556821840-3a63f95609a7?auto=format&fit=crop&w=800&q=80','upperwear','hoodie','olive','streetwear',array['western','eastAsian','other'],array['cold','veryCold'],array['autumn','winter']),
('p14','Black Abaya','Modest outerwear for Middle Eastern and conservative preferences.',7990,'PKR','https://images.unsplash.com/photo-1585487000160-6ebcfceb0d03?auto=format&fit=crop&w=800&q=80','upperwear','abaya','black','modest',array['middleEastern','pakistani'],array['mild','cold','hot'],array['all']),
('p15','Khussa Shoes','Traditional footwear that pairs with kurta and shalwar.',2190,'PKR','https://images.unsplash.com/photo-1543163521-1bf539c55dd2?auto=format&fit=crop&w=800&q=80','footwear','khussa','gold','traditional',array['pakistani','indian'],array['mild','hot'],array['spring','summer']),
('p16','Waterproof Rain Jacket','Prioritize this when precipitation probability is high.',6490,'PKR','https://images.unsplash.com/photo-1507679799987-c73779587ccf?auto=format&fit=crop&w=800&q=80','upperwear','jacket','navy','casual',array['all'],array['cold','mild'],array['spring','autumn']),
('p17','Classic Leather Watch','Minimalist analog watch with brown leather strap.',3890,'PKR','https://images.unsplash.com/photo-1524805444758-089113d48a6d?auto=format&fit=crop&w=800&q=80','accessories','watch','brown','smart',array['all'],array['mild','hot','cold','veryCold'],array['all']),
('p18','Classic Sunglasses','UV-protective sunglasses suitable for sunny and warm days.',1990,'PKR','https://images.unsplash.com/photo-1511499767150-a48a237f0083?auto=format&fit=crop&w=800&q=80','accessories','sunglasses','black','casual',array['all'],array['hot','mild'],array['spring','summer']),
('p19','Black Leather Belt','Genuine leather dress belt with polished silver buckle.',1490,'PKR','https://images.unsplash.com/photo-1624222247344-550fb60583dc?auto=format&fit=crop&w=800&q=80','accessories','belt','black','formal',array['all'],array['cold','mild','hot','veryCold'],array['all']),
('p20','Canvas Tote Bag','Spacious everyday tote bag for books, shopping, and day trips.',1790,'PKR','https://images.unsplash.com/photo-1544816155-12df9643f363?auto=format&fit=crop&w=800&q=80','accessories','bag','cream','casual',array['all'],array['mild','hot','cold'],array['all'])
on conflict (id) do nothing;

insert into public.trends (
  id, title, subtitle, description, image_url, culture_tags, colors, item_types, season, styling_idea
) values
('t1','Ivory kurta + navy trousers','Pakistani seasonal staple','A light kurta with tailored trousers stays culturally aligned and weather-flexible for mild days.','https://images.unsplash.com/photo-1617137968427-85924c800a22?auto=format&fit=crop&w=800&q=80',array['pakistani','indian'],array['cream','navy','white'],array['kurta','trousers','dupatta'],'spring','Add a beige dupatta for university or family gatherings.'),
('t2','Layered neutrals','Western cold-weather trend','Grey coat, white tee, and dark denim is a high-frequency winter combination.','https://images.unsplash.com/photo-1487222477894-8943e31ef7b2?auto=format&fit=crop&w=800&q=80',array['western'],array['grey','white','black'],array['coat','t-shirt','jeans'],'winter','Keep accessories minimal; add a maroon scarf if it is windy.'),
('t3','Modest navy one-piece','Middle Eastern evening look','Long navy dresses remain a formal modest option that does not depend on shorts or mini silhouettes.','https://images.unsplash.com/photo-1515886657613-9f3515b0c78f?auto=format&fit=crop&w=800&q=80',array['middleEastern','pakistani'],array['navy','gold'],array['modest dress','abaya'],'all','Pair with closed shoes rather than sandals for formal events.'),
('t4','Earth-tone kaftan','African occasion dressing','Olive and gold kaftans work for celebrations while remaining modest.','https://images.unsplash.com/photo-1490481651871-ab68de25d43d?auto=format&fit=crop&w=800&q=80',array['african'],array['olive','gold','brown'],array['kaftan','dress'],'summer','Choose breathable fabric when temperatures are hot.'),
('t5','Clean shirt and chinos','East Asian smart casual','Crisp shirts with tapered trousers stay office-appropriate without loud prints.','https://images.unsplash.com/photo-1598033129183-c4f50c736f10?auto=format&fit=crop&w=800&q=80',array['eastAsian','western','other'],array['white','navy','beige'],array['shirt','trousers','loafers'],'all','Swap loafers for sneakers only on casual days.'),
('t6','Monochrome modest layers','Cross-culture conservative trend','Black and cream layers photograph well and respect modest preferences.','https://images.unsplash.com/photo-1496747611176-843222e1e57c?auto=format&fit=crop&w=800&q=80',array['all'],array['black','cream','beige'],array['modest top','trousers','scarf'],'autumn','Use a scarf or dupatta instead of a cropped silhouette.')
on conflict (id) do nothing;

-- Quick check (optional): after Run, open Table Editor and confirm
-- profiles.body_type and wardrobe_items.pattern_source exist.

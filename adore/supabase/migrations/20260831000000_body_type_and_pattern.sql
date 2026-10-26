-- Additive profile and wardrobe fields. Existing rows stay valid.

alter table public.profiles
  add column if not exists body_type text;

alter table public.wardrobe_items
  add column if not exists pattern_source text default 'user';

alter table public.wardrobe_items
  add column if not exists pattern_confidence double precision;

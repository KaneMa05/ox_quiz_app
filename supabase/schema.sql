-- OX 퀴즈 (과목 → 단원 → 지문 단위 → 선지 행)
-- Supabase Dashboard → SQL Editor 에서 실행하세요.

create table if not exists public.quiz_subjects (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  sort_order int not null default 0,
  is_active boolean not null default true,
  created_at timestamptz not null default now()
);

create table if not exists public.quiz_units (
  id uuid primary key default gen_random_uuid(),
  subject_id uuid not null references public.quiz_subjects (id) on delete cascade,
  -- null: 대단원 또는 단일 단원. 값 있으면 소단원(부모=대단원 id)
  parent_unit_id uuid references public.quiz_units (id) on delete cascade,
  name text not null,
  sort_order int not null default 0,
  is_active boolean not null default true,
  created_at timestamptz not null default now()
);

-- 한 지문(기출 번호·4지선다 묶음 등). 선지는 quiz_questions 행으로 유지(item_id로 연결).
create table if not exists public.quiz_items (
  id uuid primary key default gen_random_uuid(),
  unit_id uuid not null references public.quiz_units (id) on delete cascade,
  stem text not null,
  sort_order int not null default 0,
  pack_no int,
  item_type text not null default 'ox_per_choice',
  is_active boolean not null default true,
  created_at timestamptz not null default now()
);

create table if not exists public.quiz_questions (
  id uuid primary key default gen_random_uuid(),
  unit_id uuid not null references public.quiz_units (id) on delete cascade,
  item_id uuid references public.quiz_items (id) on delete cascade,
  question text not null,
  choice_text text not null,
  answer boolean not null,
  explanation text,
  sort_order int not null default 0,
  pack_no int,
  is_active boolean not null default true,
  created_at timestamptz not null default now()
);

create index if not exists idx_quiz_units_subject on public.quiz_units (subject_id);
create index if not exists idx_quiz_units_parent on public.quiz_units (parent_unit_id);
create index if not exists idx_quiz_items_unit on public.quiz_items (unit_id);
create index if not exists idx_quiz_items_pack on public.quiz_items (pack_no) where pack_no is not null;
create index if not exists idx_quiz_questions_unit on public.quiz_questions (unit_id);
create index if not exists idx_quiz_questions_item on public.quiz_questions (item_id) where item_id is not null;

-- 기존 DB(과거 스키마 호환): 컬럼 추가
alter table public.quiz_questions add column if not exists question text;
alter table public.quiz_questions add column if not exists choice_text text;
alter table public.quiz_questions add column if not exists item_id uuid references public.quiz_items (id) on delete cascade;

alter table public.quiz_units add column if not exists parent_unit_id uuid references public.quiz_units (id) on delete cascade;

-- 앱 설정(anon 읽기 전용). 예: 출제에서 제외할 pack_no 목록 JSON 배열
create table if not exists public.quiz_settings (
  key text primary key,
  value jsonb not null,
  updated_at timestamptz not null default now()
);

alter table public.quiz_settings enable row level security;

drop policy if exists "quiz_settings_select_public" on public.quiz_settings;
create policy "quiz_settings_select_public" on public.quiz_settings
  for select using (true);

alter table public.quiz_subjects enable row level security;
alter table public.quiz_units enable row level security;
alter table public.quiz_items enable row level security;
alter table public.quiz_questions enable row level security;

drop policy if exists "quiz_subjects_select_public" on public.quiz_subjects;
create policy "quiz_subjects_select_public" on public.quiz_subjects
  for select using (is_active = true);

drop policy if exists "quiz_units_select_public" on public.quiz_units;
create policy "quiz_units_select_public" on public.quiz_units
  for select using (is_active = true);

drop policy if exists "quiz_items_select_public" on public.quiz_items;
create policy "quiz_items_select_public" on public.quiz_items
  for select using (is_active = true);

drop policy if exists "quiz_questions_select_public" on public.quiz_questions;
create policy "quiz_questions_select_public" on public.quiz_questions
  for select using (is_active = true);

-- 실제 문제 데이터: SQL Editor에서 seed_*.sql 실행
-- (기존 DB에 pack_no만 없으면: alter table public.quiz_questions add column if not exists pack_no int;)
-- 지문 단위 테이블만 추가하는 경우: add_quiz_items.sql

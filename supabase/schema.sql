-- OX 퀴즈 (과목 → 단원 → 문제)
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
  name text not null,
  sort_order int not null default 0,
  is_active boolean not null default true,
  created_at timestamptz not null default now()
);

create table if not exists public.quiz_questions (
  id uuid primary key default gen_random_uuid(),
  unit_id uuid not null references public.quiz_units (id) on delete cascade,
  question text not null,
  choice_text text not null,
  answer boolean not null,
  explanation text,
  sort_order int not null default 0,
  pack_no int,
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  body text
);

create index if not exists idx_quiz_units_subject on public.quiz_units (subject_id);
create index if not exists idx_quiz_questions_unit on public.quiz_questions (unit_id);

-- 기존 DB(예전 body만 있던 테이블): 컬럼 추가
alter table public.quiz_questions add column if not exists question text;
alter table public.quiz_questions add column if not exists choice_text text;

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
alter table public.quiz_questions enable row level security;

drop policy if exists "quiz_subjects_select_public" on public.quiz_subjects;
create policy "quiz_subjects_select_public" on public.quiz_subjects
  for select using (is_active = true);

drop policy if exists "quiz_units_select_public" on public.quiz_units;
create policy "quiz_units_select_public" on public.quiz_units
  for select using (is_active = true);

drop policy if exists "quiz_questions_select_public" on public.quiz_questions;
create policy "quiz_questions_select_public" on public.quiz_questions
  for select using (is_active = true);

-- 실제 문제 데이터: SQL Editor에서 seed_water_leisure.sql 실행
-- (기존 DB에 pack_no만 없으면: alter table public.quiz_questions add column if not exists pack_no int;)

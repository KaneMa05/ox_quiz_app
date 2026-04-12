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
create index if not exists idx_quiz_items_unit on public.quiz_items (unit_id);
create index if not exists idx_quiz_items_pack on public.quiz_items (pack_no) where pack_no is not null;
create index if not exists idx_quiz_questions_unit on public.quiz_questions (unit_id);
-- parent_unit_id / item_id 는 아래 ALTER 로 예전 테이블에 붙을 수 있으므로 인덱스는 컬럼 추가 뒤에 둡니다.

-- 기존 DB(과거 스키마 호환): 컬럼 추가
alter table public.quiz_subjects add column if not exists is_active boolean not null default true;
alter table public.quiz_subjects add column if not exists created_at timestamptz not null default now();

alter table public.quiz_units add column if not exists parent_unit_id uuid references public.quiz_units (id) on delete cascade;
alter table public.quiz_units add column if not exists is_active boolean not null default true;
alter table public.quiz_units add column if not exists created_at timestamptz not null default now();

alter table public.quiz_questions add column if not exists question text;
alter table public.quiz_questions add column if not exists choice_text text;
alter table public.quiz_questions add column if not exists pack_no int;
alter table public.quiz_questions add column if not exists is_active boolean not null default true;
alter table public.quiz_questions add column if not exists created_at timestamptz not null default now();
-- FK 없이 item_id 만 있던 경우: 아래 DO 블록에서 quiz_items(id) 로 제약 추가
alter table public.quiz_questions add column if not exists item_id uuid;

alter table public.quiz_items add column if not exists item_type text not null default 'ox_per_choice';
alter table public.quiz_items add column if not exists is_active boolean not null default true;
alter table public.quiz_items add column if not exists created_at timestamptz not null default now();

-- item_id → quiz_items FK (컬럼만 있고 REFERENCES 없으면 PostgREST 임베드 불가).
-- item_id 에 quiz_items 에 없는 id 가 있으면 아래 ALTER 가 실패합니다 → 해당 행을 수정하거나 item_id 를 null 로 두세요.
do $$
begin
  if exists (
    select 1 from information_schema.columns
    where table_schema = 'public' and table_name = 'quiz_questions' and column_name = 'item_id'
  ) and exists (
    select 1 from information_schema.tables
    where table_schema = 'public' and table_name = 'quiz_items'
  ) then
    if not exists (
      select 1
      from pg_constraint c
      join pg_class rel on rel.oid = c.conrelid
        and rel.relnamespace = (select oid from pg_namespace where nspname = 'public')
      where rel.relname = 'quiz_questions'
        and c.contype = 'f'
        and c.confrelid = 'public.quiz_items'::regclass
    ) then
      alter table public.quiz_questions
        add constraint quiz_questions_item_id_fkey
        foreign key (item_id) references public.quiz_items (id) on delete cascade;
    end if;
  end if;
end $$;

create index if not exists idx_quiz_units_parent on public.quiz_units (parent_unit_id);
create index if not exists idx_quiz_questions_item on public.quiz_questions (item_id) where item_id is not null;

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

-- 실제 문제 데이터는 Table Editor 또는 별도 INSERT 로 채웁니다.
-- 기존 프로젝트: 이 파일 전체를 SQL Editor에서 한 번 더 실행해도 됩니다(컬럼·정책은 IF NOT EXISTS / DROP IF EXISTS 로 정합).

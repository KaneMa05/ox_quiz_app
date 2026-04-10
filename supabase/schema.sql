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
  body text not null,
  answer boolean not null,
  explanation text,
  sort_order int not null default 0,
  is_active boolean not null default true,
  created_at timestamptz not null default now()
);

create index if not exists idx_quiz_units_subject on public.quiz_units (subject_id);
create index if not exists idx_quiz_questions_unit on public.quiz_questions (unit_id);

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

-- 예시 데이터 (이미 과목이 있으면 건너뜀)
do $$
declare
  s_const uuid;
  s_admin uuid;
  u1 uuid;
  u2 uuid;
  ua uuid;
begin
  if exists (select 1 from public.quiz_subjects limit 1) then
    return;
  end if;

  insert into public.quiz_subjects (name, sort_order) values ('헌법', 0) returning id into s_const;
  insert into public.quiz_subjects (name, sort_order) values ('행정법', 1) returning id into s_admin;

  insert into public.quiz_units (subject_id, name, sort_order) values (s_const, '총강', 0) returning id into u1;
  insert into public.quiz_units (subject_id, name, sort_order) values (s_const, '국회', 1) returning id into u2;
  insert into public.quiz_units (subject_id, name, sort_order) values (s_admin, '행정법 개론', 0) returning id into ua;

  insert into public.quiz_questions (unit_id, body, answer, explanation, sort_order) values
    (u1, '대한민국은 민주공화국이다.', true, '헌법 제1조 제1항.', 0),
    (u1, '대한민국의 수도는 부산이다.', false, '수도는 서울입니다.', 1),
    (u2, '국회는 단원제이다.', true, '단원제 국회입니다.', 0),
    (ua, '행정법은 공법에 해당한다.', true, '대표적인 공법입니다.', 0);
end $$;

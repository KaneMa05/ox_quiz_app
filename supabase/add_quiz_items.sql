-- 지문 단위(quiz_items) + 선지 행(quiz_questions.item_id) — 기존 DB에 한 번만 실행
-- 신규 프로젝트는 schema.sql 전체 실행으로 동일 구조를 만들 수 있습니다.

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

create index if not exists idx_quiz_items_unit on public.quiz_items (unit_id);
create index if not exists idx_quiz_items_pack on public.quiz_items (pack_no) where pack_no is not null;

alter table public.quiz_questions add column if not exists item_id uuid references public.quiz_items (id) on delete cascade;

create index if not exists idx_quiz_questions_item on public.quiz_questions (item_id) where item_id is not null;

alter table public.quiz_items enable row level security;

drop policy if exists "quiz_items_select_public" on public.quiz_items;
create policy "quiz_items_select_public" on public.quiz_items
  for select using (is_active = true);

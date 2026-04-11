-- 기존 DB: 대단원·소단원 계층용 컬럼 (한 번만 실행)
alter table public.quiz_units add column if not exists parent_unit_id uuid references public.quiz_units (id) on delete cascade;
create index if not exists idx_quiz_units_parent on public.quiz_units (parent_unit_id);

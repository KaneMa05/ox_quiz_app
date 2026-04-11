-- 이미 schema.sql 예전 버전만 실행한 DB용: 설정 테이블만 추가
create table if not exists public.quiz_settings (
  key text primary key,
  value jsonb not null,
  updated_at timestamptz not null default now()
);
alter table public.quiz_settings enable row level security;
drop policy if exists "quiz_settings_select_public" on public.quiz_settings;
create policy "quiz_settings_select_public" on public.quiz_settings for select using (true);

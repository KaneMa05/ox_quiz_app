-- 중복 저장 제거: 통합 문자열은 question + choice_text 로 앱에서 조합합니다.
alter table public.quiz_questions drop column if exists body;

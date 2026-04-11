# OX 퀴즈 — Supabase + Vercel 배포

제가 **귀하의 Vercel·Supabase 계정에 로그인하거나 클릭 배포를 대신할 수는 없습니다.** 아래 순서대로 진행하면 같은 결과를 낼 수 있습니다.

## 1. Supabase (DB)

1. [Supabase](https://supabase.com)에서 새 프로젝트 생성.
2. **SQL Editor**에서 `supabase/schema.sql` 전체를 실행한 뒤, 같은 곳에서 `supabase/seed_water_leisure.sql` 전체를 실행합니다. (문제 본문은 `data.js`와 동일하고, 맨 아래 `quiz_settings`에 출제 제외 `pack_no` 목록이 들어갑니다.)
3. 예전에 `schema.sql`만 돌린 DB라면 `supabase/add_quiz_settings.sql`을 한 번 실행한 뒤, `seed_water_leisure.sql` 맨 아래 `insert ... quiz_settings` 한 줄만 실행해도 됩니다.
4. **Settings → API**에서 `Project URL`, `anon public` 키를 복사해 둡니다.

## 2. Vercel (배포)

1. [Vercel](https://vercel.com) 로그인 → **Add New → Project**.
2. GitHub 등에 이 저장소를 연결한 뒤, **Root Directory**를 `ox-quiz-app` 으로 지정합니다.  
   (또는 `ox-quiz-app` 폴더만 별도 저장소로 올려도 됩니다.)
3. **Environment Variables**에 다음 중 하나 방식으로 추가합니다.
   - `SUPABASE_PROJECT_ID` + `SUPABASE_ANON_KEY`  
   - 또는 `SUPABASE_URL` + `SUPABASE_ANON_KEY`  
   (`env.example.txt` 참고)
4. Deploy.

## 3. 동작 방식

- 브라우저가 `/api/env?format=json`으로 키를 읽고, Supabase에서 `quiz_subjects`, `quiz_units`, `quiz_questions`, `quiz_settings`(출제 제외 번호)를 조회합니다.
- Vercel에 키가 없거나 조회에 실패하면 `data.js`의 로컬 데이터를 씁니다.

## 4. 로컬에서 API까지 테스트

`ox-quiz-app` 폴더에서 Vercel CLI:

```bash
cd ox-quiz-app
npx vercel dev
```

환경 변수는 Vercel 프로젝트에 넣거나, 로컬 `.env`를 `vercel dev`가 읽도록 설정합니다.

# OX 퀴즈 — Supabase + Vercel 배포

## 1. Supabase (DB)

1. [Supabase](https://supabase.com)에서 프로젝트를 만듭니다.
2. **SQL Editor**에서 이 저장소의 `supabase/schema.sql` 전체를 한 번 실행합니다(테이블·RLS·`quiz_questions`↔`quiz_items` FK). 이미 예전 스키마가 있으면 **같은 파일을 다시 실행**해 컬럼·FK를 맞추면 됩니다.
3. 과목·단원·문항 데이터는 **Table Editor**에서 직접 넣거나, SQL Editor에서 직접 `INSERT`를 작성해 실행합니다.  
   앱은 키가 없을 때 `data.js` 로컬 데이터를 쓰므로, DB는 비워 둔 채로도 동작 확인은 가능합니다.
4. **Settings → API**에서 `Project URL`, `anon public` 키를 복사해 둡니다.

## 2. Vercel (배포)

1. [Vercel](https://vercel.com)에서 프로젝트를 만들고 GitHub 저장소를 연결합니다. **Root Directory**는 `ox-quiz-app` 입니다.
2. **Environment Variables** (`env.example.txt` 참고):
   - `SUPABASE_PROJECT_ID` + `SUPABASE_ANON_KEY` 또는 `SUPABASE_URL` + `SUPABASE_ANON_KEY`
   - 관리자(`/admin`)·`/api/admin/questions`용: `SUPABASE_SERVICE_ROLE_KEY`, `OX_ADMIN_SECRET`
3. Deploy. 환경 변수를 바꾼 뒤에는 **재배포**해야 서버 함수에 반영됩니다.

### 배포가 반영되지 않을 때

- **Root Directory**가 `ox-quiz-app` 인지 확인합니다.
- **Production** 배포·도메인을 보고 있는지, **Deployments**에서 최신 커밋이 Ready 인지 확인합니다.
- OX 전용 저장소: [KaneMa05/ox_quiz_app](https://github.com/KaneMa05/ox_quiz_app). 상위 monorepo만 쓰는 경우 `git subtree push --prefix=ox-quiz-app ox main` 등으로 동기화합니다.
- `POST /api/admin/questions` 가 **503**이면: `OX_ADMIN_SECRET`, `SUPABASE_SERVICE_ROLE_KEY`, 그리고 `SUPABASE_URL` 또는 `SUPABASE_PROJECT_ID`(또는 `NEXT_PUBLIC_*` 동명)가 Production에 있는지 확인한 뒤 재배포합니다.

## 3. 동작 방식

- 브라우저는 `/api/env?format=json`으로 anon 키·URL을 읽고, Supabase에서 커리큘럼을 불러옵니다.
- 실패 시 `data.js` 로컬 데이터를 사용합니다.

## 4. 로컬에서 API 테스트

```bash
cd ox-quiz-app
npx vercel dev
```

환경 변수는 Vercel 프로젝트에 두거나, 같은 폴더의 `.env.local`을 `vercel dev`가 읽도록 둡니다.

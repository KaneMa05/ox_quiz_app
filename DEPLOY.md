# OX 퀴즈 — Supabase + Vercel 배포

제가 **귀하의 Vercel·Supabase 계정에 로그인하거나 클릭 배포를 대신할 수는 없습니다.** 아래 순서대로 진행하면 같은 결과를 낼 수 있습니다.

## 1. Supabase (DB)

1. [Supabase](https://supabase.com)에서 새 프로젝트 생성.
2. **SQL Editor**에서 `supabase/schema.sql` 전체를 실행한 뒤, 같은 곳에서 `supabase/seed_water_leisure.sql` 전체를 실행합니다. (문제 본문은 `data.js`와 동일하고, 맨 아래 `quiz_settings`에 출제 제외 `pack_no` 목록이 들어갑니다.)  
   예전 DB에는 `supabase/add_parent_unit_id.sql`을 한 번 실행해 `quiz_units.parent_unit_id`(대단원·소단원) 컬럼이 있는지 확인하세요. `null`이면 대단원(또는 단일 단원), 값이 있으면 그 id를 부모로 하는 소단원입니다. 문제(`quiz_questions`)는 **소단원(말단 단원)** id에만 연결합니다.
3. 예전에 `schema.sql`만 돌린 DB라면 `supabase/add_quiz_settings.sql`을 한 번 실행한 뒤, `seed_water_leisure.sql` 맨 아래 `insert ... quiz_settings` 한 줄만 실행해도 됩니다.
4. **Settings → API**에서 `Project URL`, `anon public` 키를 복사해 둡니다.

### Supabase에 접속해서 데이터를 넣는 방법

1. **로그인·프로젝트**  
   [supabase.com](https://supabase.com)에 로그인 → 상단에서 **본인의 OX 퀴즈 프로젝트**를 선택합니다.

2. **SQL로 한 번에 넣기 (권장)**  
   왼쪽 메뉴 **SQL Editor** → **New query** → 이 저장소의 `supabase/schema.sql`(최초 1회), `add_parent_unit_id.sql`·`add_quiz_settings.sql` 등 필요한 것만 순서대로 실행한 뒤, `seed_water_leisure.sql`처럼 준비된 시드 전체를 붙여넣고 **Run** 합니다.  
   개별 문항만 넣을 때는 `INSERT INTO public.quiz_subjects ...` 형태의 SQL을 작성해 같은 SQL Editor에서 실행하면 됩니다. (문자열 안의 작은따옴표 `'`는 SQL에서 `''`로 이스케이프합니다.)

3. **화면에서 한 줄씩 넣기**  
   **Table Editor** → `quiz_subjects`, `quiz_units`, `quiz_questions` 등 테이블을 고른 뒤 **Insert** / 행 추가로 값을 입력합니다. `id`는 비워 두면 UUID가 자동 생성되는 경우가 많습니다.  
   **대단원·소단원**: `quiz_units`에서 소단원 행의 `parent_unit_id`에 대단원 행의 `id`를 넣습니다. `quiz_questions.unit_id`는 **소단원(말단)** id만 가리킵니다.

4. **외부 클라이언트로 접속**  
   **Project Settings → Database**에서 **Connection string**(URI)을 복사해, PC에 설치한 [DBeaver](https://dbeaver.io/), [TablePlus](https://tableplus.com/), `psql` 등으로 접속해 동일하게 `INSERT`·`SELECT`를 실행할 수도 있습니다.

5. **주의**  
   `seed_water_leisure.sql` 맨 위의 `truncate ... cascade`는 **기존 과목·단원·문제를 비웁니다.** 이미 넣은 데이터를 지우고 싶지 않다면 시드 전체 대신 **필요한 `INSERT`만** 따로 실행하세요.

### data.js를 Supabase에 자동 반영 (`npm run db:sync`)

1. **Supabase Dashboard → Settings → API**에서 **Project URL**과 **service_role** 시크릿 키를 복사합니다. (`anon` 키가 아닙니다.)
2. `ox-quiz-app` 루트에 `.env.local`(또는 `.env`)을 만들고 다음을 넣습니다.  
   `SUPABASE_URL=...`  
   `SUPABASE_SERVICE_ROLE_KEY=...`  
   **service_role 키는 RLS를 우회합니다. Git에 커밋하거나 Vercel 환경 변수(브라우저에 노출되는 값)에 넣지 마세요.**
3. 터미널에서:
   ```bash
   cd ox-quiz-app
   npm install
   npm run db:sync
   ```
4. 스크립트는 **동기화 대상 과목**과 **같은 이름**의 `quiz_subjects` 행을 삭제한 뒤(연쇄로 단원·문항 삭제), `data.js` 내용으로 다시 채웁니다. `quiz_settings`의 `excluded_pack_nos`도 `data.js`와 맞춥니다.
5. **일부 과목만** 넣거나 갱신하려면 같은 파일에  
   `OX_DB_SYNC_SUBJECTS=해양경찰학개론`  
   처럼 **과목 표시명**을 쉼표로 구분해 넣습니다. 비우거나 `all`이면 `data.js`에 있는 **모든** 과목을 대상으로 합니다(해사법규 분량이 많으면 시간이 걸릴 수 있습니다).

### Cursor Supabase MCP (`execute_sql`)

Cursor에 **Supabase MCP**가 연결되어 있으면, 채팅 중 에이전트가 **`execute_sql`**로 Postgres에 SQL을 실행할 수 있습니다(대시보드 SQL Editor와 유사). 스키마 변경은 MCP의 **`apply_migration`** 사용이 권장됩니다.

- MCP는 **MCP 설정에 연결된 프로젝트**에만 적용됩니다.
- `DELETE`·`INSERT` 등은 Cursor에서 도구 승인 시 실행되므로, **대량·전체 동기화**는 여전히 **`npm run db:sync`**가 안정적입니다. MCP는 소량 수정·점검용 `SELECT`·짧은 DML에 적합합니다.

## 2. Vercel (배포)

1. [Vercel](https://vercel.com) 로그인 → **Add New → Project**.
2. GitHub 등에 이 저장소를 연결한 뒤, **Root Directory**를 `ox-quiz-app` 으로 지정합니다.  
   (또는 `ox-quiz-app` 폴더만 별도 저장소로 올려도 됩니다.)
3. **Environment Variables**에 다음 중 하나 방식으로 추가합니다.
   - `SUPABASE_PROJECT_ID` + `SUPABASE_ANON_KEY`  
   - 또는 `SUPABASE_URL` + `SUPABASE_ANON_KEY`  
   (`env.example.txt` 참고)
4. **문제 입력 페이지(`/admin`)**를 쓰려면 같은 프로젝트에 다음도 넣습니다. (`service_role`은 서버 함수에서만 쓰이며 브라우저에 내려가지 않습니다.)
   - `SUPABASE_SERVICE_ROLE_KEY` — Supabase **Settings → API**의 service_role (절대 공개 저장소에 커밋하지 마세요.)
   - `OX_ADMIN_SECRET` — 임의로 긴 문자열. 관리 페이지에서 입력한 값과 일치할 때만 `/api/admin/questions`가 삽입·삭제를 수행합니다.
5. Deploy.

### 배포가 반영되지 않을 때 (체크리스트)

1. **Root Directory**  
   Vercel 프로젝트 → **Settings → General → Root Directory**가 반드시 **`ox-quiz-app`** 인지 확인하세요.  
   비어 있거나 저장소 루트(`Demo/`)이면 **일기 앱 등 다른 폴더가 배포**되고, OX 퀴즈 변경은 이 URL에 나타나지 않습니다. OX 전용으로는 **같은 Git 저장소라도 Vercel 프로젝트를 하나 더 만들고** Root만 `ox-quiz-app`으로 두는 방식이 안전합니다.

2. **올바른 URL·배포**  
   대시보드 **Deployments**에서 최신 커밋 메시지·SHA가 방금 푸시한 것과 같은지 확인하세요. **Preview** URL이 아니라 **Production** 도메인을 보고 있는지도 확인합니다.

3. **빌드 실패**  
   해당 배포가 **Ready**(초록)인지, **Error**면 로그를 열어 실패 원인을 먼저 해결합니다.

4. **브라우저 캐시**  
   강력 새로고침(Windows: `Ctrl+Shift+R`) 또는 시크릿 창에서 열어 봅니다. 이 저장소의 `vercel.json`은 문서·API 응답에 캐시를 거의 쓰지 않도록 설정합니다.

5. **Git 푸시 대상**  
   Vercel이 연결한 **브랜치**(보통 `main`)에 푸시했는지, 다른 브랜치·다른 원격만 갱신하지 않았는지 확인합니다.

6. **올바른 GitHub 저장소**  
   OX 전용 저장소는 **[KaneMa05/ox_quiz_app](https://github.com/KaneMa05/ox_quiz_app)** 입니다. 상위 monorepo(다른 `origin`)의 `ox-quiz-app` 폴더만 작업했다면, 여기로 반영되지 않을 수 있습니다. monorepo에서 동기화하려면 `git remote add ox https://github.com/KaneMa05/ox_quiz_app.git` 후 `git subtree push --prefix=ox-quiz-app ox main` 등을 사용합니다(히스토리가 다르면 `--force`가 필요할 수 있음).

7. **`POST /api/admin/questions` 가 503일 때**  
   서버는 다음이 없으면 503과 JSON `error` 메시지를 돌려줍니다.
   - `OX_ADMIN_SECRET` 미설정 → `"OX_ADMIN_SECRET is not set on the server"`
   - Supabase URL/ref 미설정 → `SUPABASE_URL` 또는 `SUPABASE_PROJECT_ID` (또는 이미 쓰는 **`NEXT_PUBLIC_SUPABASE_URL` / `NEXT_PUBLIC_SUPABASE_PROJECT_ID`** 도 `/api/env`와 같이 관리 API에서 읽습니다.)
   - **`SUPABASE_SERVICE_ROLE_KEY`** 미설정 — 이름은 이것만 인식합니다. anon 키와는 별개이며, Supabase **Settings → API**의 **service_role** 값을 넣어야 합니다.  
   Vercel **Production**에 넣은 뒤 **재배포**해야 서버리스에 반영됩니다.

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

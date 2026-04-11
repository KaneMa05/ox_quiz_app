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

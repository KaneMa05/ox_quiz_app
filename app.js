const ui = {
  pickCard: document.getElementById("pickCard"),
  quizCard: document.getElementById("quizCard"),
  resultCard: document.getElementById("resultCard"),
  subjectSelect: document.getElementById("subjectSelect"),
  unitSelect: document.getElementById("unitSelect"),
  startBtn: document.getElementById("startBtn"),
  progress: document.getElementById("progress"),
  score: document.getElementById("score"),
  question: document.getElementById("question"),
  hint: document.getElementById("hint"),
  btnO: document.getElementById("btnO"),
  btnX: document.getElementById("btnX"),
  finalScore: document.getElementById("finalScore"),
  retryBtn: document.getElementById("retryBtn"),
};

let curriculum = [];
let activeQuestions = [];
let idx = 0;
let score = 0;

async function loadEnvJson() {
  try {
    const res = await fetch("/api/env?format=json", { cache: "no-store" });
    if (!res.ok) return {};
    return (await res.json()) || {};
  } catch {
    return {};
  }
}

function supabaseUrlFromEnv(env) {
  const u = (env.SUPABASE_URL || "").trim();
  if (u) return u;
  const pid = (env.SUPABASE_PROJECT_ID || "").trim();
  if (pid) return `https://${pid}.supabase.co`;
  return "";
}

function buildCurriculumFromRows(subjects, units, questions) {
  const subs = (subjects || []).slice().sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0));
  const uns = (units || []).slice().sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0));
  const qs = (questions || []).slice().sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0));

  return subs.map((s) => ({
    id: s.id,
    name: s.name,
    units: uns
      .filter((u) => u.subject_id === s.id)
      .map((u) => ({
        id: u.id,
        name: u.name,
        questions: qs
          .filter((q) => q.unit_id === u.id)
          .map((q) => ({
            body: q.body,
            answer: q.answer,
            explanation: q.explanation || "",
          })),
      })),
  }));
}

async function loadCurriculumFromSupabase(env) {
  const url = supabaseUrlFromEnv(env);
  const key = (env.SUPABASE_ANON_KEY || "").trim();
  if (!url || !key || !window.supabase?.createClient) return null;

  const client = window.supabase.createClient(url, key, {
    global: { headers: { apikey: key, Authorization: `Bearer ${key}` } },
  });

  const [subRes, unitRes, qRes] = await Promise.all([
    client.from("quiz_subjects").select("id,name,sort_order").order("sort_order"),
    client.from("quiz_units").select("id,subject_id,name,sort_order").order("sort_order"),
    client.from("quiz_questions").select("id,unit_id,body,answer,explanation,sort_order").order("sort_order"),
  ]);

  if (subRes.error) throw subRes.error;
  if (unitRes.error) throw unitRes.error;
  if (qRes.error) throw qRes.error;

  return buildCurriculumFromRows(subRes.data, unitRes.data, qRes.data);
}

function fillSubjects() {
  ui.subjectSelect.innerHTML = "";
  for (const s of curriculum) {
    const opt = document.createElement("option");
    opt.value = s.id;
    opt.textContent = s.name;
    ui.subjectSelect.appendChild(opt);
  }
}

function fillUnits() {
  const sid = ui.subjectSelect.value;
  const sub = curriculum.find((s) => s.id === sid);
  ui.unitSelect.innerHTML = "";
  if (!sub) return;
  for (const u of sub.units) {
    const opt = document.createElement("option");
    opt.value = u.id;
    opt.textContent = u.name;
    ui.unitSelect.appendChild(opt);
  }
}

function showPick() {
  ui.pickCard.classList.remove("hidden");
  ui.quizCard.classList.add("hidden");
  ui.resultCard.classList.add("hidden");
  ui.btnO.disabled = false;
  ui.btnX.disabled = false;
}

function showQuiz() {
  ui.pickCard.classList.add("hidden");
  ui.quizCard.classList.remove("hidden");
  ui.resultCard.classList.add("hidden");
}

function renderQuestion() {
  const q = activeQuestions[idx];
  ui.progress.textContent = `${idx + 1} / ${activeQuestions.length}`;
  ui.score.textContent = `점수 ${score}`;
  ui.question.textContent = q.body;
  ui.hint.textContent = "";
}

function finish() {
  ui.quizCard.classList.add("hidden");
  ui.resultCard.classList.remove("hidden");
  ui.finalScore.textContent = `${activeQuestions.length}문제 중 ${score}개 맞음`;
}

function answer(userAnswer) {
  const q = activeQuestions[idx];
  const ok = userAnswer === q.answer;
  if (ok) score += 1;
  ui.hint.textContent = ok ? `정답. ${q.explanation}` : `오답. ${q.explanation}`;

  setTimeout(() => {
    idx += 1;
    if (idx >= activeQuestions.length) {
      finish();
      return;
    }
    renderQuestion();
  }, 500);
}

function start() {
  const sid = ui.subjectSelect.value;
  const uid = ui.unitSelect.value;
  const sub = curriculum.find((s) => s.id === sid);
  const unit = sub?.units.find((u) => u.id === uid);
  const list = unit?.questions || [];
  if (!list.length) {
    window.alert("이 단원에 문제가 없습니다.");
    return;
  }
  activeQuestions = list;
  idx = 0;
  score = 0;
  showQuiz();
  renderQuestion();
}

function retry() {
  idx = 0;
  score = 0;
  ui.resultCard.classList.add("hidden");
  if (activeQuestions.length) {
    showQuiz();
    renderQuestion();
  } else {
    showPick();
  }
}

function bind() {
  ui.subjectSelect.addEventListener("change", fillUnits);
  ui.startBtn.addEventListener("click", start);
  ui.btnO.addEventListener("click", () => answer(true));
  ui.btnX.addEventListener("click", () => answer(false));
  ui.retryBtn.addEventListener("click", retry);
}

async function boot() {
  bind();

  const fallback = window.OX_CURRICULUM || [];
  curriculum = fallback;
  fillSubjects();
  fillUnits();

  const env = await loadEnvJson();
  const hasKeys = Boolean(
    (env.SUPABASE_ANON_KEY || "").trim() && (supabaseUrlFromEnv(env) || "").trim()
  );

  if (!hasKeys) return;

  try {
    const fromDb = await loadCurriculumFromSupabase(env);
    if (fromDb && fromDb.length) {
      curriculum = fromDb;
      fillSubjects();
      fillUnits();
    }
  } catch (e) {
    console.warn("Supabase 로드 실패, 로컬 data.js 사용:", e);
  }
}

boot();

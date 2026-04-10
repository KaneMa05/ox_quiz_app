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
  choiceText: document.getElementById("choiceText"),
  hint: document.getElementById("hint"),
  btnO: document.getElementById("btnO"),
  btnX: document.getElementById("btnX"),
  confirmBtn: document.getElementById("confirmBtn"),
  finalScore: document.getElementById("finalScore"),
  retryBtn: document.getElementById("retryBtn"),
};

let curriculum = [];
let activeQuestions = [];
let idx = 0;
let score = 0;
let answeredCurrent = false;
const USE_LOCAL_ONLY = true;
const MASTERED_KEY = "ox-mastered-v1";

function readMasteredMap() {
  try {
    const raw = localStorage.getItem(MASTERED_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw);
    return parsed && typeof parsed === "object" ? parsed : {};
  } catch {
    return {};
  }
}

function writeMasteredMap(next) {
  try {
    localStorage.setItem(MASTERED_KEY, JSON.stringify(next));
  } catch {
    // ignore storage failures
  }
}

function isMastered(unitId, question) {
  const map = readMasteredMap();
  const unitMap = map[unitId];
  if (!unitMap || typeof unitMap !== "object") return false;
  return !!unitMap[question.body];
}

function markMastered(unitId, question) {
  const map = readMasteredMap();
  if (!map[unitId] || typeof map[unitId] !== "object") map[unitId] = {};
  map[unitId][question.body] = true;
  writeMasteredMap(map);
}

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
  const body = (q.body || "").toString();
  const marker = "\n\n선지:";
  if (body.includes(marker)) {
    const [stem, choice] = body.split(marker);
    ui.question.textContent = stem.replace(/^문제:\s*/, "").trim();
    if (ui.choiceText) ui.choiceText.textContent = choice.trim();
  } else if (body.includes("선지:")) {
    const parts = body.split("선지:");
    ui.question.textContent = parts[0].replace(/^문제:\s*/, "").trim();
    if (ui.choiceText) ui.choiceText.textContent = (parts[1] || "").trim();
  } else {
    ui.question.textContent = body;
    if (ui.choiceText) ui.choiceText.textContent = "";
  }
  ui.hint.textContent = "";
  answeredCurrent = false;
  ui.btnO.disabled = false;
  ui.btnX.disabled = false;
  if (ui.confirmBtn) ui.confirmBtn.disabled = true;
}

function finish() {
  ui.quizCard.classList.add("hidden");
  ui.resultCard.classList.remove("hidden");
  ui.finalScore.textContent = `${activeQuestions.length}문제 중 ${score}개 맞음`;
}

function answer(userAnswer) {
  if (answeredCurrent) return;
  const q = activeQuestions[idx];
  const ok = userAnswer === q.answer;
  if (ok) {
    score += 1;
    const uid = ui.unitSelect.value;
    if (uid) markMastered(uid, q);
  }
  ui.hint.textContent = ok ? `정답. ${q.explanation}` : `오답. ${q.explanation}`;
  answeredCurrent = true;
  ui.btnO.disabled = true;
  ui.btnX.disabled = true;
  if (ui.confirmBtn) ui.confirmBtn.disabled = false;
}

function goNext() {
  if (!answeredCurrent) return;
  idx += 1;
  if (idx >= activeQuestions.length) {
    finish();
    return;
  }
  renderQuestion();
}

const SESSION_QUESTION_COUNT = 20;

function shuffleCopy(arr) {
  const a = arr.slice();
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    const t = a[i];
    a[i] = a[j];
    a[j] = t;
  }
  return a;
}

function start() {
  const sid = ui.subjectSelect.value;
  const uid = ui.unitSelect.value;
  const sub = curriculum.find((s) => s.id === sid);
  const unit = sub?.units.find((u) => u.id === uid);
  const all = unit?.questions || [];
  const excluded = new Set((window.OX_EXCLUDED_PACK_NOS || []).map(Number));
  const list = all.filter(
    (q) =>
      (q.packNo == null || !excluded.has(Number(q.packNo))) && !isMastered(uid, q)
  );
  if (!list.length) {
    window.alert("이 단원은 맞춘 문제·출제 제외 번호를 반영하면 남은 문제가 없습니다.");
    return;
  }
  activeQuestions = shuffleCopy(list).slice(0, SESSION_QUESTION_COUNT);
  idx = 0;
  score = 0;
  showQuiz();
  renderQuestion();
}

function retry() {
  idx = 0;
  score = 0;
  ui.resultCard.classList.add("hidden");
  start();
}

function bind() {
  ui.subjectSelect.addEventListener("change", fillUnits);
  ui.startBtn.addEventListener("click", start);
  ui.btnO.addEventListener("click", () => answer(true));
  ui.btnX.addEventListener("click", () => answer(false));
  if (ui.confirmBtn) ui.confirmBtn.addEventListener("click", goNext);
  ui.retryBtn.addEventListener("click", retry);
}

async function boot() {
  bind();

  const fallback = window.OX_CURRICULUM || [];
  curriculum = fallback;
  fillSubjects();
  fillUnits();

  if (USE_LOCAL_ONLY) return;

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

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
  homeBtn: document.getElementById("homeBtn"),
  finalScore: document.getElementById("finalScore"),
  retryBtn: document.getElementById("retryBtn"),
};

let curriculum = [];
let activeQuestions = [];
/** @type {null | { locked: boolean, userAnswer: boolean, ok: boolean, hintText: string }} */
let quizSession = [];
let idx = 0;
let score = 0;
let answeredCurrent = false;
/** false: `/api/env?format=json`로 키를 읽고 Supabase에서 과목·단원·문제를 불러옴. 실패 시 data.js 유지 */
const USE_LOCAL_ONLY = false;
const MASTERED_KEY = "ox-mastered-v1";
/** 같은 문항(body)을 이 횟수만큼 맞추면 이후 출제에서 제외 */
const MASTER_EXCLUDE_AFTER_CORRECT = 2;

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

/** @returns {number} 해당 문항을 맞춘 누적 횟수 (구버전 true → 2로 간주해 계속 제외) */
function getCorrectCount(unitId, body) {
  const map = readMasteredMap();
  const unitMap = map[unitId];
  if (!unitMap || typeof unitMap !== "object") return 0;
  const v = unitMap[body];
  if (v === true) return MASTER_EXCLUDE_AFTER_CORRECT;
  if (typeof v === "number" && Number.isFinite(v)) return Math.max(0, Math.floor(v));
  return 0;
}

function questionBodyKey(q) {
  const b = (q.body != null && String(q.body).trim() !== "") ? String(q.body).trim() : "";
  if (b) return b;
  const qq = (q.question != null ? String(q.question) : "").trim();
  const ct = (q.choice_text != null ? String(q.choice_text) : "").trim();
  if (qq && ct) return `문제: ${qq}\n\n선지: ${ct}`;
  return "";
}

function isMastered(unitId, question) {
  return getCorrectCount(unitId, questionBodyKey(question)) >= MASTER_EXCLUDE_AFTER_CORRECT;
}

function recordCorrect(unitId, question) {
  const map = readMasteredMap();
  if (!map[unitId] || typeof map[unitId] !== "object") map[unitId] = {};
  const body = questionBodyKey(question);
  const next = Math.min(MASTER_EXCLUDE_AFTER_CORRECT, getCorrectCount(unitId, body) + 1);
  map[unitId][body] = next;
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
            packNo: q.pack_no != null ? Number(q.pack_no) : null,
            question: (q.question ?? "").toString(),
            choice_text: (q.choice_text ?? "").toString(),
            body: (() => {
              if (q.body != null && String(q.body).trim() !== "") return String(q.body).trim();
              const qq = (q.question ?? "").toString().trim();
              const ct = (q.choice_text ?? "").toString().trim();
              return qq && ct ? `문제: ${qq}\n\n선지: ${ct}` : "";
            })(),
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
    client
      .from("quiz_questions")
      .select("id,unit_id,question,choice_text,body,answer,explanation,sort_order,pack_no")
      .order("sort_order"),
  ]);

  if (subRes.error) throw subRes.error;
  if (unitRes.error) throw unitRes.error;
  if (qRes.error) throw qRes.error;

  const cur = buildCurriculumFromRows(subRes.data, unitRes.data, qRes.data);

  const cfgRes = await client.from("quiz_settings").select("value").eq("key", "excluded_pack_nos").maybeSingle();
  if (!cfgRes.error && cfgRes.data && Array.isArray(cfgRes.data.value) && cfgRes.data.value.length) {
    window.OX_EXCLUDED_PACK_NOS = cfgRes.data.value
      .map((n) => Number(n))
      .filter((n) => Number.isFinite(n));
  }

  return cur;
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
  if (ui.homeBtn) ui.homeBtn.classList.add("hidden");
}

function hasQuizProgress() {
  if (!activeQuestions.length) return false;
  if (idx > 0 || answeredCurrent) return true;
  return quizSession.some((s) => s != null);
}

function goHome() {
  if (!ui.pickCard.classList.contains("hidden")) return;
  const inQuiz = !ui.quizCard.classList.contains("hidden");
  const inResult = !ui.resultCard.classList.contains("hidden");
  if (inQuiz && hasQuizProgress()) {
    if (!window.confirm("처음 화면(과목·단원 선택)으로 돌아갈까요?")) return;
  } else if (inResult) {
    if (!window.confirm("처음 화면(과목·단원 선택)으로 돌아갈까요?")) return;
  }
  activeQuestions = [];
  quizSession = [];
  idx = 0;
  score = 0;
  answeredCurrent = false;
  showPick();
}

function showQuiz() {
  ui.pickCard.classList.add("hidden");
  ui.quizCard.classList.remove("hidden");
  ui.resultCard.classList.add("hidden");
  if (ui.homeBtn) ui.homeBtn.classList.remove("hidden");
}

function parseQuestionParts(q) {
  const qq = (q.question != null ? String(q.question) : "").trim();
  const ct = (q.choice_text != null ? String(q.choice_text) : "").trim();
  if (qq !== "" && ct !== "") return { stem: qq, choice: ct };

  const body = (q.body || "").toString();
  const marker = "\n\n선지:";
  if (body.includes(marker)) {
    const [stem, choice] = body.split(marker);
    const stemT = stem.replace(/^문제:\s*/, "").trim();
    const choiceT = choice.trim();
    return { stem: stemT, choice: choiceT };
  }
  if (body.includes("선지:")) {
    const parts = body.split("선지:");
    const stemT = parts[0].replace(/^문제:\s*/, "").trim();
    const choiceT = (parts[1] || "").trim();
    return { stem: stemT, choice: choiceT };
  }
  return { stem: body.trim(), choice: "" };
}

/** 4지선다형 기출 꼬리 문구 — OX 화면에서는 지문만 보이도록 제거(데이터·저장 키는 그대로) */
function stripMcQuestionTail(stem) {
  if (!stem) return stem;
  const patterns = [
    /\s*에\s*대한\s*설명으로\s*가장\s*옳지\s*않은\s*것은\??\s*$/u,
    /\s*중\s*가장\s*옳지\s*않은\s*것은\??\s*$/u,
    /\s*으로\s*가장\s*옳지\s*않은\s*것은\??\s*$/u,
    /(?<!으)\s*로\s*가장\s*옳지\s*않은\s*것은\??\s*$/u,
    /\s*으로\s*가장\s*옳은\s*것은\??\s*$/u,
    /\s*경우로\s*가장\s*옳은\s*것은\??\s*$/u,
    /(?<!으)\s*로\s*가장\s*옳은\s*것은\??\s*$/u,
    /\s*가장\s*옳지\s*않은\s*것은\??\s*$/u,
    /\s*가장\s*옳은\s*것은\??\s*$/u,
  ];
  let s = stem;
  for (const re of patterns) {
    s = s.replace(re, "");
  }
  return s.trim();
}

function fillQuestionPanels(q) {
  const { stem, choice } = parseQuestionParts(q);
  ui.question.textContent = stripMcQuestionTail(stem);
  if (ui.choiceText) ui.choiceText.textContent = choice;
}

function renderQuestion() {
  const q = activeQuestions[idx];
  ui.progress.textContent = `${idx + 1} / ${activeQuestions.length}`;
  ui.score.textContent = `점수 ${score}`;
  fillQuestionPanels(q);

  const slot = quizSession[idx];
  if (slot?.locked) {
    ui.hint.textContent = slot.hintText;
    answeredCurrent = true;
    ui.btnO.disabled = true;
    ui.btnX.disabled = true;
    if (ui.confirmBtn) ui.confirmBtn.disabled = false;
    return;
  }
  if (slot && !slot.locked) {
    ui.hint.textContent = slot.hintText;
    answeredCurrent = true;
    ui.btnO.disabled = true;
    ui.btnX.disabled = true;
    if (ui.confirmBtn) ui.confirmBtn.disabled = false;
    return;
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
  if (ui.homeBtn) ui.homeBtn.classList.remove("hidden");
  ui.finalScore.textContent = `${activeQuestions.length}문제 중 ${score}개 맞음`;
}

function answer(userAnswer) {
  const slot = quizSession[idx];
  if (slot?.locked) return;
  if (answeredCurrent) return;
  const q = activeQuestions[idx];
  const ok = userAnswer === q.answer;
  const hintText = ok ? `정답. ${q.explanation}` : `오답. ${q.explanation}`;
  quizSession[idx] = { locked: false, userAnswer, ok, hintText };
  if (ok) {
    score += 1;
    const uid = ui.unitSelect.value;
    if (uid) recordCorrect(uid, q);
  }
  ui.hint.textContent = hintText;
  answeredCurrent = true;
  ui.btnO.disabled = true;
  ui.btnX.disabled = true;
  if (ui.confirmBtn) ui.confirmBtn.disabled = false;
}

function goNext() {
  if (!answeredCurrent) return;
  const slot = quizSession[idx];
  if (!slot) return;
  if (!slot.locked) slot.locked = true;
  idx += 1;
  answeredCurrent = false;
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
    window.alert(
      "이 단원은 2회 이상 맞춘 문항·출제 제외 번호를 반영하면 남은 문제가 없습니다."
    );
    return;
  }
  if (list.length < SESSION_QUESTION_COUNT) {
    window.alert(
      `선지 단위 문항이 ${SESSION_QUESTION_COUNT}개 미만입니다(현재 ${list.length}개). 한 세션은 ${SESSION_QUESTION_COUNT}문항으로 진행됩니다.`
    );
    return;
  }
  activeQuestions = shuffleCopy(list).slice(0, SESSION_QUESTION_COUNT);
  quizSession = activeQuestions.map(() => null);
  idx = 0;
  score = 0;
  showQuiz();
  renderQuestion();
}

function retry() {
  idx = 0;
  score = 0;
  quizSession = [];
  ui.resultCard.classList.add("hidden");
  start();
}

function bind() {
  ui.subjectSelect.addEventListener("change", fillUnits);
  ui.startBtn.addEventListener("click", start);
  ui.btnO.addEventListener("click", () => answer(true));
  ui.btnX.addEventListener("click", () => answer(false));
  if (ui.confirmBtn) ui.confirmBtn.addEventListener("click", goNext);
  if (ui.homeBtn) ui.homeBtn.addEventListener("click", goHome);
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

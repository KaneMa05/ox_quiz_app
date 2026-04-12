const ui = {
  pickCard: document.getElementById("pickCard"),
  quizCard: document.getElementById("quizCard"),
  resultCard: document.getElementById("resultCard"),
  subjectSelect: document.getElementById("subjectSelect"),
  majorUnitRow: document.getElementById("majorUnitRow"),
  pickTierWrap: document.getElementById("pickTierWrap"),
  pickUnitRow: document.getElementById("pickUnitRow"),
  majorSelect: document.getElementById("majorSelect"),
  minorLabel: document.getElementById("minorLabel"),
  unitSelect: document.getElementById("unitSelect"),
  startBtn: document.getElementById("startBtn"),
  wrongReviewBtn: document.getElementById("wrongReviewBtn"),
  quizModeBadge: document.getElementById("quizModeBadge"),
  resetMasteredBtn: document.getElementById("resetMasteredBtn"),
  resetModal: document.getElementById("resetModal"),
  resetModalCancel: document.getElementById("resetModalCancel"),
  resetModalConfirm: document.getElementById("resetModalConfirm"),
  progress: document.getElementById("progress"),
  score: document.getElementById("score"),
  question: document.getElementById("question"),
  choiceText: document.getElementById("choiceText"),
  hint: document.getElementById("hint"),
  btnO: document.getElementById("btnO"),
  btnX: document.getElementById("btnX"),
  confirmBtn: document.getElementById("confirmBtn"),
  removeWrongBtn: document.getElementById("removeWrongBtn"),
  homeBtn: document.getElementById("homeBtn"),
  finalScore: document.getElementById("finalScore"),
  retryBtn: document.getElementById("retryBtn"),
  dataSourceNote: document.getElementById("dataSourceNote"),
};

/** @type {HTMLElement | null} */
let resetModalPrevFocus = null;

let curriculum = [];
let activeQuestions = [];
/** @type {null | { locked: boolean, userAnswer: boolean, ok: boolean, hintText: string }} */
let quizSession = [];
let idx = 0;
let score = 0;
let answeredCurrent = false;
/** true: 선택 단원의 저장된 오답만 출제 */
let wrongReviewMode = false;
/** false: `/api/env?format=json`로 키를 읽고 Supabase에서 과목·단원·문제를 불러옴. 실패 시 data.js 유지 */
const USE_LOCAL_ONLY = false;

/** "supabase" | "local_js" — 해양경찰학개론 예시는 data.js에 4문항만 있어, 로컬이면 DB 미연결과 동일한 증상이 납니다. */
let curriculumDataSource = "local_js";
const MASTERED_KEY = "ox-mastered-v1";
const WRONG_KEY = "ox-wrong-v1";
/** 같은 문항(진행 키 = 지문+선지 조합)을 이 횟수만큼 맞추면 이후 출제에서 제외 */
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

function clearMasteredMap() {
  writeMasteredMap({});
}

function openResetMasteredModal() {
  if (!ui.resetModal) return;
  resetModalPrevFocus = /** @type {HTMLElement | null} */ (document.activeElement);
  ui.resetModal.classList.remove("hidden");
  ui.resetModal.setAttribute("aria-hidden", "false");
  if (ui.resetModalConfirm) ui.resetModalConfirm.focus();
}

function closeResetMasteredModal() {
  if (!ui.resetModal) return;
  ui.resetModal.classList.add("hidden");
  ui.resetModal.setAttribute("aria-hidden", "true");
  if (resetModalPrevFocus && typeof resetModalPrevFocus.focus === "function") {
    resetModalPrevFocus.focus();
  }
  resetModalPrevFocus = null;
}

function onResetModalKeydown(ev) {
  if (!ui.resetModal || ui.resetModal.classList.contains("hidden")) return;
  if (ev.key === "Escape") {
    ev.preventDefault();
    closeResetMasteredModal();
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

function readWrongMap() {
  try {
    const raw = localStorage.getItem(WRONG_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw);
    return parsed && typeof parsed === "object" ? parsed : {};
  } catch {
    return {};
  }
}

function writeWrongMap(next) {
  try {
    localStorage.setItem(WRONG_KEY, JSON.stringify(next));
  } catch {
    // ignore
  }
}

function addWrong(unitId, question) {
  const k = questionBodyKey(question);
  if (!unitId || !k) return;
  const map = readWrongMap();
  if (!map[unitId] || typeof map[unitId] !== "object") map[unitId] = {};
  map[unitId][k] = true;
  writeWrongMap(map);
}

function removeWrong(unitId, question) {
  const k = questionBodyKey(question);
  if (!unitId || !k) return;
  const map = readWrongMap();
  const um = map[unitId];
  if (!um || typeof um !== "object") return;
  delete um[k];
  if (!Object.keys(um).length) delete map[unitId];
  writeWrongMap(map);
}

function getWrongKeysForUnit(unitId) {
  const um = readWrongMap()[unitId];
  if (!um || typeof um !== "object") return new Set();
  return new Set(Object.keys(um));
}

async function loadEnvJson() {
  try {
    const res = await fetch("/api/env?format=json", { cache: "no-store" });
    if (!res.ok) {
      console.warn("OX: /api/env 응답 실패", res.status, res.statusText);
      return {};
    }
    return (await res.json()) || {};
  } catch (e) {
    console.warn("OX: /api/env 요청 오류", e);
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

function eqUuid(a, b) {
  return a != null && b != null && String(a).toLowerCase() === String(b).toLowerCase();
}

/** parent_unit_id → 소단원 목록 Map 키용(PostgREST·select value 간 대소문자 차이 방지) */
function uuidMapKey(v) {
  if (v == null || v === "") return "";
  return String(v).toLowerCase();
}

function embeddedQuizItem(q) {
  const raw = q.quiz_items;
  if (raw == null) return null;
  return Array.isArray(raw) ? raw[0] ?? null : raw;
}

function mapQuestionRowFromDb(q) {
  const item = embeddedQuizItem(q);
  const stemFromItem = item && item.stem != null ? String(item.stem).trim() : "";
  const stem = stemFromItem || (q.question ?? "").toString();
  const choiceText = (q.choice_text ?? "").toString();
  const packFromRow = q.pack_no != null ? Number(q.pack_no) : null;
  const packFromItem = item && item.pack_no != null ? Number(item.pack_no) : null;
  const packNo = packFromRow != null ? packFromRow : packFromItem;

  return {
    packNo: Number.isFinite(packNo) ? packNo : null,
    question: stem,
    choice_text: choiceText,
    body: (() => {
      const qq = stem.trim();
      const ct = choiceText.trim();
      return qq && ct ? `문제: ${qq}\n\n선지: ${ct}` : "";
    })(),
    answer: q.answer,
    explanation: q.explanation || "",
  };
}

function buildCurriculumFromRows(subjects, units, questions) {
  const subs = (subjects || []).slice().sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0));
  const uns = (units || []).slice().sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0));
  const qs = (questions || []).slice().sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0));

  return subs.map((s) => {
    const sunits = uns.filter((u) => eqUuid(u.subject_id, s.id));
    const hasHierarchy = sunits.some((u) => u.parent_unit_id);

    if (!hasHierarchy) {
      return {
        id: s.id,
        name: s.name,
        units: sunits
          .filter((u) => !u.parent_unit_id)
          .map((u) => ({
            id: u.id,
            name: u.name,
            questions: qs.filter((qq) => eqUuid(qq.unit_id, u.id)).map(mapQuestionRowFromDb),
          })),
      };
    }

    const majors = sunits
      .filter((u) => !u.parent_unit_id)
      .sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0));
    const minorsByParent = new Map();
    for (const u of sunits.filter((x) => x.parent_unit_id)) {
      const pid = uuidMapKey(u.parent_unit_id);
      if (!minorsByParent.has(pid)) minorsByParent.set(pid, []);
      minorsByParent.get(pid).push(u);
    }

    return {
      id: s.id,
      name: s.name,
      units: majors.map((ma) => ({
        id: ma.id,
        name: ma.name,
        children: (minorsByParent.get(uuidMapKey(ma.id)) || [])
          .slice()
          .sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0))
          .map((mi) => ({
            id: mi.id,
            name: mi.name,
            // 소단원 id + 그 부모 대단원 id(실수로 대단원에만 넣은 문항도 소단원에서 출제되게)
            questions: qs
              .filter((qq) => eqUuid(qq.unit_id, mi.id) || eqUuid(qq.unit_id, ma.id))
              .map(mapQuestionRowFromDb),
          })),
      })),
    };
  });
}

/** DB·data.js에서 parent/children으로 만든 계층이면 true(소단원 문항이 0개인 대단원만 있어도 대단원·소단원 UI 유지). */
function subjectHasTieredUnits(sub) {
  return !!(sub?.units?.length && sub.units.some((u) => Array.isArray(u.children)));
}

function findLeafUnit(sub, leafId) {
  if (!sub?.units || !leafId) return null;
  if (subjectHasTieredUnits(sub)) {
    for (const m of sub.units) {
      const c = m.children?.find((x) => eqUuid(x.id, leafId));
      if (c) return c;
    }
    return null;
  }
  return sub.units.find((u) => eqUuid(u.id, leafId)) || null;
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
    client.from("quiz_units").select("id,subject_id,parent_unit_id,name,sort_order").order("sort_order"),
    client
      .from("quiz_questions")
      .select(
        "id,unit_id,item_id,question,choice_text,answer,explanation,sort_order,pack_no,quiz_items(stem,pack_no,item_type,sort_order)",
      )
      .order("sort_order")
      // PostgREST 기본 max-rows(예: 1000) 넘으면 뒤쪽 문항이 잘려 단원에 문제가 없는 것처럼 보일 수 있음
      .limit(20000),
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

function fillMinorUnits() {
  const sid = ui.subjectSelect.value;
  const sub = curriculum.find((s) => eqUuid(s.id, sid));
  if (!sub || !subjectHasTieredUnits(sub) || !ui.majorSelect) return;
  const mid = ui.majorSelect.value;
  const major = sub.units.find((u) => eqUuid(u.id, mid));
  const children = major?.children || [];
  ui.unitSelect.innerHTML = "";
  for (const c of children) {
    const opt = document.createElement("option");
    opt.value = c.id;
    opt.textContent = c.name;
    ui.unitSelect.appendChild(opt);
  }
}

function fillPickerUnits() {
  const sid = ui.subjectSelect.value;
  const sub = curriculum.find((s) => eqUuid(s.id, sid));
  if (!sub) return;
  const tiered = subjectHasTieredUnits(sub);
  if (ui.pickTierWrap) {
    ui.pickTierWrap.classList.toggle("hidden", !tiered);
    ui.pickTierWrap.setAttribute("aria-hidden", tiered ? "false" : "true");
  }
  if (ui.pickUnitRow) ui.pickUnitRow.classList.toggle("pickUnitRow--minor", tiered);
  if (ui.minorLabel) ui.minorLabel.textContent = tiered ? "소단원" : "단원";
  if (tiered && ui.majorSelect) {
    ui.majorSelect.innerHTML = "";
    for (const m of sub.units) {
      const opt = document.createElement("option");
      opt.value = m.id;
      opt.textContent = m.name;
      ui.majorSelect.appendChild(opt);
    }
    fillMinorUnits();
  } else {
    ui.unitSelect.innerHTML = "";
    for (const u of sub.units) {
      const opt = document.createElement("option");
      opt.value = u.id;
      opt.textContent = u.name;
      ui.unitSelect.appendChild(opt);
    }
  }
}

function showPick() {
  wrongReviewMode = false;
  updateQuizModeBadge();
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

function updateQuizModeBadge() {
  if (!ui.quizModeBadge) return;
  if (wrongReviewMode) {
    ui.quizModeBadge.textContent = "오답 모아보기";
    ui.quizModeBadge.classList.remove("hidden");
  } else {
    ui.quizModeBadge.textContent = "";
    ui.quizModeBadge.classList.add("hidden");
  }
}

function updateRemoveWrongBtnVisibility() {
  if (!ui.removeWrongBtn) return;
  if (wrongReviewMode && activeQuestions.length > 0 && idx < activeQuestions.length) {
    ui.removeWrongBtn.classList.remove("hidden");
  } else {
    ui.removeWrongBtn.classList.add("hidden");
  }
}

function showQuiz() {
  ui.pickCard.classList.add("hidden");
  ui.quizCard.classList.remove("hidden");
  ui.resultCard.classList.add("hidden");
  if (ui.homeBtn) ui.homeBtn.classList.remove("hidden");
  updateQuizModeBadge();
  updateRemoveWrongBtnVisibility();
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
    updateRemoveWrongBtnVisibility();
    return;
  }
  if (slot && !slot.locked) {
    ui.hint.textContent = slot.hintText;
    answeredCurrent = true;
    ui.btnO.disabled = true;
    ui.btnX.disabled = true;
    if (ui.confirmBtn) ui.confirmBtn.disabled = false;
    updateRemoveWrongBtnVisibility();
    return;
  }

  ui.hint.textContent = "";
  answeredCurrent = false;
  ui.btnO.disabled = false;
  ui.btnX.disabled = false;
  if (ui.confirmBtn) ui.confirmBtn.disabled = true;
  updateRemoveWrongBtnVisibility();
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
  const uid = ui.unitSelect.value;
  if (ok) {
    score += 1;
    if (uid) {
      recordCorrect(uid, q);
      if (!wrongReviewMode) removeWrong(uid, q);
    }
  } else if (uid) {
    addWrong(uid, q);
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

/** 오답 모아보기: 저장된 오답만 지우고(점수·맞춤 기록 불변) 현재 세션에서도 빼기 */
function removeCurrentFromWrongList() {
  if (!wrongReviewMode) return;
  const uid = ui.unitSelect.value;
  const q = activeQuestions[idx];
  if (!uid || !q) return;
  if (
    !window.confirm(
      "이 문항을 오답 목록에서만 제거할까요?\n(점수와 2회 맞춤 기록은 바뀌지 않습니다. 지금 세션에서도 건너뜁니다.)"
    )
  ) {
    return;
  }
  removeWrong(uid, q);
  activeQuestions.splice(idx, 1);
  quizSession.splice(idx, 1);
  if (!activeQuestions.length) {
    wrongReviewMode = false;
    activeQuestions = [];
    quizSession = [];
    idx = 0;
    score = 0;
    answeredCurrent = false;
    showPick();
    window.alert("남은 문항이 없어 처음 화면으로 돌아갑니다.");
    return;
  }
  if (idx >= activeQuestions.length) idx = activeQuestions.length - 1;
  answeredCurrent = false;
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
  wrongReviewMode = false;
  const sid = ui.subjectSelect.value;
  const uid = ui.unitSelect.value;
  const sub = curriculum.find((s) => eqUuid(s.id, sid));
  const unit = findLeafUnit(sub, uid);
  const all = unit?.questions || [];
  const excluded = new Set((window.OX_EXCLUDED_PACK_NOS || []).map(Number));
  const list = all.filter(
    (q) =>
      (q.packNo == null || !excluded.has(Number(q.packNo))) && !isMastered(uid, q)
  );
  if (!list.length) {
    if (!unit) {
      window.alert(
        "선택한 단원 정보를 찾지 못했습니다. 새로고침 후 과목·대단원·소단원을 다시 고르고 시작해 보세요."
      );
    } else if (!all.length) {
      window.alert(
        "이 소단원에 붙은 문항이 앱 쪽에서는 0개입니다.\n" +
          "· Supabase Table Editor에 quiz_questions 행이 있는지\n" +
          "· 배포 사이트(Vercel)의 환경 변수가 지금 확인 중인 DB와 같은 프로젝트인지\n" +
          "· 최신 앱(문항 한도 확대·대단원 UUID 문항 포함 패치)이 배포됐는지\n" +
          "를 확인해 보세요."
      );
    } else {
      const nPack = all.filter((q) => q.packNo != null && excluded.has(Number(q.packNo))).length;
      const nMaster = all.filter((q) => isMastered(uid, q)).length;
      window.alert(
        `이 단원 문항은 DB에서 ${all.length}개 불러왔지만, 출제 가능한 문항이 0개입니다.\n` +
          `· 출제 제외 pack 번호에 해당: ${nPack}개 (quiz_settings.excluded_pack_nos)\n` +
          `· 이미 2회 이상 맞춰 제외: ${nMaster}개\n` +
          `하단 「맞춤 기록 초기화」로 맞춤 기록을 지우거나, 제외 pack 설정을 확인해 보세요.`
      );
    }
    return;
  }
  const take = Math.min(SESSION_QUESTION_COUNT, list.length);
  if (list.length < SESSION_QUESTION_COUNT) {
    window.alert(
      `이 소단원(단원)의 출제 가능 문항이 ${SESSION_QUESTION_COUNT}개 미만입니다(현재 ${list.length}개). ${take}문항으로 진행합니다.`
    );
  }
  activeQuestions = shuffleCopy(list).slice(0, take);
  quizSession = activeQuestions.map(() => null);
  idx = 0;
  score = 0;
  showQuiz();
  renderQuestion();
}

function startWrongReview() {
  const sid = ui.subjectSelect.value;
  const uid = ui.unitSelect.value;
  const sub = curriculum.find((s) => eqUuid(s.id, sid));
  const unit = findLeafUnit(sub, uid);
  const all = unit?.questions || [];
  const excluded = new Set((window.OX_EXCLUDED_PACK_NOS || []).map(Number));
  const wrongKeys = getWrongKeysForUnit(uid);
  const list = all.filter((q) => {
    const k = questionBodyKey(q);
    if (!k) return false;
    if (q.packNo != null && excluded.has(Number(q.packNo))) return false;
    return wrongKeys.has(k);
  });
  if (!list.length) {
    window.alert(
      wrongReviewMode
        ? "이 단원에 더 모아볼 오답이 없습니다. (오답 모아보기에서 맞춰도 목록은 유지되며, 하단 「오답 목록에서 제거」로만 지울 수 있습니다.)"
        : "이 단원에 저장된 오답이 없습니다. 일반 퀴즈에서 틀린 문항이 쌓이면 여기서 모아볼 수 있습니다."
    );
    wrongReviewMode = false;
    showPick();
    return;
  }
  wrongReviewMode = true;
  const take = Math.min(SESSION_QUESTION_COUNT, list.length);
  activeQuestions = shuffleCopy(list).slice(0, take);
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
  if (wrongReviewMode) {
    startWrongReview();
  } else {
    start();
  }
}

function bind() {
  ui.subjectSelect.addEventListener("change", fillPickerUnits);
  if (ui.majorSelect) ui.majorSelect.addEventListener("change", fillMinorUnits);
  ui.startBtn.addEventListener("click", start);
  if (ui.wrongReviewBtn) ui.wrongReviewBtn.addEventListener("click", startWrongReview);
  if (ui.removeWrongBtn) ui.removeWrongBtn.addEventListener("click", removeCurrentFromWrongList);
  ui.btnO.addEventListener("click", () => answer(true));
  ui.btnX.addEventListener("click", () => answer(false));
  if (ui.confirmBtn) ui.confirmBtn.addEventListener("click", goNext);
  if (ui.homeBtn) ui.homeBtn.addEventListener("click", goHome);
  ui.retryBtn.addEventListener("click", retry);

  if (ui.resetMasteredBtn) ui.resetMasteredBtn.addEventListener("click", openResetMasteredModal);
  if (ui.resetModalCancel) ui.resetModalCancel.addEventListener("click", closeResetMasteredModal);
  if (ui.resetModalConfirm) {
    ui.resetModalConfirm.addEventListener("click", () => {
      clearMasteredMap();
      closeResetMasteredModal();
    });
  }
  if (ui.resetModal) {
    ui.resetModal.addEventListener("click", (ev) => {
      const t = /** @type {HTMLElement} */ (ev.target);
      if (t?.dataset?.modalDismiss === "true") closeResetMasteredModal();
    });
  }
  document.addEventListener("keydown", onResetModalKeydown);
}

function renderDataSourceNote() {
  const el = ui.dataSourceNote;
  if (!el) return;
  if (USE_LOCAL_ONLY) {
    el.classList.remove("hidden");
    el.textContent = "로컬 전용 모드: data.js에 들어 있는 문항만 사용합니다.";
    return;
  }
  if (curriculumDataSource === "supabase") {
    el.classList.add("hidden");
    el.textContent = "";
    return;
  }
  el.classList.remove("hidden");
  el.textContent =
    "Supabase에 연결되지 않아 내장 data.js 예시만 사용 중입니다. (해양경찰학개론·역사는 예시 4문항.) " +
    "Vercel → Project → Settings → Environment Variables에 SUPABASE_ANON_KEY와 SUPABASE_URL(또는 SUPABASE_PROJECT_ID)을 추가하고 재배포한 뒤, " +
    "브라우저에서 /api/env?format=json 을 열어 값이 채워지는지 확인하세요. (개발자 도구 콘솔에 /api/env 관련 경고가 있으면 그 HTTP 상태를 참고하세요.)";
}

async function boot() {
  bind();

  curriculumDataSource = "local_js";
  const fallback = window.OX_CURRICULUM || [];
  curriculum = fallback;
  fillSubjects();
  fillPickerUnits();

  if (USE_LOCAL_ONLY) {
    renderDataSourceNote();
    return;
  }

  const env = await loadEnvJson();
  const anon = (env.SUPABASE_ANON_KEY || "").trim();
  const hasKeys = Boolean(
    anon.length >= 20 && (supabaseUrlFromEnv(env) || "").trim()
  );
  if (env.envHint && typeof env.envHint === "string") {
    console.warn("OX:", env.envHint);
  }

  if (!hasKeys) {
    console.warn("OX: /api/env 에 Supabase URL·anon 키가 없어 data.js 로 폴백합니다.");
    renderDataSourceNote();
    return;
  }

  if (!window.supabase?.createClient) {
    console.warn("OX: supabase-js 스크립트가 없어 data.js 로 폴백합니다.");
    renderDataSourceNote();
    return;
  }

  try {
    const fromDb = await loadCurriculumFromSupabase(env);
    if (fromDb && fromDb.length) {
      curriculum = fromDb;
      curriculumDataSource = "supabase";
      fillSubjects();
      fillPickerUnits();
    } else {
      console.warn("OX: Supabase에서 과목이 0개라 data.js 로 폴백합니다.", fromDb);
    }
  } catch (e) {
    console.warn("Supabase 로드 실패, 로컬 data.js 사용:", e);
  }
  renderDataSourceNote();
}

boot();

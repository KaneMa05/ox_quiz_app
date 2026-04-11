/**
 * data.js의 OX_CURRICULUM·OX_EXCLUDED_PACK_NOS를 Supabase에 반영합니다.
 * 로컬 전용: SUPABASE_SERVICE_ROLE_KEY는 브라우저·Vercel(anon)에 넣지 마세요.
 *
 * 환경 변수:
 *   SUPABASE_URL
 *   SUPABASE_SERVICE_ROLE_KEY
 *   OX_DB_SYNC_SUBJECTS (선택) — 쉼표로 과목명. 비우거나 "all"이면 data.js의 전체 과목.
 */
import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";
import { fileURLToPath } from "node:url";
import dotenv from "dotenv";
import { createClient } from "@supabase/supabase-js";
import { v5 as uuidv5 } from "uuid";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const APP_ROOT = path.join(__dirname, "..");

dotenv.config({ path: path.join(APP_ROOT, ".env.local") });
dotenv.config({ path: path.join(APP_ROOT, ".env") });

/** 결정적 UUID용 네임스페이스(임의 고정 UUID). */
const NS = "a1e2c3d4-b5a6-4789-a012-3456789abcde";

function loadDataJs() {
  const dataPath = path.join(APP_ROOT, "data.js");
  const code = fs.readFileSync(dataPath, "utf8");
  const sandbox = { window: {}, console };
  vm.createContext(sandbox);
  vm.runInContext(code, sandbox, { filename: "data.js" });
  const curriculum = sandbox.window.OX_CURRICULUM;
  const excluded = sandbox.window.OX_EXCLUDED_PACK_NOS;
  if (!Array.isArray(curriculum)) throw new Error("data.js: window.OX_CURRICULUM이 없습니다.");
  return {
    curriculum,
    excluded: Array.isArray(excluded) ? excluded.map(Number).filter((n) => Number.isFinite(n)) : [],
  };
}

function filterSubjects(curriculum) {
  const raw = (process.env.OX_DB_SYNC_SUBJECTS || "").trim();
  if (!raw || raw.toLowerCase() === "all") return curriculum;
  const want = new Set(
    raw
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean),
  );
  return curriculum.filter((s) => want.has(s.name));
}

function isTieredSubject(subject) {
  const u0 = subject.units?.[0];
  return !!(u0 && Array.isArray(u0.children));
}

function subjectUuid(subject) {
  return uuidv5(`subject:${subject.id}`, NS);
}

function unitUuid(subject, ...pathSeg) {
  return uuidv5(`unit:${subject.id}/${pathSeg.join("/")}`, NS);
}

function questionUuid(subject, unitKey, index) {
  return uuidv5(`q:${subject.id}/${unitKey}/${index}`, NS);
}

function rowQuestion(subject, unitKey, qi, q, unitId) {
  return {
    id: questionUuid(subject, unitKey, qi),
    unit_id: unitId,
    question: q.question ?? "",
    choice_text: q.choice_text ?? "",
    body: q.body ?? "",
    answer: !!q.answer,
    explanation: q.explanation ?? null,
    sort_order: qi,
    pack_no: q.packNo == null ? null : Number(q.packNo),
    is_active: true,
  };
}

async function insertChunks(supabase, table, rows, size = 250) {
  for (let i = 0; i < rows.length; i += size) {
    const chunk = rows.slice(i, i + size);
    const { error } = await supabase.from(table).insert(chunk);
    if (error) throw error;
  }
}

async function replaceSubjectTree(supabase, subject, sortOrder) {
  const { error: delErr } = await supabase.from("quiz_subjects").delete().eq("name", subject.name);
  if (delErr) throw delErr;

  const sid = subjectUuid(subject);
  const { error: subErr } = await supabase.from("quiz_subjects").insert({
    id: sid,
    name: subject.name,
    sort_order: sortOrder,
    is_active: true,
  });
  if (subErr) throw subErr;

  const unitRows = [];
  const questionRows = [];

  if (isTieredSubject(subject)) {
    subject.units.forEach((major, mi) => {
      const mid = unitUuid(subject, major.id);
      unitRows.push({
        id: mid,
        subject_id: sid,
        parent_unit_id: null,
        name: major.name,
        sort_order: mi,
        is_active: true,
      });
      const children = major.children || [];
      children.forEach((minor, ci) => {
        const nid = unitUuid(subject, major.id, minor.id);
        unitRows.push({
          id: nid,
          subject_id: sid,
          parent_unit_id: mid,
          name: minor.name,
          sort_order: ci,
          is_active: true,
        });
        const qs = minor.questions || [];
        const unitKey = `${major.id}/${minor.id}`;
        qs.forEach((q, qi) => {
          questionRows.push(rowQuestion(subject, unitKey, qi, q, nid));
        });
      });
    });
  } else {
    (subject.units || []).forEach((unit, ui) => {
      const uid = unitUuid(subject, unit.id);
      unitRows.push({
        id: uid,
        subject_id: sid,
        parent_unit_id: null,
        name: unit.name,
        sort_order: ui,
        is_active: true,
      });
      const qs = unit.questions || [];
      qs.forEach((q, qi) => {
        questionRows.push(rowQuestion(subject, unit.id, qi, q, uid));
      });
    });
  }

  if (unitRows.length) {
    await insertChunks(supabase, "quiz_units", unitRows);
  }
  if (questionRows.length) {
    await insertChunks(supabase, "quiz_questions", questionRows);
  }

  return { units: unitRows.length, questions: questionRows.length };
}

async function upsertExcludedPackNos(supabase, excluded) {
  const { error } = await supabase.from("quiz_settings").upsert(
    {
      key: "excluded_pack_nos",
      value: excluded,
      updated_at: new Date().toISOString(),
    },
    { onConflict: "key" },
  );
  if (error) throw error;
}

async function main() {
  const url = (process.env.SUPABASE_URL || "").trim();
  const key = (process.env.SUPABASE_SERVICE_ROLE_KEY || "").trim();
  if (!url || !key) {
    console.error("SUPABASE_URL 과 SUPABASE_SERVICE_ROLE_KEY 가 필요합니다(.env / .env.local).");
    process.exit(1);
  }

  const { curriculum: all, excluded } = loadDataJs();
  const toSync = filterSubjects(all);
  if (!toSync.length) {
    console.error("동기화할 과목이 없습니다. OX_DB_SYNC_SUBJECTS 과목명을 확인하세요.");
    process.exit(1);
  }

  const supabase = createClient(url, key, {
    auth: { persistSession: false, autoRefreshToken: false },
  });

  console.log(`과목 ${toSync.length}개 동기화: ${toSync.map((s) => s.name).join(", ")}`);

  for (let i = 0; i < toSync.length; i++) {
    const sub = toSync[i];
    const globalOrder = all.indexOf(sub);
    const sortOrder = globalOrder >= 0 ? globalOrder : i;
    const stats = await replaceSubjectTree(supabase, sub, sortOrder);
    console.log(`  ✓ ${sub.name} — 단원 ${stats.units}개, 문항 ${stats.questions}개`);
  }

  await upsertExcludedPackNos(supabase, excluded);
  console.log(`quiz_settings.excluded_pack_nos 갱신 (${excluded.length}개).`);
  console.log("완료.");
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});

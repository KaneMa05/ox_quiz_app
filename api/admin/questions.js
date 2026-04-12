/**
 * 문제(선지) 행 삽입·삭제 — 서버에서만 SUPABASE_SERVICE_ROLE_KEY 사용.
 * 헤더: x-ox-admin-secret: <OX_ADMIN_SECRET 과 일치>
 */
import { createClient } from "@supabase/supabase-js";

function supabaseUrl() {
  const u = (process.env.SUPABASE_URL || "").trim();
  if (u) return u;
  const id = (process.env.SUPABASE_PROJECT_ID || "").trim();
  if (id) return `https://${id}.supabase.co`;
  return "";
}

function json(res, code, obj) {
  res.statusCode = code;
  res.setHeader("Content-Type", "application/json; charset=utf-8");
  res.setHeader("Cache-Control", "no-store");
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "POST, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type, x-ox-admin-secret");
  res.end(JSON.stringify(obj));
}

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

function readJsonBody(req) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    req.on("data", (c) => chunks.push(c));
    req.on("end", () => {
      try {
        const raw = Buffer.concat(chunks).toString("utf8");
        if (!raw.trim()) return resolve({});
        resolve(JSON.parse(raw));
      } catch (e) {
        reject(e);
      }
    });
    req.on("error", reject);
  });
}

export default async function handler(req, res) {
  if (req.method === "OPTIONS") {
    res.statusCode = 204;
    res.setHeader("Access-Control-Allow-Origin", "*");
    res.setHeader("Access-Control-Allow-Methods", "POST, OPTIONS");
    res.setHeader("Access-Control-Allow-Headers", "Content-Type, x-ox-admin-secret");
    res.end();
    return;
  }

  if (req.method !== "POST") {
    json(res, 405, { ok: false, error: "POST only" });
    return;
  }

  const expected = (process.env.OX_ADMIN_SECRET || "").trim();
  if (!expected) {
    json(res, 503, { ok: false, error: "OX_ADMIN_SECRET is not set on the server" });
    return;
  }

  const got = String(req.headers["x-ox-admin-secret"] || "").trim();
  if (got !== expected) {
    json(res, 401, { ok: false, error: "Invalid admin secret" });
    return;
  }

  const key = (process.env.SUPABASE_SERVICE_ROLE_KEY || "").trim();
  const url = supabaseUrl();
  if (!url || !key) {
    json(res, 503, { ok: false, error: "SUPABASE_URL (or PROJECT_ID) and SUPABASE_SERVICE_ROLE_KEY must be set" });
    return;
  }

  let body;
  try {
    body = await readJsonBody(req);
  } catch {
    json(res, 400, { ok: false, error: "Invalid JSON body" });
    return;
  }

  const supabase = createClient(url, key, { auth: { persistSession: false } });
  const action = String(body.action || "").trim();

  if (action === "delete") {
    const id = String(body.id || "").trim();
    if (!UUID_RE.test(id)) {
      json(res, 400, { ok: false, error: "id must be a UUID" });
      return;
    }
    const { error } = await supabase.from("quiz_questions").delete().eq("id", id);
    if (error) {
      json(res, 400, { ok: false, error: error.message });
      return;
    }
    json(res, 200, { ok: true });
    return;
  }

  if (action === "insert") {
    const unit_id = String(body.unit_id || "").trim();
    if (!UUID_RE.test(unit_id)) {
      json(res, 400, { ok: false, error: "unit_id must be a UUID" });
      return;
    }
    const question = String(body.question || "").trim();
    const choice_text = String(body.choice_text || "").trim();
    if (!question || !choice_text) {
      json(res, 400, { ok: false, error: "question and choice_text are required" });
      return;
    }
    if (typeof body.answer !== "boolean") {
      json(res, 400, { ok: false, error: "answer must be boolean" });
      return;
    }
    const explanation = body.explanation != null ? String(body.explanation).trim() : "";
    const pack_no =
      body.pack_no === null || body.pack_no === undefined || body.pack_no === ""
        ? null
        : Number(body.pack_no);
    const packFinal = Number.isFinite(pack_no) ? pack_no : null;

    let sort_order = body.sort_order;
    if (sort_order === null || sort_order === undefined || sort_order === "") {
      const { data: last, error: qerr } = await supabase
        .from("quiz_questions")
        .select("sort_order")
        .eq("unit_id", unit_id)
        .order("sort_order", { ascending: false })
        .limit(1)
        .maybeSingle();
      if (qerr) {
        json(res, 400, { ok: false, error: qerr.message });
        return;
      }
      sort_order = (last?.sort_order != null ? Number(last.sort_order) : -1) + 1;
    } else {
      sort_order = Math.floor(Number(sort_order));
      if (!Number.isFinite(sort_order)) sort_order = 0;
    }

    const row = {
      unit_id,
      question,
      choice_text,
      answer: body.answer,
      explanation: explanation || null,
      sort_order,
      pack_no: packFinal,
      is_active: body.is_active === false ? false : true,
    };

    const { data, error } = await supabase.from("quiz_questions").insert(row).select("id").single();
    if (error) {
      json(res, 400, { ok: false, error: error.message });
      return;
    }
    json(res, 200, { ok: true, id: data?.id });
    return;
  }

  json(res, 400, { ok: false, error: 'action must be "insert" or "delete"' });
}

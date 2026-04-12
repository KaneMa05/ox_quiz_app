# -*- coding: utf-8 -*-
"""data.js에서 q(...) 줄을 파싱해 supabase/seed_water_leisure.sql 생성. python tools/gen-seed-sql.py"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_JS = ROOT / "data.js"
OUT_SQL = ROOT / "supabase" / "seed_water_leisure.sql"


def esc_sql(s: str) -> str:
    return s.replace("\\", "\\\\").replace("'", "''")


def extract_mdp_stem(text: str) -> str | None:
    m = re.search(r"const\s+MDP_HISTORY_19G01_STEM\s*=\s*`([\s\S]*?)`;", text)
    if m:
        return m.group(1)
    return None


def parse_q_line(line: str, stem_aliases: dict[str, str]) -> tuple[int, str, str, str, bool, str] | None:
    line = line.strip()
    if not line.startswith("q("):
        return None
    line = line.rstrip()
    if line.endswith("),"):
        s = line[2:-2]  # strip q( and ),
    elif line.endswith(")"):
        s = line[2:-1]
    else:
        return None

    i = 0
    n = len(s)

    def skip_ws():
        nonlocal i
        while i < n and s[i] in " \t":
            i += 1

    def expect_comma():
        nonlocal i
        skip_ws()
        if i < n and s[i] == ",":
            i += 1
        skip_ws()

    def read_int() -> int:
        nonlocal i
        skip_ws()
        j = i
        while j < n and s[j].isdigit():
            j += 1
        v = int(s[i:j])
        i = j
        return v

    def read_ident() -> str:
        nonlocal i
        skip_ws()
        j = i
        while j < n and (s[j].isalnum() or s[j] == "_"):
            j += 1
        ident = s[i:j]
        i = j
        return ident

    def read_string() -> str:
        nonlocal i
        skip_ws()
        if i >= n or s[i] != '"':
            raise ValueError(f"expected string at {i}: {s[i : i + 40]!r}")
        i += 1
        parts: list[str] = []
        while i < n:
            c = s[i]
            if c == "\\":
                i += 1
                if i < n:
                    parts.append(s[i])
                    i += 1
            elif c == '"':
                i += 1
                break
            else:
                parts.append(c)
                i += 1
        return "".join(parts)

    def read_bool() -> bool:
        nonlocal i
        skip_ws()
        if s.startswith("true", i):
            i += 4
            return True
        if s.startswith("false", i):
            i += 5
            return False
        raise ValueError(f"expected bool at {i}: {s[i : i + 20]!r}")

    pack = read_int()
    expect_comma()
    skip_ws()
    if i < n and s[i] == '"':
        stem = read_string()
    else:
        ident = read_ident()
        if ident not in stem_aliases:
            return None
        stem = stem_aliases[ident]
    expect_comma()
    choice = read_string()
    expect_comma()
    statement = read_string()
    expect_comma()
    answer = read_bool()
    expect_comma()
    explanation = read_string()
    skip_ws()
    if i < n:
        raise ValueError(f"trailing junk at {i}: {s[i : i + 40]!r}")
    return (pack, stem, choice, statement, answer, explanation)


def parse_excluded_pack_nos(text: str) -> list[int]:
    m = re.search(r"window\.OX_EXCLUDED_PACK_NOS\s*=\s*\[([^\]]*)\]", text)
    if not m:
        return []
    out: list[int] = []
    for part in m.group(1).split(","):
        p = part.strip()
        if p.isdigit() or (p.startswith("-") and p[1:].isdigit()):
            out.append(int(p))
    return out


def main() -> None:
    text = DATA_JS.read_text(encoding="utf-8")
    stem_aliases: dict[str, str] = {}
    mdp = extract_mdp_stem(text)
    if mdp is not None:
        stem_aliases["MDP_HISTORY_19G01_STEM"] = mdp
    rows: list[tuple[int, str, str, bool, str]] = []
    for raw in text.splitlines():
        parsed = parse_q_line(raw, stem_aliases)
        if not parsed:
            continue
        pack, stem, _choice, statement, answer, explanation = parsed
        rows.append((pack, stem, statement, answer, explanation))

    lines: list[str] = [
        "-- 자동 생성: python tools/gen-seed-sql.py",
        "-- Supabase SQL Editor: 이 파일만 실행해도 됨(quiz_settings 없으면 아래에서 생성).",
        "",
        "alter table public.quiz_questions add column if not exists pack_no int;",
        "alter table public.quiz_questions add column if not exists question text;",
        "alter table public.quiz_questions add column if not exists choice_text text;",
        "alter table public.quiz_units add column if not exists parent_unit_id uuid references public.quiz_units(id) on delete cascade;",
        "",
        "create table if not exists public.quiz_settings (",
        "  key text primary key,",
        "  value jsonb not null,",
        "  updated_at timestamptz not null default now()",
        ");",
        "alter table public.quiz_settings enable row level security;",
        'drop policy if exists "quiz_settings_select_public" on public.quiz_settings;',
        'create policy "quiz_settings_select_public" on public.quiz_settings for select using (true);',
        "",
        "truncate public.quiz_subjects restart identity cascade;",
        "",
        "do $$",
        "declare",
        "  sid uuid;",
        "  uid uuid;",
        "begin",
        "  insert into public.quiz_subjects (name, sort_order) values ('해사법규', 0) returning id into sid;",
        "  insert into public.quiz_units (subject_id, parent_unit_id, name, sort_order) values (sid, null, '수상레저안전법', 0) returning id into uid;",
    ]
    for ord_i, (pack, stem, statement, answer, explanation) in enumerate(rows):
        q_esc = esc_sql(stem)
        c_esc = esc_sql(statement)
        e = esc_sql(explanation)
        a = "true" if answer else "false"
        pk = str(int(pack)) if pack is not None else "null"
        lines.append(
            "  insert into public.quiz_questions "
            "(unit_id, question, choice_text, answer, explanation, sort_order, pack_no) "
            f"values (uid, '{q_esc}', '{c_esc}', {a}, '{e}', {ord_i}, {pk});"
        )
    lines.extend(["end $$;", ""])

    excluded = parse_excluded_pack_nos(text)
    if excluded:
        js = json.dumps(excluded, ensure_ascii=False)
        js_esc = js.replace("'", "''")
        lines.append(
            "insert into public.quiz_settings (key, value) values ('excluded_pack_nos', '"
            + js_esc
            + "'::jsonb) on conflict (key) do update set value = EXCLUDED.value, updated_at = now();"
        )
        lines.append("")

    OUT_SQL.write_text("\n".join(lines), encoding="utf-8")
    print("Wrote", OUT_SQL, "rows=", len(rows))


if __name__ == "__main__":
    try:
        main()
    except Exception as ex:
        print(ex, file=sys.stderr)
        sys.exit(1)

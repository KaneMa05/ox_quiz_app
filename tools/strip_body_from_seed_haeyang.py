# -*- coding: utf-8 -*-
"""seed_haeyang_mdp.sql 에서 quiz_questions.body 컬럼·값 제거."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SQL = ROOT / "supabase" / "seed_haeyang_mdp.sql"
pat = re.compile(r"convert_from\(decode\('([0-9a-fA-F]*)', 'hex'\), 'UTF8'\)")


def patch_line(line: str) -> str:
    if not line.startswith("insert into public.quiz_questions"):
        return line
    line2 = line.replace(
        "(id, unit_id, question, choice_text, body, answer,",
        "(id, unit_id, question, choice_text, answer,",
    )
    matches = list(pat.finditer(line2))
    if len(matches) < 3:
        raise ValueError(f"expected 3 convert_from, got {len(matches)}: {line2[:220]}")
    m = matches[2]
    s, e = m.start(), m.end()
    rest = line2[e:]
    if rest.startswith(", "):
        rest = rest[2:]
    elif rest.startswith(","):
        rest = rest[1:].lstrip()
    return line2[:s] + rest


def main() -> None:
    text = SQL.read_text(encoding="utf-8")
    lines = [patch_line(L) for L in text.splitlines()]
    SQL.write_text("\n".join(lines) + ("\n" if text.endswith("\n") else ""), encoding="utf-8")
    print("patched", SQL)


if __name__ == "__main__":
    main()

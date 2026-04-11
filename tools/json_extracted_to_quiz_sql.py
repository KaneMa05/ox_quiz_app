# -*- coding: utf-8 -*-
"""
maritime_police_extracted_from_images.json 등 → public.quiz_questions INSERT SQL.

Supabase SQL Editor 에 붙여 넣어 실행합니다.
  py -3 tools/json_extracted_to_quiz_sql.py \\
    --json tools/admin/_out/maritime_police_extracted_from_images.json \\
    --unit-id <소단원_uuid> \\
    -o tools/admin/_out/maritime_police_insert.sql

unit_id: Table Editor → quiz_units → 「해양경찰의 역사」같은 말단 단원 행의 id(UUID).
pack_no: 기본 410부터 문항마다 +1 (4선지는 동일 pack_no 공유).
"""
from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path


def _sql_dollar_quote(s: str) -> str:
    tag = f"ox{uuid.uuid4().hex}"
    return f"${tag}${s}${tag}$"


def _json_items_to_sql_rows(
    items: list[dict],
    *,
    unit_id: str,
    pack_base: int,
) -> str:
    lines: list[str] = []
    lines.append(
        f"-- json_extracted_to_quiz_sql.py\n"
        f"-- unit_id = {unit_id}\n"
        f"-- 실행 전: 아래 unit_id 를 본인 DB의 소단원(quiz_units) UUID 로 바꾸세요.\n"
    )
    sort_global = 0
    for qi, item in enumerate(items):
        stem = (item.get("stem") or "").strip()
        choices = list(item.get("choices") or [])
        if len(choices) != 4:
            lines.append(f"-- SKIP {item.get('id')}: choices != 4\n")
            continue
        summary = (item.get("explanation_summary") or "검수 필요").strip() or "검수 필요"
        exps = list(item.get("explanations") or [])
        while len(exps) < 4:
            exps.append(summary)
        pno = pack_base + qi
        for i, ch in enumerate(choices):
            st = (ch.get("text") or "").strip()
            ans = bool(ch.get("correct"))
            ex = (exps[i] if i < len(exps) else summary).strip() or summary
            body = f"문제: {stem}\n\n선지: {st}"
            qid = str(uuid.uuid4())
            lines.append(
                "insert into public.quiz_questions (id, unit_id, question, choice_text, body, answer, explanation, sort_order, pack_no, is_active) values ("
                f"'{qid}'::uuid, '{unit_id}'::uuid, "
                f"{_sql_dollar_quote(stem)}, {_sql_dollar_quote(st)}, {_sql_dollar_quote(body)}, "
                f"{str(ans).lower()}, {_sql_dollar_quote(ex)}, {sort_global}, {pno}, true);"
            )
            sort_global += 1
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description="JSON 추출 문항 → quiz_questions INSERT SQL")
    ap.add_argument(
        "--json",
        type=Path,
        default=Path(__file__).resolve().parent / "admin" / "_out" / "maritime_police_extracted_from_images.json",
        help="입력 JSON (questions 배열)",
    )
    ap.add_argument(
        "--unit-id",
        default="00000000-0000-4000-8000-000000000099",
        help="quiz_questions.unit_id (소단원 UUID로 반드시 교체)",
    )
    ap.add_argument("--pack-base", type=int, default=410, help="첫 문항의 pack_no (이후 +1씩)")
    ap.add_argument("-o", "--out", type=Path, default=None, help="출력 .sql (없으면 stdout)")
    args = ap.parse_args()

    path = args.json
    if not path.is_file():
        print(f"파일 없음: {path}", file=sys.stderr)
        return 1
    doc = json.loads(path.read_text(encoding="utf-8"))
    items = doc.get("questions")
    if not isinstance(items, list):
        print("JSON 에 questions 배열이 없습니다.", file=sys.stderr)
        return 1
    sql = _json_items_to_sql_rows(items, unit_id=args.unit_id.strip(), pack_base=args.pack_base)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(sql, encoding="utf-8")
        print(args.out)
    else:
        sys.stdout.write(sql)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

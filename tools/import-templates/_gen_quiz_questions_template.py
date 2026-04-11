"""quiz_questions.template.csv / .rows.json 생성 — data.js 의 MDP_HISTORY_19G01_STEM 과 동일 지문."""
import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # ox-quiz-app/
text = (ROOT / "data.js").read_text(encoding="utf-8")
m = re.search(r"const MDP_HISTORY_19G01_STEM = `([\s\S]*?)`;", text)
if not m:
    raise SystemExit("MDP_HISTORY_19G01_STEM not found in data.js")
STEM = m.group(1)

rows = [
    ["id", "unit_id", "question", "choice_text", "body", "answer", "explanation", "sort_order", "pack_no", "is_active"],
    [
        "866aebf0-c7f0-5421-a82d-33f7d7a29068",
        "a3418c9f-0641-5cf6-b4fe-39ae5cfb50b0",
        STEM,
        "㉠ 1953, ㉡ 1996",
        f"문제: {STEM}\n\n선지: ㉠ 1953, ㉡ 1996",
        "TRUE",
        "정답 ①. ㉠ 1953년, ㉡ 1996년(무부 치안국 소속 해양경찰대 발족일·해양수산부 발족과 함께 외청 독립일).",
        "0",
        "301",
        "true",
    ],
    [
        "3f472429-b678-5ded-bc4d-3947832f0358",
        "a3418c9f-0641-5cf6-b4fe-39ae5cfb50b0",
        STEM,
        "㉠ 1950, ㉡ 1993",
        f"문제: {STEM}\n\n선지: ㉠ 1950, ㉡ 1993",
        "FALSE",
        "연도 조합이 변천사와 맞지 않는다.",
        "1",
        "301",
        "true",
    ],
    [
        "eca94593-7e0b-5ba4-abbf-ca67b5312363",
        "a3418c9f-0641-5cf6-b4fe-39ae5cfb50b0",
        STEM,
        "㉠ 1951, ㉡ 1992",
        f"문제: {STEM}\n\n선지: ㉠ 1951, ㉡ 1992",
        "FALSE",
        "연도 조합이 변천사와 맞지 않는다.",
        "2",
        "301",
        "true",
    ],
    [
        "885a7654-34b0-5301-8baa-f23384dadcb4",
        "a3418c9f-0641-5cf6-b4fe-39ae5cfb50b0",
        STEM,
        "㉠ 1952, ㉡ 1995",
        f"문제: {STEM}\n\n선지: ㉠ 1952, ㉡ 1995",
        "FALSE",
        "연도 조합이 변천사와 맞지 않는다.",
        "3",
        "301",
        "true",
    ],
]

out = Path(__file__).resolve().parent / "quiz_questions.template.csv"
with out.open("w", newline="", encoding="utf-8-sig") as f:
    csv.writer(f).writerows(rows)
print("wrote", out)

jpath = out.with_suffix(".rows.json")
payload = {"headers": rows[0], "rows": [dict(zip(rows[0], r)) for r in rows[1:]]}
jpath.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
print("wrote", jpath)

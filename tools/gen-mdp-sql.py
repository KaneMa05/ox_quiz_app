# One-off: emit SQL for 해양경찰학개론 (push-curriculum.mjs UUID scheme). UTF-8.
import pathlib
import uuid

NS = uuid.UUID("a1e2c3d4-b5a6-4789-a012-3456789abcde")
stem = """다음은 해양경찰의 변천사를 설명한 것이다. ( ) 안에 들어갈 말을 차례로 나열한 것은?

( ㉠ )년 12월 23일 \uB0B4\uBB34\uBD80 치안국 소속 해양경찰대로 발족되어 영해경비, 어업자원보호 임무를 수행하다가, 1955년 상공부 해무청 소속으로 바뀌어 해양경비 임무 등을 수행하였다.

1962년 5월 1일에는 다시 \uB0B4\uBB34\uBD80 소속으로 복귀하여 해상에서 경찰에 관한 사무와 해난구조와 해양오염에 관한 사무를 관장하기 시작하다가 1991년 8월에는 경찰법 제정에 의하여 경찰청 소속기관으로 편입되었다가, ( ㉡ )년 8월 8일에는 해양수산부 발족과 함께 외청(중앙행정관청)으로 독립하였다."""
opts = [
    ("①", "㉠ 1953, ㉡ 1996", True, "정답 ①. ㉠ 1953년, ㉡ 1996년(\uB0B4\uBB34\uBD80 치안국 소속 해양경찰대 발족일·해양수산부 발족과 함께 외청 독립일)."),
    ("②", "㉠ 1950, ㉡ 1993", False, "연도 조합이 변천사와 맞지 않는다."),
    ("③", "㉠ 1951, ㉡ 1992", False, "연도 조합이 변천사와 맞지 않는다."),
    ("④", "㉠ 1952, ㉡ 1995", False, "연도 조합이 변천사와 맞지 않는다."),
]
uid = str(uuid.uuid5(NS, "unit:sub-mdp-intro/maj-mdpi-1/min-mdpi-1-1"))
qids = [str(uuid.uuid5(NS, f"q:sub-mdp-intro/maj-mdpi-1/min-mdpi-1-1/{i}")) for i in range(4)]


def dq(label: str, s: str) -> str:
    """Postgres dollar-quote; label must not appear in s."""
    tag = f"x{label}"
    return f"${tag}${s}${tag}$"


def main() -> None:
    lines: list[str] = []
    lines.append("delete from public.quiz_subjects where name = '해양경찰학개론';")
    lines.append(
        "insert into public.quiz_subjects (id, name, sort_order, is_active) values "
        "('4767fbe6-ca22-5df3-8aa2-fb8abc795de3'::uuid, '해양경찰학개론', 1, true);"
    )
    lines.append("insert into public.quiz_units (id, subject_id, parent_unit_id, name, sort_order, is_active) values")
    lines.append(
        " ('1288da96-5777-5457-9f4b-889c36adca69'::uuid, '4767fbe6-ca22-5df3-8aa2-fb8abc795de3'::uuid, null, '해양경찰의 개념', 0, true),"
    )
    lines.append(
        f" ('{uid}'::uuid, '4767fbe6-ca22-5df3-8aa2-fb8abc795de3'::uuid, '1288da96-5777-5457-9f4b-889c36adca69'::uuid, '해양경찰의 역사', 0, true),"
    )
    lines.append(
        " ('bcb924b4-00dc-5910-96ce-c6fa808ea6d4'::uuid, '4767fbe6-ca22-5df3-8aa2-fb8abc795de3'::uuid, null, '해양경찰의 법적 토대', 1, true),"
    )
    lines.append(
        " ('f1c07010-c543-5e06-bc84-baab4ca1bc44'::uuid, '4767fbe6-ca22-5df3-8aa2-fb8abc795de3'::uuid, 'bcb924b4-00dc-5910-96ce-c6fa808ea6d4'::uuid, '해양경찰 공무원', 0, true),"
    )
    lines.append(
        " ('c2ab0d5f-6c16-5b44-84ea-84008e16d67d'::uuid, '4767fbe6-ca22-5df3-8aa2-fb8abc795de3'::uuid, 'bcb924b4-00dc-5910-96ce-c6fa808ea6d4'::uuid, '해양경찰의 작용', 1, true);"
    )
    for i, (_c, st, a, ex) in enumerate(opts):
        lines.append(
            "insert into public.quiz_questions (id, unit_id, question, choice_text, answer, explanation, sort_order, pack_no, is_active) values ("
            f"'{qids[i]}'::uuid, '{uid}'::uuid, {dq('q', stem)}, {dq('c', st)}, {str(a).lower()}, {dq('e', ex)}, {i}, 301, true);"
        )
    out = pathlib.Path(__file__).resolve().parent / "_tmp_mdp_sync.sql"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(out, len("\n".join(lines)))


if __name__ == "__main__":
    main()

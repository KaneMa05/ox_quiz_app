"""Emit ASCII-only SQL using decode(..., 'hex') for UTF-8 text (MCP-safe)."""
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


def hutf(s: str) -> str:
    return s.encode("utf-8").hex()


def main() -> None:
    subj = "해양경찰학개론"
    hsub = hutf(subj)
    lines: list[str] = []
    lines.append(
        f"delete from public.quiz_subjects where name = convert_from(decode('{hsub}', 'hex'), 'UTF8');"
    )
    lines.append(
        "insert into public.quiz_subjects (id, name, sort_order, is_active) values ("
        f"'4767fbe6-ca22-5df3-8aa2-fb8abc795de3'::uuid, "
        f"convert_from(decode('{hsub}', 'hex'), 'UTF8'), "
        "1, true);"
    )
    n1 = hutf("해양경찰의 개념")
    n2 = hutf("해양경찰의 역사")
    n3 = hutf("해양경찰의 법적 토대")
    n4 = hutf("해양경찰 공무원")
    n5 = hutf("해양경찰의 작용")
    lines.append("insert into public.quiz_units (id, subject_id, parent_unit_id, name, sort_order, is_active) values")
    lines.append(
        f" ('1288da96-5777-5457-9f4b-889c36adca69'::uuid, '4767fbe6-ca22-5df3-8aa2-fb8abc795de3'::uuid, null, convert_from(decode('{n1}', 'hex'), 'UTF8'), 0, true),"
    )
    lines.append(
        f" ('{uid}'::uuid, '4767fbe6-ca22-5df3-8aa2-fb8abc795de3'::uuid, '1288da96-5777-5457-9f4b-889c36adca69'::uuid, convert_from(decode('{n2}', 'hex'), 'UTF8'), 0, true),"
    )
    lines.append(
        f" ('bcb924b4-00dc-5910-96ce-c6fa808ea6d4'::uuid, '4767fbe6-ca22-5df3-8aa2-fb8abc795de3'::uuid, null, convert_from(decode('{n3}', 'hex'), 'UTF8'), 1, true),"
    )
    lines.append(
        f" ('f1c07010-c543-5e06-bc84-baab4ca1bc44'::uuid, '4767fbe6-ca22-5df3-8aa2-fb8abc795de3'::uuid, 'bcb924b4-00dc-5910-96ce-c6fa808ea6d4'::uuid, convert_from(decode('{n4}', 'hex'), 'UTF8'), 0, true),"
    )
    lines.append(
        f" ('c2ab0d5f-6c16-5b44-84ea-84008e16d67d'::uuid, '4767fbe6-ca22-5df3-8aa2-fb8abc795de3'::uuid, 'bcb924b4-00dc-5910-96ce-c6fa808ea6d4'::uuid, convert_from(decode('{n5}', 'hex'), 'UTF8'), 1, true);"
    )
    hs = hutf(stem)
    for i, (_c, st, a, ex) in enumerate(opts):
        body = "문제: " + stem + "\n\n선지: " + st
        lines.append(
            "insert into public.quiz_questions (id, unit_id, question, choice_text, body, answer, explanation, sort_order, pack_no, is_active) values ("
            f"'{qids[i]}'::uuid, '{uid}'::uuid, "
            f"convert_from(decode('{hs}', 'hex'), 'UTF8'), "
            f"convert_from(decode('{hutf(st)}', 'hex'), 'UTF8'), "
            f"convert_from(decode('{hutf(body)}', 'hex'), 'UTF8'), "
            f"{str(a).lower()}, "
            f"convert_from(decode('{hutf(ex)}', 'hex'), 'UTF8'), "
            f"{i}, 301, true);"
        )
    out = pathlib.Path(__file__).resolve().parent / "seed_mdp_hex.sql"
    out.write_text("\n".join(lines), encoding="ascii")
    print(out, "lines", len(lines))


if __name__ == "__main__":
    main()

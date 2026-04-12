# -*- coding: utf-8 -*-
"""
문제 이미지/PDF → 구조화 JSON·(선택) SQL·data.js 스니펫.

무료: Tesseract OCR + ①~④ 파서(GUI 기본 / CLI --ocr). 유료: Vision(OpenAI 키, GUI에서 선택).
"""
from __future__ import annotations

import base64
import io
import json
import os
import re
import sys
import uuid
from pathlib import Path
from typing import Any

_ADMIN = Path(__file__).resolve().parent
_APP_ROOT = _ADMIN.parent.parent


def _load_openai_key_from_env_local() -> None:
    for name in (".env.local", ".env", "api.env.local"):
        p = _APP_ROOT / name
        if not p.is_file():
            continue
        try:
            for raw in p.read_text(encoding="utf-8").splitlines():
                line = raw.strip()
                if line.startswith("#") or "=" not in line:
                    continue
                k, _, v = line.partition("=")
                k, v = k.strip(), v.strip().strip('"').strip("'")
                if k == "OPENAI_API_KEY" and v and not os.environ.get("OPENAI_API_KEY"):
                    os.environ["OPENAI_API_KEY"] = v
        except OSError:
            pass


def get_tesseract_executable() -> str | None:
    env = (os.environ.get("TESSERACT_CMD") or "").strip().strip('"')
    if env and Path(env).is_file():
        return env
    hint = _ADMIN / "_tesseract_path.txt"
    if hint.is_file():
        p = hint.read_text(encoding="utf-8").splitlines()[0].strip().strip('"')
        if p and Path(p).is_file():
            return p
    for cand in (
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    ):
        if Path(cand).is_file():
            return cand
    return None


def _image_to_jpeg_bytes(path: Path, max_side: int = 2048) -> tuple[bytes, str]:
    from PIL import Image

    im = Image.open(path).convert("RGB")
    w, h = im.size
    if max(w, h) > max_side:
        if w >= h:
            nw, nh = max_side, int(h * max_side / w)
        else:
            nh, nw = max_side, int(w * max_side / h)
        im = im.resize((nw, nh), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, format="JPEG", quality=88)
    return buf.getvalue(), "image/jpeg"


def _pdf_first_page_jpeg(path: Path, dpi: int = 200) -> tuple[bytes, str]:
    import fitz  # pymupdf

    doc = fitz.open(path)
    if doc.page_count < 1:
        doc.close()
        raise ValueError("PDF 에 페이지가 없습니다.")
    page = doc.load_page(0)
    mat = fitz.Matrix(dpi / 72, dpi / 72)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    doc.close()
    try:
        im_bytes = pix.tobytes("jpg")
    except TypeError:
        im_bytes = pix.tobytes("jpeg")
    return im_bytes, "image/jpeg"


def _media_bytes(path: Path) -> tuple[bytes, str]:
    suf = path.suffix.lower()
    if suf == ".pdf":
        try:
            return _pdf_first_page_jpeg(path)
        except ImportError as e:
            raise RuntimeError("PDF 는 pymupdf 가 필요합니다: py -3 -m pip install pymupdf") from e
    return _image_to_jpeg_bytes(path)


def _pdf_pages_jpegs(path: Path, dpi: int = 200) -> list[bytes]:
    import fitz  # pymupdf

    doc = fitz.open(path)
    out: list[bytes] = []
    try:
        scale = dpi / 72
        mat = fitz.Matrix(scale, scale)
        for i in range(doc.page_count):
            page = doc.load_page(i)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            try:
                out.append(pix.tobytes("jpg"))
            except TypeError:
                out.append(pix.tobytes("jpeg"))
    finally:
        doc.close()
    return out


def _jpeg_pages_for_path(path: Path) -> list[bytes]:
    suf = path.suffix.lower()
    if suf == ".pdf":
        try:
            return _pdf_pages_jpegs(path)
        except ImportError as e:
            raise RuntimeError("PDF OCR 에는 pymupdf 필요: pip install pymupdf") from e
    return [_image_to_jpeg_bytes(path)[0]]


def _normalize_quiz_plaintext(s: str) -> str:
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    s = s.replace("：", ":").replace("０", "0")
    for a, b in zip("１２３４", "1234", strict=True):
        s = s.replace(a, b)
    return s


def _safe_debug_stem(name: str, max_len: int = 50) -> str:
    s = re.sub(r"[^\w\-가-힣.]+", "_", name).strip("._")
    return (s[:max_len] if s else "image")


def _ocr_heuristic_normalize(s: str) -> str:
    """OCR 결과를 ①~④ + 정답 파서가 잡기 쉽게 정리합니다."""
    s = _normalize_quiz_plaintext(s).lstrip("\ufeff")
    for a, b in (
        ("\u2460", "①"),
        ("\u2461", "②"),
        ("\u2462", "③"),
        ("\u2463", "④"),
        ("\u2776", "①"),
        ("\u2777", "②"),
        ("\u2778", "③"),
        ("\u2779", "④"),
    ):
        s = s.replace(a, b)
    circ = ["①", "②", "③", "④"]
    lines = s.split("\n")
    out_ln: list[str] = []
    for line in lines:
        m = re.match(r"^(\s*)([1-4])[.)．、]\s*(.*)$", line)
        if m:
            idx = int(m.group(2)) - 1
            line = f"{m.group(1)}{circ[idx]} {m.group(3)}"
        else:
            m2 = re.match(r"^(\s*)[\(（]\s*([1-4])\s*[\)）]\s*(.*)$", line)
            if m2:
                idx = int(m2.group(2)) - 1
                line = f"{m2.group(1)}{circ[idx]} {m2.group(3)}"
        out_ln.append(line)
    s = "\n".join(out_ln)
    s = re.sub(r"(?m)(정답|답)\s*[:：]?\s*([1-4])(?=\s*$)", lambda m: f"{m.group(1)}: {circ[int(m.group(2)) - 1]}", s)
    for mark in ("②", "③", "④"):
        s = re.sub(rf"([^\n]){mark}", rf"\1\n{mark}", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


_QBLOCK = re.compile(
    r"(?P<stem>[\s\S]+?)"
    r"①\s*(?P<c1>[\s\S]+?)\s*"
    r"②\s*(?P<c2>[\s\S]+?)\s*"
    r"③\s*(?P<c3>[\s\S]+?)\s*"
    r"④\s*(?P<c4>[\s\S]+?)\s*"
    r"(?:정답|답)\s*[:：]?\s*(?P<ans>[①②③④1234])",
    re.MULTILINE,
)


def _answer_marker_to_index(ans: str) -> int:
    ans = ans.strip()
    m = {"①": 0, "②": 1, "③": 2, "④": 3, "1": 0, "2": 1, "3": 2, "4": 3}
    if ans not in m:
        raise ValueError(ans)
    return m[ans]


def parse_plaintext_to_questions(text: str, default_explanation: str) -> tuple[list[dict[str, Any]], list[str]]:
    """①~④ + 정답: 형식 텍스트를 questions JSON 구조로 변환 (OCR/메모장용)."""
    notes: list[str] = []
    text = _ocr_heuristic_normalize(text)
    out: list[dict[str, Any]] = []
    pos = 0
    while pos < len(text):
        m = _QBLOCK.search(text, pos)
        if not m:
            tail = text[pos:].strip()
            if tail and not out:
                notes.append(
                    "①~④(또는 줄 시작 1.~4.) + 마지막 '정답:' 줄이 필요합니다. "
                    "실패 시 _out 폴더에 저장된 *_ocr_raw.txt 를 메모장으로 고친 뒤「텍스트만」모드로 다시 실행하세요."
                )
            elif tail:
                notes.append("일부 끝 텍스트는 문항 패턴에 맞지 않아 건너뜀(검수).")
            break
        stem = (m.group("stem") or "").strip()
        c1, c2, c3, c4 = (m.group("c1") or "").strip(), (m.group("c2") or "").strip(), (m.group("c3") or "").strip(), (
            m.group("c4") or ""
        ).strip()
        if any(not x.strip() for x in (c1, c2, c3, c4)):
            notes.append("선지가 비어 있는 블록을 건너뜀.")
            pos = m.end()
            continue
        try:
            ai = _answer_marker_to_index(m.group("ans") or "")
        except ValueError:
            notes.append(f"정답 표기를 해석하지 못함: {m.group('ans')!r}")
            pos = m.end()
            continue
        markers = ["①", "②", "③", "④"]
        texts = [c1, c2, c3, c4]
        choices: list[dict[str, Any]] = []
        for i, t in enumerate(texts):
            flat = re.sub(r"\s+", " ", t.replace("\n", " ")).strip()
            choices.append({"marker": markers[i], "text": flat, "correct": i == ai})
        ex = (default_explanation or "검수 필요").strip() or "검수 필요"
        out.append(
            {
                "page_column": "left",
                "stem": stem,
                "choices": choices,
                "explanations": [ex, ex, ex, ex],
                "explanation_continuation": False,
                "explanation_note": "",
            }
        )
        pos = m.end()
    return out, notes


def _tesseract_ocr_jpeg(
    jpeg_bytes: bytes, *, lang: str, tess_exe: str | None, tess_config: str = "--oem 1 --psm 6"
) -> str:
    import pytesseract
    from PIL import Image

    prev_cmd = getattr(pytesseract.pytesseract, "tesseract_cmd", "") or ""
    try:
        if tess_exe:
            pytesseract.pytesseract.tesseract_cmd = tess_exe
        im = Image.open(io.BytesIO(jpeg_bytes)).convert("RGB")
        return pytesseract.image_to_string(im, lang=lang or "kor+eng", config=tess_config)
    finally:
        pytesseract.pytesseract.tesseract_cmd = prev_cmd


def _ocr_jpeg_try_layouts(
    jpeg_bytes: bytes,
    *,
    lang: str,
    tess_exe: str | None,
    explanation: str,
    debug_txt: Path | None,
) -> tuple[list[dict[str, Any]], list[str]]:
    """여러 PSM으로 OCR 후 파싱; 실패 시 debug_txt 에 원문 저장."""
    configs = (
        "--oem 1 --psm 6",
        "--oem 1 --psm 3",
        "--oem 1 --psm 4",
        "--oem 1 --psm 11",
        "--oem 1 --psm 1",
    )
    best: list[dict[str, Any]] = []
    best_raw = ""
    last_raw = ""
    notes: list[str] = []
    for cfg in configs:
        try:
            last_raw = _tesseract_ocr_jpeg(jpeg_bytes, lang=lang, tess_exe=tess_exe, tess_config=cfg)
        except Exception as e:
            notes.append(f"Tesseract({cfg}) 오류: {e}")
            continue
        qs, _ = parse_plaintext_to_questions(last_raw, explanation)
        if len(qs) > len(best):
            best = qs
            best_raw = last_raw
    if not best and debug_txt is not None:
        try:
            debug_txt.parent.mkdir(parents=True, exist_ok=True)
            debug_txt.write_text(last_raw or best_raw or "", encoding="utf-8")
            notes.append(
                f"문항 0개 — OCR 원문 저장: {debug_txt}\n"
                "메모장에서 ①~④ 또는 1.~4. + '정답: ③' 형으로 고친 뒤, 같은 파일로「텍스트만」실행하면 됩니다."
            )
        except OSError as e:
            notes.append(f"OCR 원문 저장 실패: {e}")
    return best, notes


SYSTEM_PROMPT = """당신은 한국어 시험·교재 페이지에서 객관식 문항만 추출하는 전문가입니다.

규칙(매우 중요):
1) 지문(stem)은 원본 글자·띄어쓰기·줄바꿈을 최대한 그대로 옮깁니다. 요약·말줄임·바꿔쓰기 금지.
2) 고유명사·부처명·연도·법령명은 원문 표기를 그대로 유지합니다(예:무부).
3) 선지는 ①②③④ 네 개를 전제로 하며, 각 choice_text 는 원문에서 원 번호 기호(① 등) 뒤의 본문만 넣습니다.
4) 정답이 하나일 때 correct 가 true 인 항목은 정확히 하나여야 합니다.
5) explanations 는 네 개 모두 문자열. 모르면 해당 칸에 "검수 필요" 라고 적습니다.
6) JSON 이외의 텍스트는 출력하지 마세요.

페이지가 좌·우 두 단으로 나뉜 경우(기출·교재 흔한 형태):
- 한 단 안에서는 위→아래 순서로 문항을 읽습니다.
- 좌단과 우단은 서로 다른 문제 영역입니다. 좌단 지문과 우단 선지를 한 문항으로 합치지 마세요.
- 질문 출력 순서: 먼저 좌단 전체를 위에서 아래로, 그 다음 우단 전체를 위에서 아래로 넣습니다(페이지에 인쇄된 읽기 순서가 명백히 다르면 그 순서를 따르되, 좌우를 섞지 마세요).
- 각 문항에 page_column 값으로 "left" 또는 "right" 를 넣습니다(한 단만 있으면 "left").

해설이 다음 장·다음 면으로 이어지는 경우:
- 지금 보이는 이미지에 해설 일부만 있으면, 보이는 범위만 explanations 에 넣고 explanation_continuation 을 true 로 하며 explanation_note 에 "해설이 다음 페이지에 이어짐" 등 짧게 적습니다. 없는 페이지 내용은 추측하지 마세요.
- 사용자가 연속된 두 이미지(앞장+뒷장)를 함께 줄 때는, 같은 문항의 해설이 두 장에 걸쳐 있으면 questions 항목은 하나로 두고 explanations 를 두 장에서 읽은 내용으로 완성합니다(뒷장에 없는 추측 금지).
"""


def _schema_hint_single() -> str:
    return """응답 JSON 형식:
{
  "questions": [
    {
      "page_column": "left",
      "stem": "지문 전체(질문+박스 본문 등)",
      "choices": [
        {"marker":"①","text":"...","correct":true},
        {"marker":"②","text":"...","correct":false},
        {"marker":"③","text":"...","correct":false},
        {"marker":"④","text":"...","correct":false}
      ],
      "explanations": ["해설①","해설②","해설③","해설④"],
      "explanation_continuation": false,
      "explanation_note": ""
    }
  ]
}
- page_column: "left" | "right"
- explanation_continuation: 해설이 이 이미지 밖으로 이어지면 true, 아니면 false
- explanation_note: 이어짐·좌우 구분 등 검수용 메모(없으면 "")
한 페이지에 문항이 여러 개면 questions 배열에 위 규칙 순서대로 넣습니다. 없으면 questions 는 빈 배열."""


def _schema_hint_spread() -> str:
    return """응답 JSON 형식은 단일 페이지와 동일합니다.
{
  "questions": [ ... ]
}
- 이미지 1 = 앞쪽 페이지, 이미지 2 = 바로 이어지는 뒤쪽 페이지입니다.
- 각 장마다 좌단→우단 순으로 문항을 나열한 뒤, 앞 장 questions 를 먼저 모두 넣고 뒷 장 questions 를 이어서 넣습니다.
- 한 문항의 해설이 1번 이미지 하단에서 끊기고 2번 이미지에 이어지면: 해당 문항은 하나만 두고 explanations 를 두 이미지에서 읽은 텍스트로 합칩니다(추측 금지).
- 뒷 장에만 시작하는 새 문항은 별도 항목으로 추가합니다."""


def _vision_extract(image_b64: str, mime: str) -> dict[str, Any]:
    _load_openai_key_from_env_local()
    key = (os.environ.get("OPENAI_API_KEY") or "").strip()
    if not key:
        raise RuntimeError(
            "OPENAI_API_KEY 없음 → ox-quiz-app/.env.local 에 OPENAI_API_KEY=sk-... 한 줄 (.env.local.example 참고)"
        )
    try:
        from openai import OpenAI
    except ImportError as e:
        raise RuntimeError("pip install openai  (tools/admin/requirements-vision.txt)") from e

    model = (os.environ.get("OPENAI_VISION_MODEL") or "gpt-4o").strip()
    client = OpenAI(api_key=key)
    user_text = (
        "이 페이지(좌·우 단 구분)에서 객관식(4지선다) 문항을 모두 추출하세요.\n"
        "좌단과 우단을 절대 섞지 말고, page_column 과 questions 순서 규칙을 지키세요.\n\n"
        + _schema_hint_single()
    )

    msg = client.chat.completions.create(
        model=model,
        temperature=0.1,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": user_text},
                    {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{image_b64}"}},
                ],
            },
        ],
    )
    raw = (msg.choices[0].message.content or "").strip()
    return json.loads(raw)


def _vision_extract_spread(image_b64_a: str, mime_a: str, image_b64_b: str, mime_b: str) -> dict[str, Any]:
    _load_openai_key_from_env_local()
    key = (os.environ.get("OPENAI_API_KEY") or "").strip()
    if not key:
        raise RuntimeError("OPENAI_API_KEY 가 없습니다.")
    try:
        from openai import OpenAI
    except ImportError as e:
        raise RuntimeError("pip install openai") from e

    model = (os.environ.get("OPENAI_VISION_MODEL") or "gpt-4o").strip()
    client = OpenAI(api_key=key)
    user_text = (
        "아래 이미지 두 장은 교재의 연속된 두 페이지(또는 펼친면의 앞·뒤)입니다.\n"
        "각 장에서 좌단→우단 순으로 문항을 구분하고, 해설이 앞 장에서 끊기고 뒷 장에 이어지면 같은 문항으로 합쳐 explanations 를 완성하세요.\n\n"
        + _schema_hint_spread()
    )

    msg = client.chat.completions.create(
        model=model,
        temperature=0.1,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": user_text + "\n[이미지 1]"},
                    {"type": "image_url", "image_url": {"url": f"data:{mime_a};base64,{image_b64_a}"}},
                    {"type": "text", "text": "[이미지 2]"},
                    {"type": "image_url", "image_url": {"url": f"data:{mime_b};base64,{image_b64_b}"}},
                ],
            },
        ],
    )
    raw = (msg.choices[0].message.content or "").strip()
    return json.loads(raw)


def _sql_dollar_quote(s: str) -> str:
    tag = f"ox{uuid.uuid4().hex}"
    return f"${tag}${s}${tag}$"


def _choice_explanation(q: dict[str, Any], choice_index: int) -> str:
    exps = list(q.get("explanations") or [])
    while len(exps) < 4:
        exps.append("검수 필요")
    ex = exps[choice_index] if choice_index < len(exps) else "검수 필요"
    note = (q.get("explanation_note") or "").strip()
    cont = q.get("explanation_continuation")
    if note:
        ex = f"{ex}\n\n[참고] {note}"
    elif cont is True:
        ex = f"{ex}\n\n[참고] 해설이 다음 페이지에 이어질 수 있음. 검수하세요."
    return ex


def _build_sql(unit_id: str, pack_no: int, questions: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    sort_base = 0
    for qi, q in enumerate(questions):
        stem = (q.get("stem") or "").strip()
        choices: list[dict] = q.get("choices") or []
        pno = pack_no + qi * 1000 if pack_no else qi + 1
        for i, ch in enumerate(choices):
            st = (ch.get("text") or "").strip()
            ans = bool(ch.get("correct"))
            ex = _choice_explanation(q, i)
            qid = str(uuid.uuid4())
            so = sort_base + i
            lines.append(
                "insert into public.quiz_questions (id, unit_id, question, choice_text, answer, explanation, sort_order, pack_no, is_active) values ("
                f"'{qid}'::uuid, '{unit_id}'::uuid, "
                f"{_sql_dollar_quote(stem)}, {_sql_dollar_quote(st)}, "
                f"{str(ans).lower()}, {_sql_dollar_quote(ex)}, {so}, {pno}, true);"
            )
        sort_base += len(choices)
    return "\n".join(lines) + ("\n" if lines else "")


def _build_data_js_snippet(pack_no: int, questions: list[dict[str, Any]]) -> str:
    lines_out: list[str] = []
    for qi, q in enumerate(questions):
        stem = (q.get("stem") or "").strip()
        stem_js = json.dumps(stem, ensure_ascii=False)
        choices: list[dict] = q.get("choices") or []
        pno = pack_no + qi * 1000 if pack_no else qi + 1
        for i, ch in enumerate(choices):
            mk = (ch.get("marker") or ["①", "②", "③", "④"][min(i, 3)]).strip()
            st = json.dumps((ch.get("text") or "").strip(), ensure_ascii=False)
            ex = json.dumps(_choice_explanation(q, i), ensure_ascii=False)
            ans = "true" if ch.get("correct") else "false"
            lines_out.append(f"          q({pno}, {stem_js}, {json.dumps(mk, ensure_ascii=False)}, {st}, {ans}, {ex}),")
    return "\n".join(lines_out) + ("\n" if lines_out else "")


def _write_batch_result(
    *,
    all_questions: list[dict[str, Any]],
    per_file: list[dict[str, Any]],
    source: str,
    out: Path,
    pack_no: int,
    unit_id: str,
    emit_sql: bool,
    emit_data_js: bool,
    messages: list[str],
) -> dict[str, Any]:
    for q in all_questions:
        if isinstance(q, dict):
            chs = q.get("choices") or []
            n_ok = sum(1 for c in chs if isinstance(c, dict) and c.get("correct"))
            if len(chs) and n_ok != 1:
                messages.append("경고: 일부 문항의 정답(correct:true) 개수가 1이 아닙니다. JSON 은 검수하세요.")
    payload: dict[str, Any] = {
        "meta": {"pack_no": pack_no, "unit_id": unit_id, "source": source, "per_file": per_file},
        "questions": all_questions,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    messages.append(f"JSON 저장: {out}")
    return {
        "ok": True,
        "out_path": str(out),
        "messages": messages,
        "sql_text": _build_sql(unit_id, pack_no, all_questions) if emit_sql else "",
        "data_js_text": _build_data_js_snippet(pack_no, all_questions) if emit_data_js else "",
    }


def run_batch(
    *,
    images: list[Path],
    text_file: Path | None,
    out: Path,
    pack_no: int,
    lang: str,
    explanation: str,
    emit_sql: bool,
    unit_id: str,
    emit_data_js: bool,
    tesseract_cmd: str | None,
    spread_pair: bool = False,
    use_vision: bool = True,
) -> dict[str, Any]:
    messages: list[str] = []

    if not use_vision:
        if text_file and not images:
            try:
                raw = Path(text_file).read_text(encoding="utf-8")
            except OSError as e:
                return {"ok": False, "messages": [f"텍스트 읽기 실패: {e}"]}
            qs, notes = parse_plaintext_to_questions(raw, explanation)
            messages.extend(notes)
            if not qs:
                return {
                    "ok": False,
                    "messages": messages
                    + ["문항을 찾지 못했습니다. tools/admin/sample_ocr_plain.txt 형식(①~④ + 정답:)을 맞추세요."],
                }
            return _write_batch_result(
                all_questions=qs,
                per_file=[{"file": str(text_file), "count": len(qs)}],
                source="ocr_plaintext",
                out=out,
                pack_no=pack_no,
                unit_id=unit_id,
                emit_sql=emit_sql,
                emit_data_js=emit_data_js,
                messages=messages + [f"텍스트만: 문항 {len(qs)}개"],
            )

        if not images:
            return {"ok": False, "messages": ["이미지/PDF 경로가 없습니다. (텍스트만 쓰려면 텍스트 모드로 실행하세요.)"]}

        tess = (tesseract_cmd or "").strip() or (get_tesseract_executable() or "")
        if not tess or not Path(tess).is_file():
            return {
                "ok": False,
                "messages": [
                    "Tesseract(tesseract.exe)가 필요합니다. "
                    "https://github.com/UB-Mannheim/tesseract/wiki 설치 후「자동 찾기」또는 경로 입력."
                ],
            }

        all_questions: list[dict[str, Any]] = []
        per_file: list[dict[str, Any]] = []

        if spread_pair:
            if len(images) != 2:
                return {
                    "ok": False,
                    "messages": ["「연속 2장」은 파일을 정확히 2개(앞→뒤 순)만 선택하세요."],
                }
            for p in images:
                p = Path(p)
                if not p.is_file():
                    return {"ok": False, "messages": [f"파일 없음: {p}"]}
                n0 = len(all_questions)
                try:
                    jpgs = _jpeg_pages_for_path(p)
                except Exception as e:
                    return {"ok": False, "messages": [f"{p.name}: {e}"]}
                for jpi, jpg in enumerate(jpgs):
                    dbg = out.parent / f"{out.stem}_{_safe_debug_stem(p.stem)}_p{jpi}_ocr_raw.txt"
                    qs, notes = _ocr_jpeg_try_layouts(
                        jpg, lang=lang, tess_exe=tess, explanation=explanation, debug_txt=dbg
                    )
                    messages.extend(notes)
                    all_questions.extend(qs)
                per_file.append({"file": str(p), "count": len(all_questions) - n0})
            messages.append(
                f"OCR 연속 2파일: 문항 {len(all_questions)}개 (페이지별 파싱, Vision처럼 해설 병합은 하지 않습니다 — 검수)"
            )
            return _write_batch_result(
                all_questions=all_questions,
                per_file=per_file,
                source="tesseract_ocr_spread",
                out=out,
                pack_no=pack_no,
                unit_id=unit_id,
                emit_sql=emit_sql,
                emit_data_js=emit_data_js,
                messages=messages,
            )

        for p in images:
            p = Path(p)
            if not p.is_file():
                messages.append(f"건너뜀(없음): {p}")
                continue
            n0 = len(all_questions)
            try:
                jpgs = _jpeg_pages_for_path(p)
            except Exception as e:
                messages.append(f"{p.name}: 로드 실패 — {e}")
                continue
            for jpi, jpg in enumerate(jpgs):
                dbg = out.parent / f"{out.stem}_{_safe_debug_stem(p.stem)}_p{jpi}_ocr_raw.txt"
                qs, notes = _ocr_jpeg_try_layouts(
                    jpg, lang=lang, tess_exe=tess, explanation=explanation, debug_txt=dbg
                )
                messages.extend(notes)
                all_questions.extend(qs)
            n_added = len(all_questions) - n0
            per_file.append({"file": str(p), "count": n_added})
            messages.append(f"{p.name}: OCR 문항 {n_added}개")

        if not all_questions:
            return {
                "ok": False,
                "messages": messages
                + [
                    "①~④ 또는 1.~4. + '정답:' 줄이 OCR 텍스트에 없습니다. "
                    "tools/admin/_out 의 *_ocr_raw.txt 를 열어 형식을 맞춘 뒤「텍스트만」으로 재실행하세요. "
                    "Tesseract 설치 시 kor.traineddata 포함 여부도 확인하세요."
                ],
            }
        return _write_batch_result(
            all_questions=all_questions,
            per_file=per_file,
            source="tesseract_ocr",
            out=out,
            pack_no=pack_no,
            unit_id=unit_id,
            emit_sql=emit_sql,
            emit_data_js=emit_data_js,
            messages=messages,
        )

    if text_file and not images:
        return {
            "ok": False,
            "messages": ["Vision 모드는 이미지/PDF가 필요합니다. 과금 없이 하려면「텍스트만」또는 --ocr 로 이미지를 처리하세요."],
        }
    if not images:
        return {"ok": False, "messages": ["이미지/PDF 경로가 없습니다."]}

    all_questions_v: list[dict[str, Any]] = []
    per_file_v: list[dict[str, Any]] = []

    if spread_pair:
        if len(images) != 2:
            return {
                "ok": False,
                "messages": ["「연속 2장」모드는 이미지를 정확히 2장(앞장→뒷장 순)만 선택하세요."],
            }
        pa, pb = Path(images[0]), Path(images[1])
        for p in (pa, pb):
            if not p.is_file():
                return {"ok": False, "messages": [f"파일 없음: {p}"]}
        try:
            raw_a, mime_a = _media_bytes(pa)
            raw_b, mime_b = _media_bytes(pb)
        except Exception as e:
            return {"ok": False, "messages": [f"미디어 로드 실패 — {e}"]}
        b64a = base64.standard_b64encode(raw_a).decode("ascii")
        b64b = base64.standard_b64encode(raw_b).decode("ascii")
        try:
            data = _vision_extract_spread(b64a, mime_a, b64b, mime_b)
        except Exception as e:
            return {"ok": False, "messages": [f"Vision API 실패 — {e}"]}
        qs = data.get("questions")
        if not isinstance(qs, list):
            return {"ok": False, "messages": ["JSON 에 questions 배열이 없습니다."]}
        for q in qs:
            if isinstance(q, dict):
                chs = q.get("choices") or []
                n_ok = sum(1 for c in chs if isinstance(c, dict) and c.get("correct"))
                if len(chs) and n_ok != 1:
                    messages.append("경고 — 어떤 문항의 정답 개수가 1이 아닙니다. 검수하세요.")
                all_questions_v.append(q)
        per_file_v.append({"files": [str(pa), str(pb)], "mode": "spread_pair", "count": len(qs)})
        messages.append(f"연속 2장 Vision: 문항 {len(qs)}개 (좌우 단·해설 이어짐 규칙 적용)")
        return _write_batch_result(
            all_questions=all_questions_v,
            per_file=per_file_v,
            source="openai_vision_spread",
            out=out,
            pack_no=pack_no,
            unit_id=unit_id,
            emit_sql=emit_sql,
            emit_data_js=emit_data_js,
            messages=messages,
        )

    for p in images:
        p = Path(p)
        if not p.is_file():
            messages.append(f"건너뜀(없음): {p}")
            continue
        try:
            raw, mime = _media_bytes(p)
        except Exception as e:
            messages.append(f"{p.name}: 미디어 로드 실패 — {e}")
            continue
        b64 = base64.standard_b64encode(raw).decode("ascii")
        try:
            data = _vision_extract(b64, mime)
        except Exception as e:
            messages.append(f"{p.name}: Vision API 실패 — {e}")
            return {"ok": False, "messages": messages + [str(e)]}

        qs = data.get("questions")
        if not isinstance(qs, list):
            messages.append(f"{p.name}: JSON 에 questions 배열이 없습니다.")
            return {"ok": False, "messages": messages}

        for q in qs:
            if isinstance(q, dict):
                chs = q.get("choices") or []
                n_ok = sum(1 for c in chs if isinstance(c, dict) and c.get("correct"))
                if len(chs) and n_ok != 1:
                    messages.append(
                        f"{p.name}: 경고 — 정답(correct:true) 개수가 {n_ok}개입니다. JSON 은 저장했으니 반드시 검수하세요."
                    )
                all_questions_v.append(q)
        per_file_v.append({"file": str(p), "count": len(qs)})
        messages.append(f"{p.name}: 문항 {len(qs)}개 추출")

    return _write_batch_result(
        all_questions=all_questions_v,
        per_file=per_file_v,
        source="openai_vision",
        out=out,
        pack_no=pack_no,
        unit_id=unit_id,
        emit_sql=emit_sql,
        emit_data_js=emit_data_js,
        messages=messages,
    )


def _print_cli_help() -> None:
    print(
        "문제 추출 — 사용법 (인자 없이 실행하면 이 안내만)\n\n"
        "  무료 OCR: py -3 tools/admin/image_to_quiz_questions.py --ocr [--pack-no N] [--sql] [--data-js] [--spread] <이미지|PDF…>\n"
        "  Vision:  py -3 tools/admin/image_to_quiz_questions.py [--pack-no N] [--sql] [--data-js] [--spread] <이미지…>\n"
        "           (OPENAI_API_KEY — .env.local / api.env.local / 환경 변수)\n\n"
        "  --spread : 파일 정확히 2개(앞→뒤). Vision은 해설 병합, OCR은 페이지별 파싱만.\n\n"
        "GUI: tools/admin/LAUNCH_GUI.bat\n",
        flush=True,
    )


def _pause_console_if_windows() -> None:
    if sys.platform != "win32":
        return
    try:
        input("종료하려면 Enter 키를 누르세요…")
    except (EOFError, OSError):
        pass


def main(argv: list[str]) -> int:
    import argparse

    ap = argparse.ArgumentParser(description="문제 추출 — OCR(무료) 또는 Vision(OpenAI)")
    ap.add_argument("-o", "--out", type=Path, help="출력 JSON (기본: tools/admin/_out/ocr_|vision_<시각>.json)")
    ap.add_argument("--ocr", action="store_true", help="Tesseract OCR만 사용 (OpenAI 과금 없음)")
    ap.add_argument("--pack-no", type=int, default=0, dest="pack_no")
    ap.add_argument("--unit-id", default="00000000-0000-0000-0000-000000000001")
    ap.add_argument("--sql", action="store_true")
    ap.add_argument("--data-js", action="store_true")
    ap.add_argument(
        "--spread",
        action="store_true",
        help="이미지 2장(앞장→뒷장)을 한 요청으로 보내 해설이 다음 장에 이어질 때 합칩니다. paths 는 정확히 2개.",
    )
    ap.add_argument("paths", nargs="*", type=Path, default=[], help="이미지 또는 PDF 경로 (없으면 도움말만)")
    args = ap.parse_args(argv)

    if not args.paths:
        _print_cli_help()
        return 2

    out = args.out
    use_vision = not args.ocr
    if out is None:
        from datetime import datetime

        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        tag = "vision" if use_vision else "ocr"
        out = _ADMIN / "_out" / f"{tag}_{stamp}.json"

    res = run_batch(
        images=[Path(x) for x in args.paths],
        text_file=None,
        out=out,
        pack_no=args.pack_no,
        lang="kor+eng",
        explanation="",
        emit_sql=args.sql,
        unit_id=args.unit_id,
        emit_data_js=args.data_js,
        tesseract_cmd=None,
        spread_pair=args.spread,
        use_vision=use_vision,
    )
    for m in res.get("messages") or []:
        print(m)
    if not res.get("ok"):
        return 1
    if res.get("sql_text"):
        sp = Path(res["out_path"]).with_suffix(".sql")
        sp.write_text(res["sql_text"], encoding="utf-8")
        print("SQL:", sp)
    if res.get("data_js_text"):
        jp = Path(res["out_path"]).with_suffix(".data_js.txt")
        jp.write_text(res["data_js_text"], encoding="utf-8")
        print("data.js 스니펫:", jp)
    return 0


if __name__ == "__main__":
    _code = 1
    try:
        _code = main(sys.argv[1:])
    except SystemExit as _se:
        _c = _se.code
        _code = int(_c) if isinstance(_c, int) else 1
    except BaseException:
        import traceback

        traceback.print_exc()
        _code = 1
    if _code != 0 or len(sys.argv) < 2:
        _pause_console_if_windows()
    raise SystemExit(_code)

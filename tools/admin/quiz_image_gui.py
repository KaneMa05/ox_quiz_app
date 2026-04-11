# -*- coding: utf-8 -*-
"""OX 퀴즈 이미지 가공 GUI. 실행: tools/admin/LAUNCH_GUI.bat (또는 quiz_image_gui.py)."""
from __future__ import annotations

import os
import sys
import threading
import traceback
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk

import tkinter as tk

_ADMIN_DIR = Path(__file__).resolve().parent
_APP_ROOT = _ADMIN_DIR.parent.parent
_OUT_DIR = _ADMIN_DIR / "_out"

if str(_ADMIN_DIR) not in sys.path:
    sys.path.insert(0, str(_ADMIN_DIR))

os.environ["OX_QUIZ_ADMIN_TOOLS"] = "1"

from image_to_quiz_questions import _load_openai_key_from_env_local, get_tesseract_executable, run_batch


def _ensure_ocr_python_packages() -> None:
    """pytesseract / Pillow 없으면 안내 후 종료."""
    try:
        import pytesseract  # noqa: F401
        from PIL import Image  # noqa: F401
    except ImportError as e:
        root = tk.Tk()
        root.withdraw()
        cmd = (
            f'"{sys.executable}" -m pip install -r tools\\admin\\requirements-ocr.txt\n\n'
            "또는 ox-quiz-app 폴더에서:\n"
            "  py -3 -m pip install -r tools\\admin\\requirements-ocr.txt\n\n"
            "LAUNCH_GUI.bat 을 다시 실행하면 자동 설치를 시도합니다."
        )
        messagebox.showerror("Python 패키지 필요", f"{e}\n\n{cmd}")
        root.destroy()
        raise SystemExit(1) from e


def open_in_explorer(path: Path) -> None:
    path = path.resolve()
    folder = path if path.is_dir() else path.parent
    if not folder.is_dir():
        messagebox.showwarning("알림", "열 폴더가 없습니다. 먼저 저장이 된 뒤 다시 시도하세요.")
        return
    if sys.platform == "win32":
        os.startfile(str(folder))  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        import subprocess

        subprocess.Popen(["open", str(folder)])
    else:
        import subprocess

        subprocess.Popen(["xdg-open", str(folder)])


class QuizImageGuiApp:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("OX 퀴즈 이미지 가공 (관리자)")
        self.root.minsize(520, 560)
        self.root.geometry("640x620")

        if sys.platform == "win32":
            try:
                self.root.call("tk", "scaling", 1.15)
            except Exception:
                pass

        self._font_ui = ("Malgun Gothic", 10) if sys.platform == "win32" else (None, 11)
        self._font_title = ("Malgun Gothic", 13, "bold") if sys.platform == "win32" else (None, 14, "bold")

        self.mode = tk.StringVar(value="ocr")
        self.image_paths: list[Path] = []
        self.text_path: Path | None = None
        self.last_json: Path | None = None

        self.var_pack = tk.StringVar(value="0")
        self.var_lang = tk.StringVar(value="kor+eng")
        self.var_unit = tk.StringVar(value="00000000-0000-0000-0000-000000000001")
        self.var_explain = tk.StringVar(value="OCR 가공 - 해설을 채워 주세요.")
        self.var_emit_sql = tk.BooleanVar(value=True)
        self.var_emit_js = tk.BooleanVar(value=True)
        self.var_spread_pair = tk.BooleanVar(value=False)
        self.var_tesseract = tk.StringVar()
        self._tesseract_hint = _ADMIN_DIR / ".tesseract_path"
        self._load_tesseract_hint()

        self._build()

    def _build(self) -> None:
        pad = {"padx": 10, "pady": 6}
        root = self.root

        ttk.Label(root, text="문제 이미지를 넣으면 JSON·SQL 초안이 나옵니다.", font=self._font_title).pack(
            anchor="w", **pad
        )
        ttk.Label(
            root,
            text="일반 퀴즈 웹앱과 분리된 관리자 전용 창입니다.",
            font=self._font_ui,
        ).pack(anchor="w", padx=10)

        tess_f = ttk.LabelFrame(root, text="Tesseract (무료 OCR — kor 언어팩 설치 권장)", padding=8)
        tess_f.pack(fill="x", **pad)
        ttk.Label(
            tess_f,
            text="tesseract.exe 경로 (비우면 자동 검색). 설치: github.com/UB-Mannheim/tesseract/wiki",
            font=self._font_ui,
        ).pack(anchor="w")
        tess_row = ttk.Frame(tess_f)
        tess_row.pack(fill="x", pady=(6, 0))
        self.entry_tesseract = ttk.Entry(tess_row, textvariable=self.var_tesseract, width=70)
        self.entry_tesseract.pack(side="left", fill="x", expand=True, padx=(0, 6))
        ttk.Button(tess_row, text="찾아보기…", command=self._pick_tesseract_exe).pack(side="left", padx=2)
        ttk.Button(tess_row, text="자동 찾기", command=self._autodetect_tesseract).pack(side="left", padx=2)
        ttk.Button(tess_row, text="경로 저장", command=self._save_tesseract_hint).pack(side="left", padx=2)

        mode_f = ttk.LabelFrame(root, text="입력 방식", padding=8)
        mode_f.pack(fill="x", **pad)
        ttk.Radiobutton(
            mode_f,
            text="이미지/PDF → Tesseract OCR (무료, 과금 없음)",
            variable=self.mode,
            value="ocr",
        ).grid(row=0, column=0, sticky="w")
        ttk.Radiobutton(
            mode_f,
            text="이미지/PDF → Vision (OpenAI, 사용량 과금)",
            variable=self.mode,
            value="vision",
        ).grid(row=1, column=0, sticky="w")
        ttk.Radiobutton(
            mode_f,
            text="텍스트 파일만 (①~④ + 정답: 줄 — OCR 생략)",
            variable=self.mode,
            value="text",
        ).grid(row=2, column=0, sticky="w")

        img_f = ttk.LabelFrame(root, text="이미지", padding=8)
        img_f.pack(fill="both", expand=False, **pad)
        btn_row = ttk.Frame(img_f)
        btn_row.pack(fill="x")
        self.btn_pick_img = ttk.Button(btn_row, text="이미지 고르기…", command=self._pick_images)
        self.btn_pick_img.pack(side="left", padx=(0, 8))
        self.btn_clear_img = ttk.Button(btn_row, text="목록 비우기", command=self._clear_images)
        self.btn_clear_img.pack(side="left")

        self.list_images = tk.Listbox(img_f, height=5, font=self._font_ui, selectmode=tk.EXTENDED)
        self.list_images.pack(fill="both", expand=True, pady=(6, 0))

        tx_f = ttk.LabelFrame(root, text="텍스트 파일", padding=8)
        tx_f.pack(fill="x", **pad)
        ttk.Button(tx_f, text="텍스트 파일 고르기…", command=self._pick_text).pack(side="left")
        self.lbl_text = ttk.Label(tx_f, text="(선택 안 함)")
        self.lbl_text.pack(side="left", padx=12)

        opt_f = ttk.LabelFrame(root, text="옵션", padding=8)
        opt_f.pack(fill="x", **pad)
        g1 = ttk.Frame(opt_f)
        g1.pack(fill="x")
        ttk.Label(g1, text="pack_no:").pack(side="left")
        ttk.Entry(g1, textvariable=self.var_pack, width=8).pack(side="left", padx=(4, 16))
        ttk.Label(g1, text="Tesseract 언어:").pack(side="left")
        ttk.Entry(g1, textvariable=self.var_lang, width=14).pack(side="left", padx=4)

        g2 = ttk.Frame(opt_f)
        g2.pack(fill="x", pady=(8, 0))
        ttk.Label(g2, text="SQL용 unit_id (UUID):").pack(side="left")
        ttk.Entry(g2, textvariable=self.var_unit, width=42).pack(side="left", padx=4, fill="x", expand=True)

        g3 = ttk.Frame(opt_f)
        g3.pack(fill="x", pady=(8, 0))
        ttk.Checkbutton(g3, text="SQL 파일도 같이 저장", variable=self.var_emit_sql).pack(side="left", padx=(0, 12))
        ttk.Checkbutton(g3, text="data.js용 q(...) 줄 파일도 저장", variable=self.var_emit_js).pack(side="left")

        g3b = ttk.Frame(opt_f)
        g3b.pack(fill="x", pady=(6, 0))
        ttk.Checkbutton(
            g3b,
            text="연속 2장(앞장→뒷장) — 해설이 다음 장으로 이어질 때. 이미지는 정확히 2장만 선택",
            variable=self.var_spread_pair,
        ).pack(anchor="w")

        g4 = ttk.Frame(opt_f)
        g4.pack(fill="x", pady=(8, 0))
        ttk.Label(g4, text="기본 해설 문구:").pack(side="left")
        ttk.Entry(g4, textvariable=self.var_explain).pack(side="left", padx=4, fill="x", expand=True)

        act = ttk.Frame(root)
        act.pack(fill="x", **pad)
        self.btn_run = ttk.Button(act, text="실행 (가공)", command=self._run_clicked)
        self.btn_run.pack(side="left", padx=(0, 8))
        ttk.Button(act, text="결과 폴더 열기", command=lambda: open_in_explorer(_OUT_DIR)).pack(side="left", padx=(0, 8))
        ttk.Button(act, text="종료", command=self.root.quit).pack(side="right")

        ttk.Label(root, text="실행 로그", font=self._font_ui).pack(anchor="w", padx=10)
        self.log = scrolledtext.ScrolledText(root, height=14, wrap="word", font=self._font_ui)
        self.log.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self._log(
            "기본은 무료 OCR입니다. Tesseract 설치 후「자동 찾기」를 한 번 누르세요.\n"
            "문항이 0개면 tools/admin/_out 의 *_ocr_raw.txt 를 열어, ①~④ 또는 1.~4. + 정답 줄을 손으로 맞춘 뒤「텍스트만」으로 다시 실행할 수 있습니다.\n"
            "저장: tools/admin/_out/\n"
        )
        self._try_autodetect_tesseract()
        self.mode.trace_add("write", lambda *_: self._on_mode_change())
        self._on_mode_change()

    def _load_tesseract_hint(self) -> None:
        try:
            if self._tesseract_hint.is_file():
                line = self._tesseract_hint.read_text(encoding="utf-8").splitlines()[0].strip().strip('"')
                if line:
                    self.var_tesseract.set(line)
        except OSError:
            pass

    def _try_autodetect_tesseract(self) -> None:
        if self.var_tesseract.get().strip():
            return
        ex = get_tesseract_executable()
        if ex:
            self.var_tesseract.set(ex)
            self._log(f"Tesseract 자동 감지: {ex}\n")

    def _pick_tesseract_exe(self) -> None:
        p = filedialog.askopenfilename(
            title="tesseract.exe 선택",
            filetypes=[("실행 파일", "*.exe"), ("모든 파일", "*.*")],
            initialdir=os.environ.get("ProgramFiles", "C:\\Program Files"),
        )
        if p:
            self.var_tesseract.set(p)

    def _autodetect_tesseract(self) -> None:
        self.var_tesseract.set("")
        ex = get_tesseract_executable()
        if ex:
            self.var_tesseract.set(ex)
            self._log(f"Tesseract 자동 감지: {ex}\n")
            messagebox.showinfo("자동 찾기", ex)
        else:
            messagebox.showwarning(
                "자동 찾기",
                "설치된 Tesseract를 찾지 못했습니다.\n"
                "Windows 설치 후 보통:\n"
                "C:\\Program Files\\Tesseract-OCR\\tesseract.exe",
            )

    def _save_tesseract_hint(self) -> None:
        p = self.var_tesseract.get().strip().strip('"')
        if not p:
            messagebox.showwarning("알림", "경로를 입력한 뒤 저장하세요.")
            return
        if not Path(p).is_file():
            messagebox.showerror("오류", "파일이 없습니다. tesseract.exe 전체 경로인지 확인하세요.")
            return
        try:
            self._tesseract_hint.parent.mkdir(parents=True, exist_ok=True)
            self._tesseract_hint.write_text(p + "\n", encoding="utf-8")
            messagebox.showinfo("저장됨", f"다음 실행부터 사용:\n{p}")
        except OSError as e:
            messagebox.showerror("저장 실패", str(e))

    def _on_mode_change(self) -> None:
        m = self.mode.get()
        if m in ("ocr", "vision"):
            self.list_images.config(state=tk.NORMAL)
            self.btn_pick_img.state(["!disabled"])
            self.btn_clear_img.state(["!disabled"])
        else:
            self.list_images.config(state=tk.DISABLED)
            self.btn_pick_img.state(["disabled"])
            self.btn_clear_img.state(["disabled"])

    def _log(self, s: str) -> None:
        self.log.insert(tk.END, s)
        self.log.see(tk.END)
        self.root.update_idletasks()

    def _pick_images(self) -> None:
        paths = filedialog.askopenfilenames(
            title="문제 이미지 선택",
            filetypes=[
                ("이미지/PDF", "*.png *.jpg *.jpeg *.webp *.tif *.tiff *.bmp *.pdf"),
                ("모든 파일", "*.*"),
            ],
            initialdir=str(_APP_ROOT),
        )
        if not paths:
            return
        for p in paths:
            path = Path(p)
            if path not in self.image_paths:
                self.image_paths.append(path)
        self._refresh_list()

    def _clear_images(self) -> None:
        self.image_paths.clear()
        self._refresh_list()

    def _refresh_list(self) -> None:
        self.list_images.delete(0, tk.END)
        for p in self.image_paths:
            self.list_images.insert(tk.END, str(p))

    def _pick_text(self) -> None:
        p = filedialog.askopenfilename(
            title="UTF-8 텍스트 선택",
            filetypes=[("텍스트", "*.txt"), ("모든 파일", "*.*")],
            initialdir=str(_ADMIN_DIR),
        )
        if not p:
            return
        self.text_path = Path(p)
        self.lbl_text.config(text=self.text_path.name)

    def _run_clicked(self) -> None:
        self.btn_run.config(state=tk.DISABLED)
        threading.Thread(target=self._run_worker, daemon=True).start()

    def _run_worker(self) -> None:
        try:
            try:
                pack_no = int(self.var_pack.get().strip() or "0")
            except ValueError:
                self.root.after(0, lambda: self._run_done(None, "pack_no 는 숫자여야 합니다."))
                return

            mode = self.mode.get()
            use_vision = mode == "vision"
            if mode in ("ocr", "vision"):
                images = list(self.image_paths)
                text_file = None
                if not images:
                    self.root.after(0, lambda: self._run_done(None, "이미지 또는 PDF를 한 개 이상 고르세요."))
                    return
                if use_vision:
                    _load_openai_key_from_env_local()
                    if not (os.environ.get("OPENAI_API_KEY") or "").strip():
                        self.root.after(
                            0,
                            lambda: self._run_done(
                                None,
                                "Vision 은 OPENAI_API_KEY 가 필요합니다. "
                                "무료로 하려면 입력 방식에서「Tesseract OCR」을 선택하세요.",
                            ),
                        )
                        return
                if self.var_spread_pair.get() and len(images) != 2:
                    self.root.after(
                        0,
                        lambda: self._run_done(
                            None,
                            "「연속 2장」은 파일을 정확히 2개(앞 → 뒷 순)만 선택하세요.",
                        ),
                    )
                    return
            else:
                images = []
                text_file = self.text_path
                if not text_file:
                    self.root.after(0, lambda: self._run_done(None, "텍스트 파일을 고르세요."))
                    return

            _OUT_DIR.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            out_json = _OUT_DIR / f"quiz_{stamp}.json"

            tess = self.var_tesseract.get().strip().strip('"') or None
            res = run_batch(
                images=images,
                text_file=text_file,
                out=out_json,
                pack_no=pack_no,
                lang=self.var_lang.get().strip() or "kor+eng",
                explanation=self.var_explain.get().strip() or "OCR 가공 - 해설을 채워 주세요.",
                emit_sql=self.var_emit_sql.get(),
                unit_id=self.var_unit.get().strip() or "00000000-0000-0000-0000-000000000001",
                emit_data_js=self.var_emit_js.get(),
                tesseract_cmd=tess,
                spread_pair=self.var_spread_pair.get(),
                use_vision=use_vision,
            )
            self.root.after(0, lambda: self._run_done(res, None))
        except Exception as ex:
            tb = traceback.format_exc()
            self.root.after(0, lambda: self._run_done(None, f"{ex}\n\n{tb}"))

    def _run_done(self, res: dict | None, err: str | None) -> None:
        self.btn_run.config(state=tk.NORMAL)
        if err:
            self._log(err + "\n")
            messagebox.showerror("실행 오류", err[:800])
            return
        assert res is not None
        for m in res.get("messages") or []:
            self._log(m + "\n")
        if not res.get("ok"):
            messagebox.showerror("실패", "\n".join(res.get("messages") or ["알 수 없는 오류"]))
            return

        out_path = res.get("out_path")
        if out_path:
            self.last_json = Path(out_path)
            stem = self.last_json.stem
            if res.get("sql_text"):
                sql_path = self.last_json.with_suffix(".sql")
                sql_path.write_text(res["sql_text"], encoding="utf-8")
                self._log(f"SQL 저장: {sql_path}\n")
            if res.get("data_js_text"):
                js_path = self.last_json.with_suffix(".data_js.txt")
                js_path.write_text(res["data_js_text"], encoding="utf-8")
                self._log(f"data.js 스니펫 저장: {js_path}\n")
            self._log("완료.\n")
            messagebox.showinfo("완료", f"저장 위치:\n{out_path}")
        else:
            messagebox.showwarning("알림", "출력 경로가 없습니다.")

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    try:
        _ensure_ocr_python_packages()
        app = QuizImageGuiApp()
        app.run()
    except Exception as e:
        try:
            messagebox.showerror("시작 오류", f"{e}\n\n{traceback.format_exc()}")
        except Exception:
            print(e, file=sys.stderr)
            traceback.print_exc()
        raise SystemExit(1) from e


if __name__ == "__main__":
    main()

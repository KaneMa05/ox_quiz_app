import argparse
from pathlib import Path

import pypdfium2 as pdfium
import pytesseract
from PIL import Image, ImageOps, ImageFilter

pytesseract.pytesseract.DEFAULT_ENCODING = "utf-8"


def resolve_tesseract_cmd():
    candidates = [
        Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe"),
        Path(r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"),
    ]
    for c in candidates:
        if c.exists():
            return str(c)
    return None


def preprocess(img: Image.Image) -> Image.Image:
    # OCR 품질 개선: 약한 대비 강화 + 노이즈 완화 (과한 이진화는 오히려 한글 손실)
    g = ImageOps.grayscale(img)
    g = ImageOps.autocontrast(g, cutoff=1)
    g = g.filter(ImageFilter.MedianFilter(size=3))
    return g


def ocr_pdf(pdf_path: Path, out_path: Path, lang: str = "kor+eng", scale: float = 3.2, psm: int = 4):
    tcmd = resolve_tesseract_cmd()
    if tcmd:
        pytesseract.pytesseract.tesseract_cmd = tcmd

    doc = pdfium.PdfDocument(str(pdf_path))
    chunks = []
    tessdata_dir = Path(r"C:\Users\myh20\ocrdata\tessdata")
    if not tessdata_dir.exists():
        tessdata_dir = Path(__file__).parent / "tessdata"
    tesseract_config = f"--oem 1 --psm {psm}"
    if tessdata_dir.exists():
        tesseract_config += f" --tessdata-dir {tessdata_dir}"

    for i in range(len(doc)):
        page = doc[i]
        bitmap = page.render(scale=scale)
        pil_image = bitmap.to_pil()
        if not isinstance(pil_image, Image.Image):
            pil_image = Image.fromarray(pil_image)

        w, h = pil_image.size
        split_x = int(w * 0.5)
        gutter = max(8, int(w * 0.015))

        left = pil_image.crop((0, 0, max(1, split_x - gutter), h))
        right = pil_image.crop((min(w - 1, split_x + gutter), 0, w, h))

        left_text = pytesseract.image_to_string(preprocess(left), lang=lang, config=tesseract_config).strip()
        right_text = pytesseract.image_to_string(preprocess(right), lang=lang, config=tesseract_config).strip()

        chunks.append(f"\n\n=== PAGE {i+1} / LEFT ===\n{left_text}\n")
        chunks.append(f"\n\n=== PAGE {i+1} / RIGHT ===\n{right_text}\n")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("".join(chunks), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--lang", default="kor+eng")
    parser.add_argument("--scale", type=float, default=3.2)
    parser.add_argument("--psm", type=int, default=4)
    args = parser.parse_args()

    ocr_pdf(Path(args.pdf), Path(args.out), lang=args.lang, scale=args.scale, psm=args.psm)
    print(f"done: {args.out}")


if __name__ == "__main__":
    main()

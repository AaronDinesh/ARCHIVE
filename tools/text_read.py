# tools/text_read.py
from pathlib import Path
import io
import fitz  # PyMuPDF
from PIL import Image
import pytesseract

def _pdf_text_pymupdf(path: str, max_pages: int | None = None) -> str:
    """
    Extract selectable text from PDF via PyMuPDF.
    Falls back to OCR only if almost nothing is found.
    """
    txt_parts = []
    doc = fitz.open(path)
    pages = range(len(doc)) if max_pages is None else range(min(max_pages, len(doc)))
    for i in pages:
        page = doc.load_page(i)
        # "text" is plain text extraction; "blocks" or "rawdict" if you need structure later
        txt_parts.append(page.get_text("text") or "")
    doc.close()
    return "\n".join(txt_parts).strip()

def _ocr_first_pages_with_pymupdf(pdf_path: str, pages: int = 1, dpi: int = 200) -> str:
    """
    Render first N pages to images and OCR with Tesseract.
    """
    try:
        doc = fitz.open(pdf_path)
        texts = []
        for i in range(min(pages, len(doc))):
            page = doc.load_page(i)
            pix = page.get_pixmap(dpi=dpi)
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            texts.append(pytesseract.image_to_string(img))
        doc.close()
        return "\n".join(texts)
    except Exception:
        return ""

def read_text_any(path: str, ocr_pages: int = 1, max_chars: int = 4000) -> str:
    """
    - PDFs: try PyMuPDF text; if too little, OCR first page(s).
    - Images: OCR directly.
    - Other files: read as UTF-8 best-effort.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(path)

    ext = p.suffix.lower()
    text = ""

    if ext == ".pdf":
        text = _pdf_text_pymupdf(str(p))
        if len(text) < 50:  # likely a scan → OCR first N pages
            text = _ocr_first_pages_with_pymupdf(str(p), pages=ocr_pages)
    elif ext in [".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"]:
        text = pytesseract.image_to_string(Image.open(p))
    else:
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            text = ""

    return (text or "")[:max_chars]

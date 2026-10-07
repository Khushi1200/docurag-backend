import os
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")

import io
import uuid
import pymupdf as fitz         # PyMuPDF
import pytesseract
from PIL import Image
from django.conf import settings

# Windows pe Tesseract ka path batao
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


def chunk_text(text, size=800, overlap=100):
    """Lambe text ko chhote overlapping pieces mein todta hai."""
    step = size - overlap
    chunks = []
    for i in range(0, len(text), step):
        piece = text[i:i + size].strip()
        if piece:
            chunks.append(piece)
    return chunks


def extract_page_text(page):
    """Pehle normal text try karta hai, agar bahut kam text mile to OCR karta hai."""
    text = page.get_text().strip()
    if len(text) >= 30:
        return text, False   # False = OCR nahi lagi

    # Scanned page lagta hai, OCR karo
    pix = page.get_pixmap(dpi=200)
    img_bytes = pix.tobytes("png")
    img = Image.open(io.BytesIO(img_bytes))
    ocr_text = pytesseract.image_to_string(img)
    return ocr_text.strip(), True   # True = OCR lagi


def ingest_document(doc):
    """
    Document object leta hai, uski PDF file kholta hai,
    har page ka text (ya OCR) nikaalta hai, aur embedded images save karta hai.
    Abhi ke liye sirf text/OCR/images save karega, embeddings Part 4 mein aayenge.
    """
    pdf_path = doc.file.path
    pdf = fitz.open(pdf_path)

    img_dir = settings.MEDIA_ROOT / "images"
    img_dir.mkdir(parents=True, exist_ok=True)

    all_pages_data = []   # [{page, text, used_ocr}, ...]
    saved_images = []     # [{page, filename}, ...]

    for page_no, page in enumerate(pdf, start=1):
        text, used_ocr = extract_page_text(page)
        all_pages_data.append({
            "page": page_no,
            "text": text,
            "used_ocr": used_ocr,
            "chunks": chunk_text(text),
        })

        # Is page ke embedded images nikaalo
        for img_index, img in enumerate(page.get_images(full=True)):
            xref = img[0]
            base = pdf.extract_image(xref)
            img_bytes = base["image"]
            ext = base["ext"]

            # Bahut chhoti images (icons/logos) skip karo
            if base["width"] < 150 or base["height"] < 150:
                continue

            fname = f"{doc.id}_{uuid.uuid4().hex}.{ext}"
            (img_dir / fname).write_bytes(img_bytes)
            saved_images.append({"page": page_no, "filename": fname})

    doc.num_pages = len(pdf)
    doc.status = "ready"
    doc.save()

    return {
        "pages": all_pages_data,
        "images": saved_images,
    }
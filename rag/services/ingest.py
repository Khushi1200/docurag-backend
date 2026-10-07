import os
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")

import io
import uuid
import pymupdf as fitz
import pytesseract
from PIL import Image
from django.conf import settings

from .embeddings import text_model, clip_model, collections

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
        return text, False

    pix = page.get_pixmap(dpi=200)
    img_bytes = pix.tobytes("png")
    img = Image.open(io.BytesIO(img_bytes))
    ocr_text = pytesseract.image_to_string(img)
    return ocr_text.strip(), True


def ingest_document(doc):
    """
    PDF ko process karta hai: text/OCR nikaalta hai, chunks banata hai,
    images extract karta hai, aur sabko Chroma mein embeddings ke saath save karta hai.
    """
    pdf_path = doc.file.path
    pdf = fitz.open(pdf_path)

    img_dir = settings.MEDIA_ROOT / "images"
    img_dir.mkdir(parents=True, exist_ok=True)

    text_col, img_col = collections()

    total_chunks = 0
    total_images = 0

    for page_no, page in enumerate(pdf, start=1):
        # ---- Text/OCR ----
        text, used_ocr = extract_page_text(page)
        chunks = chunk_text(text)

        if chunks:
            embeddings = text_model().encode(chunks).tolist()
            ids = [str(uuid.uuid4()) for _ in chunks]
            metadatas = [
                {
                    "user_id": doc.owner_id,
                    "doc_id": doc.id,
                    "doc_name": doc.name,
                    "page": page_no,
                    "used_ocr": used_ocr,
                }
                for _ in chunks
            ]
            text_col.add(ids=ids, documents=chunks, embeddings=embeddings, metadatas=metadatas)
            total_chunks += len(chunks)

        # ---- Images ----
        for img in page.get_images(full=True):
            xref = img[0]
            base = pdf.extract_image(xref)
            img_bytes = base["image"]
            ext = base["ext"]

            if base["width"] < 150 or base["height"] < 150:
                continue   # chhote icons/logos skip

            fname = f"{doc.id}_{uuid.uuid4().hex}.{ext}"
            (img_dir / fname).write_bytes(img_bytes)

            pil_img = Image.open(img_dir / fname).convert("RGB")
            img_embedding = clip_model().encode(pil_img).tolist()

            img_col.add(
                ids=[str(uuid.uuid4())],
                documents=[f"image on page {page_no} of {doc.name}"],
                embeddings=[img_embedding],
                metadatas=[{
                    "user_id": doc.owner_id,
                    "doc_id": doc.id,
                    "doc_name": doc.name,
                    "page": page_no,
                    "filename": fname,
                }],
            )
            total_images += 1

    doc.num_pages = len(pdf)
    doc.status = "ready"
    doc.save()

    return {"pages": len(pdf), "chunks_saved": total_chunks, "images_saved": total_images}


def delete_document_data(doc):
    """Document delete hone par uske saare vectors aur images bhi hatata hai."""
    text_col, img_col = collections()
    img_dir = settings.MEDIA_ROOT / "images"

    img_records = img_col.get(where={"doc_id": doc.id}, include=["metadatas"])
    for m in img_records["metadatas"]:
        fpath = img_dir / m["filename"]
        if fpath.exists():
            fpath.unlink()

    text_col.delete(where={"doc_id": doc.id})
    img_col.delete(where={"doc_id": doc.id})
    doc.file.delete(save=False)
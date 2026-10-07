import django
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "docurag.settings")
django.setup()

from django.contrib.auth.models import User
from rag.models import Document
from rag.services.ingest import ingest_document

# Apna test PDF ka naam yahan likho
PDF_PATH = "media/docs/scan_test.pdf"

# Pehla user lo (superuser jo banaya tha)
user = User.objects.first()
if not user:
    print("Pehle 'python manage.py createsuperuser' chalao!")
    exit()

# Document record banao
with open(PDF_PATH, "rb") as f:
    from django.core.files import File
    doc = Document.objects.create(owner=user, name="scan_test.pdf")
    doc.file.save("scan_test.pdf", File(f), save=True)

print(f"Document created: id={doc.id}, status={doc.status}")

result = ingest_document(doc)

print(f"\nTotal pages: {len(result['pages'])}")
for p in result["pages"]:
    print(f"  Page {p['page']}: {len(p['chunks'])} chunks, OCR used: {p['used_ocr']}")
    print(f"    Preview: {p['text'][:100]}...")

print(f"\nImages saved: {len(result['images'])}")
for img in result["images"]:
    print(f"  Page {img['page']}: {img['filename']}")

doc.refresh_from_db()
print(f"\nFinal status: {doc.status}, num_pages: {doc.num_pages}")
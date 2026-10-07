import django
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "docurag.settings")
django.setup()

from django.contrib.auth.models import User
from rag.models import Document
from rag.services.ingest import ingest_document
from rag.services.retrieve import retrieve

PDF_PATH = "media/docs/scan_test.pdf"   # pehle wali PDF use kar rahe hain
QUESTION = "What does SUAACTION focus on?"   # apna sawal yahan daalo

user = User.objects.first()
if not user:
    print("Pehle superuser banao!")
    exit()

# Naya document banao aur ingest karo
with open(PDF_PATH, "rb") as f:
    from django.core.files import File
    doc = Document.objects.create(owner=user, name="test_for_retrieve.pdf")
    doc.file.save("test_for_retrieve.pdf", File(f), save=True)

print("Ingesting...")
result = ingest_document(doc)
print(f"Done: {result}")

print(f"\nQuestion: {QUESTION}")
chunks, images, confidence = retrieve(QUESTION, user_id=user.id)

print(f"\nConfidence: {confidence}")
print(f"\nTop {len(chunks)} text chunks:")
for c in chunks:
    print(f"  [score={c['score']}] page {c['page']}: {c['text'][:100]}...")

print(f"\nTop {len(images)} images:")
for i in images:
    print(f"  [score={i['score']}] page {i['page']}: {i['filename']}")
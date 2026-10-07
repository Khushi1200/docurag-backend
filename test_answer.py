import django
import os
import time

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "docurag.settings")
django.setup()

from django.contrib.auth.models import User
from rag.models import Document
from rag.services.ingest import ingest_document
from rag.services.retrieve import retrieve
from rag.services.generate import generate_answer

PDF_PATH = "media/docs/test.pdf"
QUESTION = "What is this document about?"

user = User.objects.first()
if not user:
    print("Pehle superuser banao!")
    exit()

with open(PDF_PATH, "rb") as f:
    from django.core.files import File
    doc = Document.objects.create(owner=user, name="test_answer.pdf")
    doc.file.save("test_answer.pdf", File(f), save=True)

print("Ingesting...")
ingest_document(doc)

print(f"\nQuestion: {QUESTION}")
start = time.time()

chunks, images, confidence = retrieve(QUESTION, user_id=user.id)

if not chunks or confidence < 0.25:
    answer = "Not found in the documents."
else:
    answer = generate_answer(QUESTION, chunks, images)

elapsed = round(time.time() - start, 2)

sources = [
    {"type": "text", "doc": c["doc"], "page": c["page"], "snippet": c["text"][:200]}
    for c in chunks[:3]
]
sources += [
    {"type": "image", "doc": i["doc"], "page": i["page"], "filename": i["filename"]}
    for i in images[:2]
]

result = {
    "answer": answer,
    "sources": sources,
    "confidence": confidence,
    "response_time_sec": elapsed,
}

print("\n--- FINAL RESULT (yahi format API se bhi aayega) ---")
import json
print(json.dumps(result, indent=2, ensure_ascii=False))
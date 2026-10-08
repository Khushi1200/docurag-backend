import django
import os
import time

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "docurag.settings")
django.setup()

import json
from django.contrib.auth.models import User
from rag.models import Document
from rag.services.retrieve import retrieve
from rag.services.generate import generate_answer

user = User.objects.first()
if not user:
    print("Pehle superuser banao!")
    exit()

with open("eval_questions.json", "r", encoding="utf-8") as f:
    test_cases = json.load(f)

results = []
correct_hit = 0
correct_hallucination_guard = 0
total_time = 0

for case in test_cases:
    question = case["question"]
    expect_page = case.get("expect_page")
    should_find = case["should_find"]

    start = time.time()
    chunks, images, confidence = retrieve(question, user_id=user.id)

    if not chunks or confidence < 0.25:
        answer = "Not found in the documents."
        found_page = None
    else:
        answer = generate_answer(question, chunks, images)
        found_page = chunks[0]["page"] if chunks else None

    elapsed = round(time.time() - start, 2)
    total_time += elapsed

    is_hallucination_guard_case = not should_find
    guard_correct = is_hallucination_guard_case and "not found" in answer.lower()
    hit_correct = should_find and found_page == expect_page

    if is_hallucination_guard_case and guard_correct:
        correct_hallucination_guard += 1
    if should_find and hit_correct:
        correct_hit += 1

    results.append({
        "question": question,
        "confidence": confidence,
        "found_page": found_page,
        "expected_page": expect_page,
        "time_sec": elapsed,
        "answer_preview": answer[:100],
    })

print("=" * 60)
print("EVALUATION REPORT")
print("=" * 60)

should_find_count = sum(1 for c in test_cases if c["should_find"])
should_not_find_count = sum(1 for c in test_cases if not c["should_find"])

print(f"\nTotal questions tested: {len(test_cases)}")
print(f"Retrieval hit rate (correct page found): {correct_hit}/{should_find_count}")
print(f"Hallucination guard (correctly said 'not found'): {correct_hallucination_guard}/{should_not_find_count}")
print(f"Average response time: {round(total_time / len(test_cases), 2)}s")

print("\nDetailed results:")
for r in results:
    status = "OK" if (r["found_page"] == r["expected_page"]) else "CHECK"
    print(f"  [{status}] Q: {r['question']}")
    print(f"        confidence={r['confidence']}, found_page={r['found_page']}, time={r['time_sec']}s")
    print(f"        answer: {r['answer_preview']}...")
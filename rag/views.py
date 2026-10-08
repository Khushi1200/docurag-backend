class EvaluateView(APIView):
    def post(self, request):
        import json, time
        with open("eval_questions.json") as f:
            test_cases = json.load(f)

        results = []
        for case in test_cases:
            start = time.time()
            chunks, images, confidence = retrieve(case["question"], request.user.id)
            if not chunks or confidence < 0.25:
                answer = "Not found in the documents."
            else:
                answer = generate_answer(case["question"], chunks, images)
            results.append({
                "question": case["question"],
                "confidence": confidence,
                "time_sec": round(time.time() - start, 2),
                "answer": answer[:150],
            })
        return Response({"results": results})
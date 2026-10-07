from .embeddings import text_model, clip_model, collections

IMG_MIN_SCORE = 0.20   # isse kam score wali images ko ignore karo


def retrieve(question, user_id, doc_ids=None, k_text=5, k_img=3):
    """
    Sawal leke, us user ke documents mein se sabse relevant
    text chunks aur images dhundta hai, saath mein ek confidence score deta hai.
    """
    text_col, img_col = collections()

    where = {"user_id": user_id}
    if doc_ids:
        where = {"$and": [{"user_id": user_id}, {"doc_id": {"$in": list(doc_ids)}}]}

    chunks = []
    n_text = len(text_col.get(where=where, include=[])["ids"])
    if n_text:
        result = text_col.query(
            query_embeddings=text_model().encode([question]).tolist(),
            n_results=min(k_text, n_text),
            where=where,
        )
        for doc_text, meta, dist in zip(
            result["documents"][0], result["metadatas"][0], result["distances"][0]
        ):
            chunks.append({
                "doc": meta["doc_name"],
                "page": meta["page"],
                "text": doc_text,
                "score": round(1 - dist, 3),
            })

    images = []
    n_img = len(img_col.get(where=where, include=[])["ids"])
    if n_img:
        result = img_col.query(
            query_embeddings=clip_model().encode([question]).tolist(),
            n_results=min(k_img, n_img),
            where=where,
        )
        for meta, dist in zip(result["metadatas"][0], result["distances"][0]):
            score = round(1 - dist, 3)
            if score >= IMG_MIN_SCORE:
                images.append({
                    "doc": meta["doc_name"],
                    "page": meta["page"],
                    "filename": meta["filename"],
                    "score": score,
                })

    # Confidence: top-3 text chunks ke average score se banaya gaya heuristic
    top_scores = [c["score"] for c in chunks[:3]]
    if top_scores:
        confidence = round(min(1.0, max(0.0, (sum(top_scores) / len(top_scores)) / 0.6)), 2)
    else:
        confidence = 0.0

    return chunks, images, confidence
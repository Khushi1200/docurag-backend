import os
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")

import chromadb
from django.conf import settings
from sentence_transformers import SentenceTransformer

_text_model = None
_clip_model = None
_client = None


def text_model():
    """Text ko embedding (numbers ki list) mein badalta hai. Ek hi baar load hota hai."""
    global _text_model
    if _text_model is None:
        _text_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    return _text_model


def clip_model():
    """Images ko embedding mein badalta hai. Ek hi baar load hota hai."""
    global _clip_model
    if _clip_model is None:
        _clip_model = SentenceTransformer("sentence-transformers/clip-ViT-B-32")
    return _clip_model


def collections():
    """Chroma database se do collections (text aur images) deta hai."""
    global _client
    if _client is None:
        settings.CHROMA_DIR.mkdir(parents=True, exist_ok=True)
        _client = chromadb.PersistentClient(path=str(settings.CHROMA_DIR))

    meta = {"hnsw:space": "cosine"}
    text_col = _client.get_or_create_collection("text_chunks", metadata=meta)
    img_col = _client.get_or_create_collection("images", metadata=meta)
    return text_col, img_col
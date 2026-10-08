# DocuRAG Backend

AI-powered multimodal document search using Retrieval-Augmented Generation (RAG).
Upload PDFs, ask questions in natural language, get grounded answers with sources,
confidence scores, and response times.

## Architecture

Frontend (Streamlit/React)
      |
Django REST API (JWT auth)
      |
  +---+---+
  |       |
Ingest   Retrieve
(PyMuPDF, |   |
OCR,      | ChromaDB (vector store)
CLIP)     |   |
          | Groq / Gemini (LLM)

1. **Ingest**: PDF text extracted via PyMuPDF; scanned pages fall back to Tesseract OCR.
   Embedded images are extracted and embedded with CLIP.
2. **Store**: Text chunks (MiniLM embeddings) and images (CLIP embeddings) are stored
   in ChromaDB, tagged with user_id and doc_id.
3. **Retrieve**: A question is embedded and matched against stored vectors using
   cosine similarity.
4. **Generate**: Retrieved context + images are sent to Groq (qwen/qwen3.8-27b).
   Gemini is used as a fallback when more than 3 images are needed.

## Tech Stack

- Backend: Django + Django REST Framework
- Auth: JWT (djangorestframework-simplejwt)
- Vector DB: ChromaDB
- Embeddings: sentence-transformers (MiniLM for text, CLIP for images)
- OCR: Tesseract
- LLM: Groq (primary), Gemini (fallback for 3+ images)

## Setup

1. Clone the repo and create a virtual environment:

python -m venv venv
venv\Scripts\activate
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.tx

2. Copy `.env.example` to `.env` and fill in your Groq, Gemini, and HuggingFace keys.
3. Run migrations and start the server:

python manage.py migrate
python manage.py runserver


## API Routes

| Method | Route | Auth | Description |
|---|---|---|---|
| GET | /api/health/ | No | Health check |
| POST | /api/auth/register/ | No | Create account |
| POST | /api/auth/login/ | No | Get JWT tokens |
| POST | /api/auth/refresh/ | No | Refresh access token |
| GET | /api/auth/me/ | Yes | Current user info |
| POST | /api/documents/upload/ | Yes | Upload a PDF |
| GET | /api/documents/ | Yes | List user's documents |
| DELETE | /api/documents/<id>/ | Yes | Delete a document |
| POST | /api/ask/ | Yes | Ask a question |

## Evaluation

Run `python evaluate.py` to test retrieval accuracy and hallucination guarding
against a small labeled test set (`eval_questions.json`).

## Unique Features

- Multimodal retrieval: text AND images are searched and cited.
- Hallucination guard: confidence-based cutoff returns "Not found" instead of
  making up an answer.
- Smart LLM routing: Groq for speed, automatic Gemini fallback for >3 images
  or Groq failures.
- Full evaluation harness with retrieval hit rate, hallucination guard rate,
  and response time tracking.

## Team

- Backend: [Khushi Singh]
- Frontend: [teammate]
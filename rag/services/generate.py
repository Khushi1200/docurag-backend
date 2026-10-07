import base64
import io
from django.conf import settings
from groq import Groq
from PIL import Image

groq_client = Groq(api_key=settings.GROQ_API_KEY)


def build_prompt(question, chunks):
    """Chunks ko ek context string mein jodta hai aur LLM ke liye prompt banata hai."""
    context = "\n\n".join(
        f"[{c['doc']}, page {c['page']}]\n{c['text']}" for c in chunks
    )
    return (
        "You are a document assistant. Answer ONLY using the context and images "
        "provided below. Mention the page numbers you used. If the answer is not "
        "present in the context, reply exactly: 'Not found in the documents.'\n\n"
        f"Context:\n{context}\n\nQuestion: {question}"
    )


def _image_to_data_url(filename):
    """Local image file ko base64 data URL mein badalta hai, LLM ko bhejne ke liye."""
    path = settings.MEDIA_ROOT / "images" / filename
    img = Image.open(path).convert("RGB")
    img.thumbnail((1024, 1024))   # size chhota rakho
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    b64 = base64.b64encode(buf.getvalue()).decode()
    return f"data:image/jpeg;base64,{b64}"


def _ask_groq(question, chunks, images):
    """Groq ko call karta hai. Max 3 images tak hi support karta hai."""
    prompt = build_prompt(question, chunks)
    content = [{"type": "text", "text": prompt}]

    for img in images[:3]:
        content.append({
            "type": "image_url",
            "image_url": {"url": _image_to_data_url(img["filename"])},
        })

    response = groq_client.chat.completions.create(
        model=settings.GROQ_MODEL,
        messages=[{"role": "user", "content": content}],
        temperature=0.1,
        max_tokens=700,
    )
    return response.choices[0].message.content


def _ask_gemini(question, chunks, images):
    """Gemini ko call karta hai, jab 3 se zyada images bhejni hon."""
    import google.generativeai as genai

    genai.configure(api_key=settings.GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-2.0-flash")

    prompt = build_prompt(question, chunks)
    parts = [prompt]

    for img in images:
        path = settings.MEDIA_ROOT / "images" / img["filename"]
        parts.append(Image.open(path).convert("RGB"))

    response = model.generate_content(parts)
    return response.text


def generate_answer(question, chunks, images):
    """
    Groq aur Gemini ke beech smart routing karta hai:
    - 3 ya kam images: Groq (tez, free)
    - 3 se zyada images: Gemini (zyada images handle kar sakta hai)
    """
    if len(images) <= 3:
        try:
            return _ask_groq(question, chunks, images)
        except Exception as e:
            if settings.GEMINI_API_KEY:
                return _ask_gemini(question, chunks, images)
            raise e
    else:
        if settings.GEMINI_API_KEY:
            return _ask_gemini(question, chunks, images)
        return _ask_groq(question, chunks, images[:3])
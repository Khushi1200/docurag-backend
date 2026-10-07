import os
from dotenv import load_dotenv

load_dotenv()

print("1) Groq test...")
from groq import Groq
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
r = client.chat.completions.create(
    model=os.getenv("GROQ_MODEL"),
    messages=[{"role": "user", "content": "Say hello in one short sentence."}],
    max_tokens=30,
)
print("Groq says:", r.choices[0].message.content)

print("2) Hugging Face text model...")
from sentence_transformers import SentenceTransformer
m = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
print("Text embedding shape:", m.encode(["hello world"]).shape)

print("3) CLIP image model...")
c = SentenceTransformer("sentence-transformers/clip-ViT-B-32")
print("CLIP embedding shape:", c.encode(["a bar chart"]).shape)

print("ALL GOOD!")
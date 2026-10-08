import threading
import time

from django.conf import settings
from django.db import close_old_connections
from rest_framework import generics
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import Document
from .serializers import RegisterSerializer, UserSerializer, DocumentSerializer, AskSerializer
from .services.ingest import ingest_document, delete_document_data
from .services.retrieve import retrieve
from .services.generate import generate_answer


# ---------- Health check ----------
class HealthView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        return Response({"status": "ok"})


# ---------- Auth ----------
class RegisterView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        s = RegisterSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        user = s.save()
        refresh = RefreshToken.for_user(user)
        return Response({
            "user": UserSerializer(user).data,
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        }, status=201)


class LoginView(TokenObtainPairView):
    pass


class MeView(APIView):
    def get(self, request):
        return Response(UserSerializer(request.user).data)


# ---------- Documents ----------
def _process_document(doc_id):
    """Background thread mein PDF process karta hai, taaki upload request turant return ho jaye."""
    try:
        doc = Document.objects.get(id=doc_id)
        ingest_document(doc)
    except Exception as e:
        Document.objects.filter(id=doc_id).update(status="failed", error=str(e)[:500])
    finally:
        close_old_connections()


class UploadView(APIView):
    parser_classes = [MultiPartParser]

    def post(self, request):
        f = request.FILES.get("file")
        if not f:
            return Response({"error": "No file provided. Use key 'file'."}, status=400)
        if not f.name.lower().endswith(".pdf"):
            return Response({"error": "Only PDF files are allowed."}, status=400)
        if f.size > settings.MAX_UPLOAD_MB * 1024 * 1024:
            return Response({"error": f"File larger than {settings.MAX_UPLOAD_MB} MB."}, status=400)

        doc = Document.objects.create(owner=request.user, file=f, name=f.name)
        threading.Thread(target=_process_document, args=(doc.id,), daemon=True).start()
        return Response(DocumentSerializer(doc).data, status=202)


class DocumentListView(generics.ListAPIView):
    serializer_class = DocumentSerializer

    def get_queryset(self):
        return Document.objects.filter(owner=self.request.user)


class DocumentDetailView(generics.RetrieveDestroyAPIView):
    serializer_class = DocumentSerializer

    def get_queryset(self):
        return Document.objects.filter(owner=self.request.user)

    def perform_destroy(self, instance):
        delete_document_data(instance)
        instance.delete()


# ---------- Ask ----------
class AskView(APIView):
    def post(self, request):
        s = AskSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        question = s.validated_data["question"].strip()
        doc_ids = s.validated_data.get("document_ids")

        ready_docs = Document.objects.filter(owner=request.user, status="ready")
        if doc_ids:
            ready_docs = ready_docs.filter(id__in=doc_ids)

        if not ready_docs.exists():
            return Response({"error": "No processed documents found. Upload a PDF first."}, status=400)

        start = time.time()
        chunks, images, confidence = retrieve(
            question, request.user.id, list(ready_docs.values_list("id", flat=True))
        )

        if not chunks or confidence < 0.25:
            answer = "Not found in the documents."
        else:
            try:
                answer = generate_answer(question, chunks, images)
            except Exception:
                return Response({"error": "AI service error. Please try again."}, status=502)

        elapsed = round(time.time() - start, 2)

        sources = [
            {"type": "text", "doc": c["doc"], "page": c["page"], "snippet": c["text"][:250]}
            for c in chunks[:3]
        ]
        sources += [
            {"type": "image", "doc": i["doc"], "page": i["page"],
             "url": f"{settings.MEDIA_URL}images/{i['filename']}"}
            for i in images[:2]
        ]

        return Response({
            "answer": answer,
            "sources": sources,
            "confidence": confidence,
            "response_time_sec": elapsed,
        })
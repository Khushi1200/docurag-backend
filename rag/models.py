from django.db import models
from django.contrib.auth.models import User


class Document(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="documents")
    file = models.FileField(upload_to="docs/")
    name = models.CharField(max_length=255)
    num_pages = models.IntegerField(default=0)
    status = models.CharField(max_length=20, default="processing")  # processing / ready / failed
    error = models.TextField(blank=True, default="")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return self.name
from django.conf import settings
from django.db import models
from django.urls import reverse

from .choices import NoteType


class Note(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="career_notes",
    )
    note_type = models.CharField(max_length=40, choices=NoteType.choices, default=NoteType.GENERAL)
    title = models.CharField(max_length=180)
    content = models.TextField()
    tags = models.CharField(max_length=240, blank=True)
    decision_date = models.DateField(blank=True, null=True)
    is_important = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_important", "-decision_date", "-created_at"]
        verbose_name = "Note"
        verbose_name_plural = "Notes"

    def __str__(self):
        return f"{self.get_note_type_display()} — {self.title}"

    def get_absolute_url(self):
        return reverse("notes:note_detail", kwargs={"pk": self.pk})

    @property
    def tag_list(self):
        if not self.tags:
            return []
        return [tag.strip() for tag in self.tags.split(",") if tag.strip()]

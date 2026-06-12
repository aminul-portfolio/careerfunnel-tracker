from __future__ import annotations

from django.conf import settings
from django.core.files.storage import FileSystemStorage


class UploadedApplicationDocumentStorage(FileSystemStorage):
    def __init__(self):
        super().__init__(
            location=settings.UPLOADED_DOCUMENTS_ROOT,
            base_url=None,
        )

uploaded_application_document_storage = UploadedApplicationDocumentStorage()

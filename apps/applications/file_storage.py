from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from typing import Literal

from django.conf import settings
from django.utils import timezone

ApplicationDocumentKind = Literal["cv", "cover_letter", "application_pack"]

_DEFAULT_FILENAME_PART = "Application_Document"
_FILENAME_PART_PATTERN = re.compile(r"[^A-Za-z0-9._-]+")
_MAX_FILENAME_PART_LENGTH = 48
_MAX_FILENAME_BASE_LENGTH = 180

PROFESSIONAL_CV_PREFIX = "Aminul_Islam_CV"
PROFESSIONAL_COVER_LETTER_PREFIX = "Aminul_Islam_Cover_Letter"
PROFESSIONAL_APPLICATION_PACK_PREFIX = "Aminul_Islam_Application_Pack"


def get_storage_root() -> Path:
    return Path(settings.STORAGE_ROOT)


def get_generated_documents_root() -> Path:
    return Path(settings.GENERATED_DOCUMENTS_ROOT)


def get_generated_exports_root() -> Path:
    return Path(settings.GENERATED_EXPORTS_ROOT)


def get_generated_screenshots_root() -> Path:
    return Path(settings.GENERATED_SCREENSHOTS_ROOT)


def get_media_generated_documents_root() -> Path:
    return Path(settings.MEDIA_GENERATED_DOCUMENTS_ROOT)


def get_uploaded_documents_root() -> Path:
    return Path(settings.UPLOADED_DOCUMENTS_ROOT)


def sanitize_filename_part(value: str, *, fallback: str = _DEFAULT_FILENAME_PART) -> str:
    cleaned = _FILENAME_PART_PATTERN.sub("_", (value or "").strip())
    cleaned = re.sub(r"_+", "_", cleaned)
    cleaned = cleaned.strip("._")
    if len(cleaned) > _MAX_FILENAME_PART_LENGTH:
        cleaned = cleaned[:_MAX_FILENAME_PART_LENGTH].rstrip("_")
    return cleaned or fallback


def _filename_date_suffix(download_date: date | None = None) -> str:
    resolved_date = download_date or timezone.localdate()
    return resolved_date.strftime("%Y%m%d")


def build_professional_cv_basename(
    company_name: str,
    job_title: str,
    *,
    reference_date: date | None = None,
) -> str:
    company = sanitize_filename_part(company_name, fallback="Company")
    role = sanitize_filename_part(job_title, fallback="Role")
    date_suffix = _filename_date_suffix(reference_date)
    base = f"{PROFESSIONAL_CV_PREFIX}_{company}_{role}_{date_suffix}"
    if len(base) > _MAX_FILENAME_BASE_LENGTH:
        base = base[:_MAX_FILENAME_BASE_LENGTH].rstrip("_")
    return base


def _build_professional_download_filename(
    prefix: str,
    company_name: str,
    job_title: str,
    extension: str,
    *,
    download_date: date | None = None,
) -> str:
    if prefix == PROFESSIONAL_CV_PREFIX:
        base = build_professional_cv_basename(
            company_name,
            job_title,
            reference_date=download_date,
        )
    else:
        company = sanitize_filename_part(company_name, fallback="Company")
        role = sanitize_filename_part(job_title, fallback="Role")
        date_suffix = _filename_date_suffix(download_date)
        base = f"{prefix}_{company}_{role}_{date_suffix}"
        if len(base) > _MAX_FILENAME_BASE_LENGTH:
            base = base[:_MAX_FILENAME_BASE_LENGTH].rstrip("_")
    return assemble_download_filename(base, extension)


def build_professional_cv_download_filename(
    company_name: str,
    job_title: str,
    extension: str,
    *,
    download_date: date | None = None,
) -> str:
    return _build_professional_download_filename(
        PROFESSIONAL_CV_PREFIX,
        company_name,
        job_title,
        extension,
        download_date=download_date,
    )


def build_professional_cover_letter_download_filename(
    company_name: str,
    job_title: str,
    extension: str,
    *,
    download_date: date | None = None,
) -> str:
    return _build_professional_download_filename(
        PROFESSIONAL_COVER_LETTER_PREFIX,
        company_name,
        job_title,
        extension,
        download_date=download_date,
    )


def build_professional_application_pack_download_filename(
    company_name: str,
    job_title: str,
    extension: str,
    *,
    download_date: date | None = None,
) -> str:
    return _build_professional_download_filename(
        PROFESSIONAL_APPLICATION_PACK_PREFIX,
        company_name,
        job_title,
        extension,
        download_date=download_date,
    )


def build_safe_generated_filename(base_name: str, extension: str) -> str:
    raw_base = (base_name or "").strip()
    raw_extension = (extension or "").lower().lstrip(".")
    for raw_part in (raw_base, raw_extension):
        if ".." in raw_part or "/" in raw_part or "\\" in raw_part:
            raise ValueError("Generated filename must not contain path segments.")
    safe_base = sanitize_filename_part(raw_base)
    return assemble_download_filename(safe_base, raw_extension)


def assemble_download_filename(base: str, extension: str) -> str:
    raw_extension = (extension or "").lower().lstrip(".")
    for raw_part in (base, raw_extension):
        if ".." in raw_part or "/" in raw_part or "\\" in raw_part:
            raise ValueError("Generated filename must not contain path segments.")
    safe_extension = sanitize_filename_part(raw_extension, fallback="bin")
    safe_base = base
    if len(safe_base) > _MAX_FILENAME_BASE_LENGTH:
        safe_base = safe_base[:_MAX_FILENAME_BASE_LENGTH].rstrip("_")
    return f"{safe_base}.{safe_extension}"


def get_application_document_folder(
    application_id: int,
    document_kind: ApplicationDocumentKind,
) -> Path:
    if application_id <= 0:
        raise ValueError("Application id must be a positive integer.")
    if document_kind not in {"cv", "cover_letter", "application_pack"}:
        raise ValueError("Unsupported application document kind.")
    return (
        get_generated_documents_root()
        / "application_documents"
        / f"application_{application_id}"
        / document_kind
    )


def _forbidden_prefixes() -> tuple[str, ...]:
    return tuple(settings.FORBIDDEN_GENERATED_FILE_PREFIXES)


def assert_generated_path_is_safe(path: Path) -> Path:
    resolved = path.resolve()
    base_dir = Path(settings.BASE_DIR).resolve()
    try:
        relative = resolved.relative_to(base_dir)
    except ValueError:
        allowed_roots = (
            get_storage_root(),
            get_generated_documents_root(),
            get_uploaded_documents_root(),
            get_generated_exports_root(),
            get_generated_screenshots_root(),
            get_media_generated_documents_root(),
        )
        if not any(
            resolved == root.resolve() or root.resolve() in resolved.parents
            for root in allowed_roots
        ):
            raise ValueError("Generated files must stay within configured storage roots.")
        return resolved

    relative_posix = relative.as_posix()
    for prefix in _forbidden_prefixes():
        if relative_posix == prefix or relative_posix.startswith(f"{prefix}/"):
            raise ValueError(
                f"Generated files must not be stored under tracked source folder: {prefix}"
            )
    return resolved


def ensure_generated_folder(path: Path) -> Path:
    generated_root = get_generated_documents_root().resolve()
    resolved = path.resolve()
    if resolved != generated_root and generated_root not in resolved.parents:
        raise ValueError("Generated document path must stay within generated documents root.")
    assert_generated_path_is_safe(resolved)
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def write_generated_document_bytes(
    application_id: int,
    document_kind: ApplicationDocumentKind,
    filename: str,
    content: bytes,
) -> Path:
    safe_filename = build_safe_generated_filename(
        Path(filename).stem,
        Path(filename).suffix.lstrip("."),
    )
    folder = ensure_generated_folder(
        get_application_document_folder(application_id, document_kind)
    )
    destination = folder / safe_filename
    if destination.resolve() != (folder / safe_filename).resolve():
        raise ValueError("Generated document filename resolved outside target folder.")
    destination.write_bytes(content)
    return destination


def normalize_upload_extension(extension: str) -> str:
    cleaned = (extension or "").lower().lstrip(".")
    return cleaned


def build_upload_storage_relative_path(
    *,
    application_id: int,
    document_type: str,
    original_filename: str,
) -> str:
    if application_id <= 0:
        raise ValueError("Application id must be a positive integer.")
    folder_kind = "cv" if document_type == "cv" else "cover_letter"
    safe_name = build_unique_upload_filename(original_filename)
    return f"application_{application_id}/{folder_kind}/uploads/{safe_name}"


def build_unique_upload_filename(original_filename: str) -> str:
    raw_name = (original_filename or "").strip()
    if ".." in raw_name or "/" in raw_name or "\\" in raw_name:
        raise ValueError("Uploaded filename must not contain path segments.")
    stem = Path(raw_name).stem
    extension = normalize_upload_extension(Path(raw_name).suffix)
    safe_stem = sanitize_filename_part(stem)
    if not extension:
        raise ValueError("Uploaded filename must include an extension.")
    timestamp = timezone.now().strftime("%Y%m%d_%H%M%S")
    return assemble_download_filename(f"{safe_stem}_{timestamp}", extension)


def resolve_upload_absolute_path(relative_path: str) -> Path:
    root = get_uploaded_documents_root().resolve()
    destination = (root / relative_path).resolve()
    if root not in destination.parents and destination != root:
        raise ValueError("Uploaded document path resolved outside upload root.")
    assert_generated_path_is_safe(destination)
    return destination

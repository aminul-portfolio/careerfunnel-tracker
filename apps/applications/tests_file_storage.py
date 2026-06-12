from __future__ import annotations

import tempfile
from contextlib import contextmanager
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase, override_settings

from apps.applications.file_storage import (
    assert_generated_path_is_safe,
    build_safe_generated_filename,
    ensure_generated_folder,
    get_application_document_folder,
    get_generated_documents_root,
    get_generated_exports_root,
    get_generated_screenshots_root,
    get_storage_root,
    write_generated_document_bytes,
)

FORBIDDEN_SOURCE_PREFIXES = (
    "apps",
    "templates",
    "static",
    "docs",
    "data/master_cv",
)


@contextmanager
def temporary_generated_storage():
    with tempfile.TemporaryDirectory(dir=settings.BASE_DIR) as tmp:
        storage_root = Path(tmp) / "storage"
        media_root = Path(tmp) / "media"
        generated_documents_root = storage_root / "generated_documents"
        with override_settings(
            STORAGE_ROOT=storage_root,
            GENERATED_DOCUMENTS_ROOT=generated_documents_root,
            GENERATED_EXPORTS_ROOT=storage_root / "exports",
            GENERATED_SCREENSHOTS_ROOT=storage_root / "screenshots",
            MEDIA_GENERATED_DOCUMENTS_ROOT=media_root / "generated_documents",
        ):
            yield storage_root, generated_documents_root


class GeneratedStorageRootTests(SimpleTestCase):
    def test_storage_roots_use_dedicated_storage_folder(self):
        storage_root = get_storage_root()
        generated_root = get_generated_documents_root()
        self.assertEqual(storage_root.name, "storage")
        self.assertEqual(generated_root, storage_root / "generated_documents")
        self.assertEqual(get_generated_exports_root(), storage_root / "exports")
        self.assertEqual(get_generated_screenshots_root(), storage_root / "screenshots")

    def test_generated_paths_are_outside_tracked_source_folders(self):
        paths = (
            get_generated_documents_root(),
            get_generated_exports_root(),
            get_generated_screenshots_root(),
        )
        base_dir = Path(settings.BASE_DIR).resolve()
        for path in paths:
            relative = path.resolve().relative_to(base_dir).as_posix()
            for prefix in FORBIDDEN_SOURCE_PREFIXES:
                self.assertFalse(
                    relative == prefix or relative.startswith(f"{prefix}/"),
                    msg=f"{relative} must not live under {prefix}",
                )

    def test_application_document_folder_structure(self):
        folder = get_application_document_folder(17, "cover_letter")
        expected_suffix = "generated_documents/application_documents/application_17/cover_letter"
        self.assertTrue(folder.as_posix().endswith(expected_suffix))

    def test_application_document_folder_rejects_invalid_id(self):
        with self.assertRaises(ValueError):
            get_application_document_folder(0, "cv")


class SafeGeneratedFilenameTests(SimpleTestCase):
    def test_sanitises_unsafe_characters(self):
        filename = build_safe_generated_filename("Acme Corp | Data Analyst", "docx")
        self.assertEqual(filename, "Acme_Corp_Data_Analyst.docx")

    def test_rejects_path_segments_in_filename(self):
        with self.assertRaises(ValueError):
            build_safe_generated_filename("../escape", "pdf")


class GeneratedFolderSafetyTests(SimpleTestCase):
    def test_ensure_generated_folder_rejects_paths_outside_root(self):
        with temporary_generated_storage():
            outside = Path(settings.BASE_DIR) / "apps" / "escape"
            with self.assertRaises(ValueError):
                ensure_generated_folder(outside)

    def test_assert_generated_path_is_safe_rejects_forbidden_prefixes(self):
        forbidden = Path(settings.BASE_DIR) / "templates" / "generated.docx"
        with self.assertRaises(ValueError):
            assert_generated_path_is_safe(forbidden)


class WriteGeneratedDocumentTests(SimpleTestCase):
    def test_write_generated_document_bytes_uses_storage_tree(self):
        with temporary_generated_storage() as (_storage_root, generated_root):
            destination = write_generated_document_bytes(
                application_id=9,
                document_kind="cv",
                filename="Acme Corp CV.docx",
                content=b"docx-bytes",
            )
            self.assertTrue(destination.is_file())
            self.assertEqual(destination.read_bytes(), b"docx-bytes")
            self.assertTrue(
                destination.as_posix().startswith(generated_root.as_posix()),
            )
            for prefix in FORBIDDEN_SOURCE_PREFIXES:
                self.assertNotIn(prefix, destination.relative_to(settings.BASE_DIR).as_posix())


class GitignoreGeneratedStorageTests(SimpleTestCase):
    def test_gitignore_excludes_runtime_generated_paths(self):
        gitignore = (Path(settings.BASE_DIR) / ".gitignore").read_text(encoding="utf-8")
        required_patterns = (
            "storage/",
            "media/generated_documents/",
            "data/master_cv/",
            "storage/**/*.docx",
            "storage/**/*.pdf",
            "media/generated_documents/**/*.docx",
            "media/generated_documents/**/*.pdf",
        )
        for pattern in required_patterns:
            self.assertIn(pattern, gitignore)

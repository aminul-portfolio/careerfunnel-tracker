from __future__ import annotations

import zipfile
from io import BytesIO

from django.contrib.auth.models import User
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from apps.ai_agents.cover_letter_adjustment import apply_cover_letter_recommended_fixes
from apps.ai_agents.services import check_cover_letter_quality
from apps.applications.file_storage import build_professional_cover_letter_download_filename
from apps.applications.master_cv import (
    COVER_LETTER_BODY_MISSING_MESSAGE,
    COVER_LETTER_CONTACT_LINE,
    MASTER_CV_HEADLINE,
    build_clean_cover_letter_body,
    build_structured_cover_letter,
    clean_repeated_cover_letter_phrases,
    extract_cover_letter_body_for_export,
    validate_cover_letter_export_body,
)
from apps.applications.professional_exports import (
    CL_MARGIN_TOP,
    count_pdf_pages,
    render_cover_letter_bytes_from_fields,
)


class CoverLetterAdjustmentContentTests(SimpleTestCase):
    def test_recommended_fixes_are_not_appended_after_sign_off(self):
        draft = (
            "Dear Howden,\n\n"
            "I am applying for the Junior Data Analyst role.\n\n"
            "Kind regards,\n"
            "Aminul Islam"
        )
        result = apply_cover_letter_recommended_fixes(
            company_name="Howden",
            job_title="Junior Data Analyst",
            job_description="KPI dashboard reporting stakeholder analysis",
            cover_letter=draft,
        )
        lowered = result.body.lower()
        self.assertNotIn("kind regards", lowered)
        self.assertNotIn("aminul islam", lowered)
        self.assertIn("howden", lowered)
        self.assertIn("junior data analyst", lowered)

    def test_adjusted_body_contains_single_integrated_opening(self):
        draft = "Dear Team,\n\nI am applying for this opportunity."
        result = apply_cover_letter_recommended_fixes(
            company_name="Monzo",
            job_title="Data Analyst",
            job_description="Python SQL reporting",
            cover_letter=draft,
        )
        self.assertIn("Monzo", result.body)
        self.assertIn("Data Analyst", result.body)
        self.assertNotIn("Quality Score", result.body)
        self.assertNotIn("Best Fix", result.body)


class AdjustedCoverLetterExportTests(SimpleTestCase):
    def setUp(self):
        draft = (
            "Dear Howden,\n\n"
            "I am applying for the Junior Data Analyst role.\n\n"
            "Kind regards,\n"
            "Aminul Islam"
        )
        self.adjusted = apply_cover_letter_recommended_fixes(
            company_name="Howden",
            job_title="Junior Data Analyst",
            job_description="KPI dashboard reporting stakeholder analysis",
            cover_letter=draft,
        )
        self.company = "Howden"
        self.role = "Junior Data Analyst"

    def _docx_xml(self, docx_bytes: bytes) -> str:
        with zipfile.ZipFile(BytesIO(docx_bytes)) as archive:
            return archive.read("word/document.xml").decode("utf-8")

    def test_single_newline_draft_preserves_body_in_export(self):
        draft = (
            "Dear Howden,\n"
            "I am writing to express my interest in the Junior Data Analyst role at Howden.\n"
            "My background combines financial services operations.\n"
            "Kind regards,\n"
            "Aminul Islam"
        )
        adjusted = apply_cover_letter_recommended_fixes(
            company_name="Howden",
            job_title="Junior Data Analyst",
            job_description="KPI dashboard reporting",
            cover_letter=draft,
        )
        body = extract_cover_letter_body_for_export(
            adjusted.body,
            company_name="Howden",
            job_title="Junior Data Analyst",
        )
        self.assertIn("I am writing to express my interest", body)
        pdf_bytes = render_cover_letter_bytes_from_fields(
            company_name="Howden",
            job_title="Junior Data Analyst",
            body=body,
            file_format="pdf",
        )
        self.assertIn(b"I am writing to express my interest", pdf_bytes)

    def test_full_structured_text_still_exports_body_paragraphs(self):
        full_text = (
            "Aminul Islam\n"
            f"{COVER_LETTER_CONTACT_LINE}\n"
            "Hiring Team\n"
            "Howden\n"
            "Junior Data Analyst\n"
            "Dear Hiring Team,\n\n"
            "I am writing to express my interest in the Junior Data Analyst role at Howden.\n\n"
            "My background combines financial services operations.\n\n"
            "Kind regards,\n"
            "Aminul Islam"
        )
        body = extract_cover_letter_body_for_export(
            full_text,
            company_name="Howden",
            job_title="Junior Data Analyst",
        )
        self.assertIn("I am writing to express my interest", body)
        self.assertIn("My background combines", body)

    def test_blank_body_export_is_blocked(self):
        self.assertEqual(
            validate_cover_letter_export_body(""),
            COVER_LETTER_BODY_MISSING_MESSAGE,
        )
        self.assertEqual(
            validate_cover_letter_export_body("Too short."),
            COVER_LETTER_BODY_MISSING_MESSAGE,
        )

    def test_adjusted_docx_uses_professional_layout(self):
        export_body = extract_cover_letter_body_for_export(
            self.adjusted.body,
            company_name=self.company,
            job_title=self.role,
        )
        docx_bytes = render_cover_letter_bytes_from_fields(
            company_name=self.company,
            job_title=self.role,
            body=export_body,
            file_format="docx",
        )
        self.assertTrue(docx_bytes.startswith(b"PK"))
        document_xml = self._docx_xml(docx_bytes)
        self.assertIn("Aminul Islam", document_xml)
        self.assertIn("Hiring Team", document_xml)
        self.assertIn("Howden", document_xml)
        self.assertIn("Junior Data Analyst", document_xml)
        self.assertIn("Dear Hiring Team", document_xml)
        self.assertIn("Kind regards", document_xml)
        self.assertIn(COVER_LETTER_CONTACT_LINE.replace("&", "&amp;"), document_xml)
        self.assertIn(f'w:top="{CL_MARGIN_TOP}"', document_xml)
        self.assertIn("I am writing to express my interest", document_xml)
        self.assertIn("Junior Data Analyst role", document_xml)

    def test_adjusted_pdf_uses_professional_layout(self):
        export_body = extract_cover_letter_body_for_export(
            self.adjusted.body,
            company_name=self.company,
            job_title=self.role,
        )
        pdf_bytes = render_cover_letter_bytes_from_fields(
            company_name=self.company,
            job_title=self.role,
            body=export_body,
            file_format="pdf",
        )
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))
        self.assertIn(b"Dear Hiring Team", pdf_bytes)
        self.assertIn(b"Howden", pdf_bytes)
        self.assertIn(b"I am writing to express my interest", pdf_bytes)
        self.assertEqual(count_pdf_pages(pdf_bytes), 1)

    def test_adjusted_export_excludes_internal_notes(self):
        export_body = extract_cover_letter_body_for_export(
            self.adjusted.body,
            company_name=self.company,
            job_title=self.role,
        )
        docx_bytes = render_cover_letter_bytes_from_fields(
            company_name=self.company,
            job_title=self.role,
            body=export_body,
            file_format="docx",
        )
        document_xml = self._docx_xml(docx_bytes)
        for excluded in (
            "Review before use",
            "Quality Score",
            "Best Fix",
            "Recommended Fixes",
            "Claim-safety notes",
            "Weaknesses",
            "Strengths",
        ):
            self.assertNotIn(excluded, document_xml)

    def test_adjusted_export_has_one_sign_off_block(self):
        export_body = extract_cover_letter_body_for_export(
            self.adjusted.body,
            company_name=self.company,
            job_title=self.role,
        )
        structured = build_structured_cover_letter(
            company_name=self.company,
            job_title=self.role,
            body=export_body,
        )
        closing_lines = [
            block.text for block in structured.blocks if block.kind == "closing_line"
        ]
        closing_names = [
            block.text for block in structured.blocks if block.kind == "closing_name"
        ]
        self.assertEqual(closing_lines, ["Kind regards,"])
        self.assertEqual(closing_names, ["Aminul Islam"])

    def test_professional_filename_is_preserved(self):
        filename = build_professional_cover_letter_download_filename(
            self.company,
            self.role,
            "pdf",
        )
        self.assertTrue(filename.startswith("Aminul_Islam_Cover_Letter_Howden_"))
        self.assertIn("Junior_Data_Analyst", filename)
        self.assertTrue(filename.endswith(".pdf"))


class CoverLetterDuplicateCleanupTests(SimpleTestCase):
    HOWDEN_FULL_LETTER = (
        "Aminul Islam\n"
        f"{MASTER_CV_HEADLINE}\n"
        f"{COVER_LETTER_CONTACT_LINE}\n"
        "Hiring Team\n"
        "Howden\n"
        "Junior Data Analyst\n"
        "Dear Hiring Team,\n\n"
        "I am writing to express my interest in the Junior Data Analyst role at Howden.\n\n"
        "My background combines financial services operations with Python and SQL reporting.\n\n"
        "Kind regards,\n"
        "Aminul Islam"
    )

    def test_phrase_cleanup_fixes_known_duplicates(self):
        self.assertEqual(
            clean_repeated_cover_letter_phrases("for the this data analytics role role"),
            "for this data analytics role",
        )
        self.assertEqual(clean_repeated_cover_letter_phrases("the this role"), "this role")

    def test_extract_removes_structural_lines_from_full_draft(self):
        body = extract_cover_letter_body_for_export(
            self.HOWDEN_FULL_LETTER,
            company_name="Howden",
            job_title="Junior Data Analyst",
        )
        self.assertIn("I am writing to express my interest", body)
        self.assertIn("My background combines", body)
        self.assertNotIn("Dear Hiring Team", body)
        self.assertNotIn("Kind regards", body)
        self.assertNotIn("Hiring Team", body)
        self.assertNotIn(COVER_LETTER_CONTACT_LINE, body)

    def test_export_has_single_header_recipient_greeting_and_sign_off(self):
        adjusted = apply_cover_letter_recommended_fixes(
            company_name="Howden",
            job_title="Junior Data Analyst",
            job_description="KPI dashboard reporting stakeholder analysis",
            cover_letter=self.HOWDEN_FULL_LETTER,
        )
        export_body = extract_cover_letter_body_for_export(
            adjusted.body,
            company_name="Howden",
            job_title="Junior Data Analyst",
        )
        pdf_bytes = render_cover_letter_bytes_from_fields(
            company_name="Howden",
            job_title="Junior Data Analyst",
            body=export_body,
            file_format="pdf",
        )
        docx_bytes = render_cover_letter_bytes_from_fields(
            company_name="Howden",
            job_title="Junior Data Analyst",
            body=export_body,
            file_format="docx",
        )
        pdf_text = pdf_bytes.decode("latin-1", errors="ignore")
        docx_xml = self._docx_xml(docx_bytes)

        self.assertTrue(pdf_bytes.startswith(b"%PDF"))
        self.assertTrue(docx_bytes.startswith(b"PK"))
        self.assertEqual(pdf_text.lower().count("dear hiring team"), 1)
        self.assertEqual(pdf_text.lower().count("kind regards"), 1)
        self.assertEqual(docx_xml.lower().count("dear hiring team"), 1)
        self.assertEqual(docx_xml.lower().count("kind regards"), 1)
        self.assertNotIn("for the this", pdf_text.lower())
        self.assertNotIn("role role", pdf_text.lower())
        self.assertNotIn("for the this", docx_xml.lower())
        self.assertNotIn("role role", docx_xml.lower())

    def _docx_xml(self, docx_bytes: bytes) -> str:
        with zipfile.ZipFile(BytesIO(docx_bytes)) as archive:
            return archive.read("word/document.xml").decode("utf-8")

    def test_candidate_name_not_duplicated_in_body(self):
        export_body = extract_cover_letter_body_for_export(
            self.HOWDEN_FULL_LETTER,
            company_name="Howden",
            job_title="Junior Data Analyst",
        )
        structured = build_structured_cover_letter(
            company_name="Howden",
            job_title="Junior Data Analyst",
            body=export_body,
        )
        name_blocks = [block.text for block in structured.blocks if block.kind == "name"]
        paragraph_blocks = [
            block.text for block in structured.blocks if block.kind == "paragraph"
        ]
        self.assertEqual(name_blocks, ["Aminul Islam"])
        for paragraph in paragraph_blocks:
            self.assertNotEqual(paragraph.strip(), "Aminul Islam")

    def test_role_alignment_sentence_avoids_role_role(self):
        result = apply_cover_letter_recommended_fixes(
            company_name="Howden",
            job_title="Junior Data Analyst",
            job_description="Python SQL KPI reporting",
            cover_letter="Dear Team,\n\nI want to contribute to your analytics team.",
        )
        self.assertNotIn("role role", result.body.lower())
        self.assertNotIn("for the this", result.body.lower())
        self.assertNotIn("i am applying for this data analytics role", result.body.lower())
        self.assertIn("Junior Data Analyst", result.body)

    def test_adjusted_body_does_not_prepend_fix_paragraphs_above_original(self):
        result = apply_cover_letter_recommended_fixes(
            company_name="Howden",
            job_title="Junior Data Analyst",
            job_description="KPI dashboard reporting stakeholder analysis",
            cover_letter=self.HOWDEN_FULL_LETTER,
        )
        paragraphs = [part.strip() for part in result.body.split("\n\n") if part.strip()]
        self.assertGreaterEqual(len(paragraphs), 2)
        self.assertTrue(
            paragraphs[0].lower().startswith("i am writing to express my interest"),
            paragraphs,
        )
        self.assertNotEqual(paragraphs[0].lower(), "howden")
        self.assertNotEqual(paragraphs[0].lower(), "junior data analyst")
        self.assertNotIn(
            "i am applying for this data analytics role",
            result.body.lower(),
        )

    def test_standalone_company_role_lines_not_in_export_body(self):
        adjusted = apply_cover_letter_recommended_fixes(
            company_name="Howden",
            job_title="Junior Data Analyst",
            job_description="KPI dashboard reporting",
            cover_letter=self.HOWDEN_FULL_LETTER,
        )
        export_body = extract_cover_letter_body_for_export(
            adjusted.body,
            company_name="Howden",
            job_title="Junior Data Analyst",
        )
        for paragraph in export_body.split("\n\n"):
            stripped = paragraph.strip()
            self.assertNotEqual(stripped, "Howden")
            self.assertNotEqual(stripped, "Junior Data Analyst")
        self.assertIn("role at Howden", export_body)

    def test_build_clean_cover_letter_body_strips_structure(self):
        body = build_clean_cover_letter_body(
            self.HOWDEN_FULL_LETTER,
            company_name="Howden",
            job_title="Junior Data Analyst",
        )
        self.assertNotIn("Dear Hiring Team", body)
        self.assertNotIn("Hiring Team", body)
        self.assertIn("I am writing to express my interest", body)

    def test_export_recipient_block_precedes_greeting_and_body(self):
        adjusted = apply_cover_letter_recommended_fixes(
            company_name="Howden",
            job_title="Junior Data Analyst",
            job_description="KPI dashboard reporting stakeholder analysis",
            cover_letter=self.HOWDEN_FULL_LETTER,
        )
        structured = build_structured_cover_letter(
            company_name="Howden",
            job_title="Junior Data Analyst",
            body=adjusted.body,
        )
        kinds = [block.kind for block in structured.blocks]
        salutation_index = kinds.index("salutation")
        recipient_indices = [index for index, kind in enumerate(kinds) if kind == "recipient"]
        first_paragraph_index = kinds.index("paragraph")
        self.assertTrue(all(index < salutation_index for index in recipient_indices))
        self.assertGreater(first_paragraph_index, salutation_index)
        first_paragraph = next(
            block.text for block in structured.blocks if block.kind == "paragraph"
        )
        self.assertTrue(first_paragraph.lower().startswith("i am writing to express my interest"))
        self.assertNotEqual(first_paragraph.strip(), "Howden")
        self.assertFalse(first_paragraph.lower().startswith("junior data analyst."))

    def test_export_block_order_company_and_role_before_greeting(self):
        adjusted = apply_cover_letter_recommended_fixes(
            company_name="Howden",
            job_title="Junior Data Analyst",
            job_description="KPI dashboard reporting stakeholder analysis",
            cover_letter=(
                "Dear Hiring Team,\n\n"
                "Howden\n"
                "Junior Data Analyst\n\n"
                "I am writing to express my interest in the Junior Data Analyst role at Howden.\n\n"
                "My background combines financial services operations.\n\n"
                "Kind regards,\n"
                "Aminul Islam"
            ),
        )
        structured = build_structured_cover_letter(
            company_name="Howden",
            job_title="Junior Data Analyst",
            body=adjusted.body,
        )
        kinds = [block.kind for block in structured.blocks]
        texts = [block.text for block in structured.blocks]
        salutation_index = kinds.index("salutation")
        company_index = texts.index("Howden")
        role_index = texts.index("Junior Data Analyst")
        first_paragraph_index = kinds.index("paragraph")
        self.assertLess(company_index, salutation_index)
        self.assertLess(role_index, salutation_index)
        self.assertGreater(first_paragraph_index, salutation_index)
        pdf_bytes = render_cover_letter_bytes_from_fields(
            company_name="Howden",
            job_title="Junior Data Analyst",
            body=adjusted.body,
            file_format="pdf",
        )
        docx_bytes = render_cover_letter_bytes_from_fields(
            company_name="Howden",
            job_title="Junior Data Analyst",
            body=adjusted.body,
            file_format="docx",
        )
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))
        self.assertTrue(docx_bytes.startswith(b"PK"))
        pdf_text = pdf_bytes.decode("latin-1", errors="ignore")
        self.assertLess(pdf_text.find("Howden"), pdf_text.find("Dear Hiring Team"))
        self.assertLess(pdf_text.find("Junior Data Analyst"), pdf_text.find("Dear Hiring Team"))
        self.assertNotIn("My background. I am", pdf_text)
        self.assertNotIn("My background. I am", self._docx_xml(docx_bytes))

    def test_standalone_role_line_merged_into_opening_not_separate_paragraph(self):
        draft = (
            "Dear Hiring Team,\n\n"
            "Howden\n"
            "Junior Data Analyst\n\n"
            "I am writing to express my interest in the Junior Data Analyst role at Howden.\n\n"
            "Kind regards,\n"
            "Aminul Islam"
        )
        result = apply_cover_letter_recommended_fixes(
            company_name="Howden",
            job_title="Junior Data Analyst",
            job_description="KPI reporting",
            cover_letter=draft,
        )
        paragraphs = [part.strip() for part in result.body.split("\n\n") if part.strip()]
        self.assertTrue(paragraphs[0].lower().startswith("i am writing to express my interest"))
        self.assertNotIn("junior data analyst. i can connect", result.body.lower())
        for paragraph in paragraphs:
            self.assertNotEqual(paragraph.strip(), "Howden")
            self.assertNotEqual(paragraph.strip(), "Junior Data Analyst")


class AdjustedCoverLetterViewIntegrationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="cl-export", password="StrongPass12345")
        self.url = reverse("ai_agents:cover_letter_quality_checker")
        self.client.login(username="cl-export", password="StrongPass12345")
        self.draft = (
            "Dear Howden,\n\nI am applying for the Junior Data Analyst role. "
            "BakeOps Intelligence shows KPI reporting experience.\n\n"
            "Kind regards,\nAminul Islam"
        )
        self.form_payload = {
            "company_name": "Howden",
            "job_title": "Junior Data Analyst",
            "job_description": "KPI reporting",
            "cover_letter": self.draft,
        }

    def test_apply_recommended_fixes_returns_adjusted_preview(self):
        response = self.client.post(
            self.url,
            {**self.form_payload, "action": "apply_recommended_fixes"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Adjusted cover letter preview")
        self.assertContains(response, "Howden")
        self.assertContains(response, "Junior Data Analyst")
        self.assertContains(response, "BakeOps Intelligence")
        self.assertContains(response, "Manual review required before use.")
        self.assertContains(response, "No external AI/API generation.")
        self.assertContains(response, "No automatic submission.")

    def test_page_copy_avoids_auto_submit_and_external_ai_claims(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Manual review required")
        self.assertContains(response, "No external AI/API generation")
        self.assertNotContains(response, "auto-submit")
        self.assertNotContains(response, "auto apply")
        self.assertNotContains(response, "OAuth")
        self.assertNotContains(response, "Gmail")
        self.assertNotContains(response, "Outlook")

    def test_download_adjusted_docx_uses_professional_renderer(self):
        quality = check_cover_letter_quality(
            company_name="Howden",
            job_title="Junior Data Analyst",
            job_description="KPI reporting",
            cover_letter=self.draft,
        )
        adjusted = apply_cover_letter_recommended_fixes(
            company_name="Howden",
            job_title="Junior Data Analyst",
            job_description="KPI reporting",
            cover_letter=self.draft,
            quality_result=quality,
        )
        response = self.client.post(
            self.url,
            {
                "action": "download_adjusted_docx",
                "company_name": "Howden",
                "job_title": "Junior Data Analyst",
                "adjusted_cover_letter": adjusted.body,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.content.startswith(b"PK"))
        with zipfile.ZipFile(BytesIO(response.content)) as docx:
            document_xml = docx.read("word/document.xml").decode("utf-8")
        self.assertIn("Aminul Islam", document_xml)
        self.assertIn("Dear Hiring Team", document_xml)
        self.assertIn("Howden", document_xml)
        self.assertIn("BakeOps Intelligence", document_xml)
        self.assertNotIn("Quality Score", document_xml)

    def test_download_adjusted_pdf_uses_professional_renderer(self):
        adjusted = apply_cover_letter_recommended_fixes(
            company_name="Howden",
            job_title="Junior Data Analyst",
            job_description="KPI reporting",
            cover_letter=self.draft,
        )
        response = self.client.post(
            self.url,
            {
                "action": "download_adjusted_pdf",
                "company_name": "Howden",
                "job_title": "Junior Data Analyst",
                "adjusted_cover_letter": adjusted.body,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.content.startswith(b"%PDF"))
        self.assertIn(b"Dear Hiring Team", response.content)
        self.assertIn(b"Howden", response.content)
        self.assertIn(b"BakeOps Intelligence", response.content)
        disposition = response["Content-Disposition"]
        self.assertIn("Aminul_Islam_Cover_Letter_Howden_", disposition)

    def test_download_blocks_blank_body_with_message(self):
        response = self.client.post(
            self.url,
            {
                "action": "download_adjusted_pdf",
                "company_name": "Howden",
                "job_title": "Junior Data Analyst",
                "adjusted_cover_letter": "Kind regards,\nAminul Islam",
            },
        )
        self.assertEqual(response.status_code, 302)
        follow = self.client.get(response.url)
        self.assertContains(follow, COVER_LETTER_BODY_MISSING_MESSAGE)

import zipfile
from datetime import date
from io import BytesIO
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import SimpleTestCase, TestCase

from apps.applications.choices import DocumentSource, DocumentStatus, DocumentType
from apps.applications.cv_template_exports import (
    STRUCTURED_RENDERER_FALLBACK,
    render_tailored_cv_bytes,
)
from apps.applications.master_cv import (
    ADDITIONAL_INFORMATION_LINES,
    BASELINE_PROFILE_PARAGRAPH,
    COVER_LETTER_CONTACT_LINE,
    DEFAULT_PROJECT_ORDER,
    EDUCATION_ENTRIES,
    EXPERIENCE_AREA_MANAGER_BULLETS,
    EXPERIENCE_EARLIER_BULLETS,
    EXPERIENCE_MONEY_TRANSFER_FX_BULLETS,
    MASTER_CV_CONTACT_LINE,
    MASTER_CV_CONTACT_LINES,
    PORTFOLIO_PROJECT_BULLETS,
    PORTFOLIO_PROJECT_TAGLINES,
    TECHNICAL_SKILL_GROUPS,
    build_structured_cover_letter,
    build_structured_master_cv,
    build_tailored_portfolio_bullets,
    canonicalize_master_cv_structured,
    parse_cv_plain_text_to_structured,
    structured_document_to_plain_text,
)
from apps.applications.models import ApplicationDocument, JobApplication
from apps.applications.professional_exports import (
    CL_MARGIN_TOP,
    count_pdf_pages,
    render_application_cv_bytes,
    render_structured_document_docx,
    render_structured_document_pdf,
)
from apps.applications.test_master_cv_fixtures import (
    TEMPLATE_MARGIN_TOP,
    build_test_master_cv_template_docx,
)
from apps.job_intelligence.draft_documents import (
    build_application_document_drafts,
    build_clean_cover_letter_content,
    build_complete_cv_content,
)


class MasterCvBaselineTests(SimpleTestCase):
    def test_baseline_contact_line_matches_approved_master_cv(self):
        self.assertIn("Purley, London", MASTER_CV_CONTACT_LINE)
        self.assertIn("07443 360827", MASTER_CV_CONTACT_LINE)
        self.assertIn("aminulislamkhan.tech@gmail.com", MASTER_CV_CONTACT_LINE)
        self.assertIn("linkedin.com/in/aminul-islam-a71a871a2", MASTER_CV_CONTACT_LINE)
        self.assertIn("UK work authorisation: ILR", MASTER_CV_CONTACT_LINE)

    def test_baseline_profile_includes_operational_context(self):
        self.assertIn("800 agents", BASELINE_PROFILE_PARAGRAPH)
        self.assertIn("GBP 30,000", BASELINE_PROFILE_PARAGRAPH)
        self.assertIn("LCCA", BASELINE_PROFILE_PARAGRAPH)

    def test_baseline_technical_skill_groups_match_approved_structure(self):
        self.assertEqual(
            tuple(TECHNICAL_SKILL_GROUPS.keys()),
            (
                "Analysis & reporting",
                "Data platforms & engineering",
                "BI, reporting & delivery",
                "Domain",
            ),
        )
        self.assertIn("Power Query", TECHNICAL_SKILL_GROUPS["Analysis & reporting"])
        self.assertIn("Git/GitHub", TECHNICAL_SKILL_GROUPS["Data platforms & engineering"])

    def test_baseline_experience_bullets_match_approved_master_cv(self):
        self.assertEqual(len(EXPERIENCE_MONEY_TRANSFER_FX_BULLETS), 4)
        self.assertIn("Western Union and Ria", EXPERIENCE_MONEY_TRANSFER_FX_BULLETS[1])
        self.assertIn("GBP 30,000", EXPERIENCE_MONEY_TRANSFER_FX_BULLETS[2])
        self.assertIn("800 agents", EXPERIENCE_AREA_MANAGER_BULLETS[0])
        self.assertIn("Pied a Terre", EXPERIENCE_EARLIER_BULLETS[0])

    def test_baseline_education_entries_match_approved_master_cv(self):
        self.assertEqual(len(EDUCATION_ENTRIES), 5)
        self.assertIn("LCCA", EDUCATION_ENTRIES[0])
        self.assertIn("University of Greenwich", EDUCATION_ENTRIES[1])
        self.assertIn("Nelson College London", EDUCATION_ENTRIES[2])

    def test_baseline_project_order_and_careerfunnel_wording(self):
        self.assertEqual(
            DEFAULT_PROJECT_ORDER,
            (
                "BakeOps Intelligence",
                "CareerFunnel Tracker",
                "TradeIntel 360",
                "DataBridge Market API / MarketVista Dashboard",
            ),
        )
        careerfunnel = PORTFOLIO_PROJECT_BULLETS["CareerFunnel Tracker"]
        self.assertIn("skill-gap tracking", careerfunnel[1])
        self.assertIn("Application Document Pack workflow", careerfunnel[1])
        self.assertIn("771 automated tests", careerfunnel[2])
        self.assertNotIn("Skill Intelligence", " ".join(careerfunnel))
        self.assertNotIn("828 automated tests", " ".join(careerfunnel))
        self.assertNotIn("screenshot evidence", " ".join(careerfunnel))

    def test_baseline_additional_information_matches_approved_master_cv(self):
        joined = " ".join(ADDITIONAL_INFORMATION_LINES)
        self.assertIn("Self-directed learning", joined)
        self.assertIn("Bengali, native", joined)
        self.assertIn("FTMO-funded-trader", joined)

    def test_default_structured_cv_uses_baseline_profile_without_angle(self):
        plain = structured_document_to_plain_text(build_structured_master_cv())
        self.assertIn(BASELINE_PROFILE_PARAGRAPH, plain)
        self.assertIn("Analysis & reporting: Python", plain)
        self.assertIn(PORTFOLIO_PROJECT_TAGLINES["BakeOps Intelligence"], plain)
        self.assertIn(PORTFOLIO_PROJECT_TAGLINES["CareerFunnel Tracker"], plain)

    def test_tailored_profile_integrates_role_context_without_appendix_sentence(self):
        plain = structured_document_to_plain_text(
            build_structured_master_cv(
                profile_angle="BI analyst angle",
                skills_to_prioritise=("Python", "SQL", "Excel"),
            )
        )
        self.assertIn("BI-ready outputs", plain)
        self.assertIn("stakeholder-ready summaries", plain)
        self.assertNotIn("For this role, I emphasise", plain)
        self.assertNotIn("For FinTech-facing roles, I emphasise", plain)

    def test_tailored_portfolio_bullets_keep_approved_careerfunnel_wording(self):
        bullets = build_tailored_portfolio_bullets(
            skills_to_prioritise=("Python", "SQL"),
            role_text="Junior Data Analyst dashboard KPI reporting",
        )
        careerfunnel = bullets["CareerFunnel Tracker"]
        self.assertEqual(careerfunnel, PORTFOLIO_PROJECT_BULLETS["CareerFunnel Tracker"])
        self.assertNotIn("Role-relevant emphasis", " ".join(careerfunnel))


class ProfessionalCvExportTests(TestCase):
    def setUp(self):
        self.structured = build_structured_master_cv(
            profile_angle="BI analyst angle",
            skills_to_prioritise=("Python", "SQL", "Excel"),
        )

    def _docx_xml(self, docx_bytes: bytes) -> str:
        with zipfile.ZipFile(BytesIO(docx_bytes)) as archive:
            return archive.read("word/document.xml").decode("utf-8")

    def test_cv_docx_uses_master_template_when_available(self):
        with patch(
            "apps.applications.cv_template_exports.master_cv_files.read_master_cv_template_if_available",
            side_effect=lambda ext: build_test_master_cv_template_docx() if ext == "docx" else None,
        ):
            document_xml = self._docx_xml(render_tailored_cv_bytes(self.structured, "docx"))
        self.assertIn(f'w:top="{TEMPLATE_MARGIN_TOP}"', document_xml)
        self.assertIn("AMINUL ISLAM", document_xml)
        self.assertIn("771 automated tests", document_xml)
        self.assertNotIn("828 automated tests", document_xml)
        self.assertNotIn("Skill Intelligence", document_xml)
        self.assertIn("skill-gap tracking", document_xml)
        self.assertIn("PROFESSIONAL EXPERIENCE", document_xml)
        education_index = document_xml.index("EDUCATION")
        projects_index = document_xml.index("PORTFOLIO PROJECTS")
        self.assertLess(education_index, projects_index)

    def test_cv_docx_uses_structured_fallback_without_template(self):
        with patch(
            "apps.applications.cv_template_exports.master_cv_files.read_master_cv_template_if_available",
            return_value=None,
        ):
            document_xml = self._docx_xml(render_tailored_cv_bytes(self.structured, "docx"))
        self.assertIn(f'w:top="{620}"', document_xml)
        self.assertEqual(STRUCTURED_RENDERER_FALLBACK.split()[0], "Structured")

    def test_cv_docx_uses_heading_styles_and_master_section_order(self):
        with patch(
            "apps.applications.cv_template_exports.master_cv_files.read_master_cv_template_if_available",
            return_value=None,
        ):
            document_xml = self._docx_xml(render_structured_document_docx(self.structured))
        profile_index = document_xml.index("PROFILE")
        technical_index = document_xml.index("TECHNICAL SKILLS")
        experience_index = document_xml.index("PROFESSIONAL EXPERIENCE")
        education_index = document_xml.index("EDUCATION")
        projects_index = document_xml.index("PORTFOLIO PROJECTS")
        additional_index = document_xml.index("ADDITIONAL INFORMATION")
        self.assertLess(profile_index, technical_index)
        self.assertLess(technical_index, experience_index)
        self.assertLess(experience_index, education_index)
        self.assertLess(education_index, projects_index)
        self.assertLess(projects_index, additional_index)
        self.assertIn("<w:b/>", document_xml)
        self.assertIn("w:hanging=\"165\"", document_xml)
        self.assertIn(">-<", document_xml)
        self.assertIn(f'w:top="{620}"', document_xml)
        self.assertIn('w:line="250"', document_xml)
        self.assertIn("<w:br w:type=\"page\"/>", document_xml)
        self.assertNotIn("For this role, I emphasise", document_xml)

    def test_cv_docx_uses_two_centered_contact_lines(self):
        document_xml = self._docx_xml(render_structured_document_docx(self.structured))
        for contact_line in MASTER_CV_CONTACT_LINES:
            self.assertIn(contact_line.replace("&", "&amp;"), document_xml)

    def test_cv_pdf_compact_output_is_exactly_two_pages(self):
        pdf_bytes = render_structured_document_pdf(self.structured)
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))
        self.assertIn(b"PROFILE", pdf_bytes)
        self.assertIn(b"PORTFOLIO PROJECTS", pdf_bytes)
        self.assertEqual(count_pdf_pages(pdf_bytes), 2)
        self.assertNotIn(b"For this role, I emphasise", pdf_bytes)
        self.assertNotIn(b"Role-tailored emphasis", pdf_bytes)

    def test_cv_pdf_uses_ascii_bullets_and_safe_currency_symbols(self):
        pdf_bytes = render_structured_document_pdf(self.structured)
        pdf_text = pdf_bytes.decode("latin-1", errors="ignore")
        self.assertIn("GBP 30,000", pdf_text)
        self.assertNotIn("(?) Tj", pdf_text)
        self.assertNotIn("(? ", pdf_text)
        self.assertIn("(- ", pdf_text)

    def test_cv_export_includes_approved_contact_details_and_headline(self):
        document_xml = self._docx_xml(render_structured_document_docx(self.structured))
        self.assertIn("AMINUL ISLAM", document_xml)
        self.assertIn("07443 360827", document_xml)
        self.assertIn("aminulislamkhan.tech@gmail.com", document_xml)
        self.assertIn(
            "Data Analyst | BI Analyst | Python, SQL, Excel, Django | FX &amp; FinTech Operations",
            document_xml,
        )

    def test_cv_export_includes_approved_experience_and_careerfunnel_wording(self):
        document_xml = self._docx_xml(render_structured_document_docx(self.structured))
        self.assertIn("Western Union and Ria", document_xml)
        self.assertIn("800 agents", document_xml)
        self.assertIn("771 automated tests", document_xml)
        self.assertIn("Application Document Pack workflow", document_xml)
        self.assertIn("University of Greenwich", document_xml)
        self.assertNotIn("Skill Intelligence", document_xml)

    def test_canonicalize_master_cv_removes_header_blank_and_uses_standard_contact(self):
        plain = structured_document_to_plain_text(self.structured)
        parsed = parse_cv_plain_text_to_structured(plain)
        canonical = canonicalize_master_cv_structured(parsed)
        self.assertEqual(canonical.blocks[0].text, "AMINUL ISLAM")
        self.assertEqual(canonical.blocks[2].text, MASTER_CV_CONTACT_LINES[0])
        self.assertEqual(canonical.blocks[3].text, MASTER_CV_CONTACT_LINES[1])
        self.assertNotIn(
            "blank",
            [block.kind for block in canonical.blocks[:5]],
        )

    def test_saved_tailored_cv_export_matches_direct_master_layout(self):
        user = User.objects.create_user(username="cv-export", password="StrongPass12345")
        application = JobApplication.objects.create(
            user=user,
            company_name="Howden",
            job_title="Junior Data Analyst",
            date_applied=date(2026, 5, 10),
            required_skills="Python SQL Excel",
            job_description="Junior BI reporting role with KPI dashboards.",
        )
        drafts = build_application_document_drafts(application)
        saved_content = build_complete_cv_content(application, drafts)
        document = ApplicationDocument.objects.create(
            application=application,
            document_type=DocumentType.CV,
            name=drafts.cv_tailoring.recommended_cv_filename,
            status=DocumentStatus.DRAFT,
            source=DocumentSource.JOB_ANALYZER,
            content=saved_content,
            cv_baseline_name=drafts.cv_tailoring.master_cv_baseline,
        )
        cv_structured = build_structured_master_cv(
            profile_angle="BI analyst angle",
            skills_to_prioritise=("Python", "SQL", "Excel"),
        )
        with patch(
            "apps.applications.cv_template_exports.master_cv_files.read_master_cv_template_if_available",
            return_value=None,
        ):
            direct_pdf = render_structured_document_pdf(cv_structured)
            saved_pdf = render_application_cv_bytes(document, "pdf")
            direct_docx = self._docx_xml(render_structured_document_docx(cv_structured))
            saved_docx = self._docx_xml(render_application_cv_bytes(document, "docx"))
        self.assertEqual(count_pdf_pages(saved_pdf), 2)
        self.assertEqual(count_pdf_pages(direct_pdf), 2)
        for marker in (
            'w:top="620"',
            'w:line="250"',
            "<w:br w:type=\"page\"/>",
            "PORTFOLIO PROJECTS",
            "771 automated tests",
        ):
            self.assertIn(marker, saved_docx)
            self.assertIn(marker, direct_docx)
        self.assertIn(b"GBP 30,000", saved_pdf)
        self.assertNotIn(b"(? ", saved_pdf)
        self.assertNotIn("Tailoring notes", saved_docx)
        self.assertNotIn("Claim-safety notes", saved_docx)
        self.assertNotIn("Quick call notes", saved_docx)


class CoverLetterExportTests(TestCase):
    def setUp(self):
        self.structured = build_structured_cover_letter(
            company_name="Howden",
            job_title="Junior Data Analyst",
            body=(
                "I am writing to express my interest in the Junior Data Analyst role at Howden. "
                "My background combines financial services operations, FX and remittance "
                "workflows, reconciliation discipline, KPI reporting, and Python/Django "
                "analytics portfolio work.\n\n"
                "In my recent role as a Money Transfer & FX Specialist, I handled high-volume "
                "financial transactions, daily balancing, discrepancy review, customer "
                "verification, AML-aware workflows, and operational reporting.\n\n"
                "My portfolio includes BakeOps Intelligence and CareerFunnel Tracker with "
                "skill-gap tracking and 771 automated tests.\n\n"
                "I would welcome the opportunity to discuss how my operational finance "
                "background could support Howden's data and reporting work."
            ),
        )

    def _docx_xml(self, docx_bytes: bytes) -> str:
        with zipfile.ZipFile(BytesIO(docx_bytes)) as archive:
            return archive.read("word/document.xml").decode("utf-8")

    def test_cover_letter_docx_uses_master_cv_style_header(self):
        document_xml = self._docx_xml(render_structured_document_docx(self.structured))
        self.assertIn("Aminul Islam", document_xml)
        self.assertIn(
            "Data Analyst | BI Analyst | Python, SQL, Excel, Django | FX &amp; FinTech Operations",
            document_xml,
        )
        self.assertIn(COVER_LETTER_CONTACT_LINE.replace("&", "&amp;"), document_xml)
        self.assertIn(f'w:top="{CL_MARGIN_TOP}"', document_xml)

    def test_cover_letter_docx_header_is_left_aligned(self):
        document_xml = self._docx_xml(render_structured_document_docx(self.structured))
        self.assertNotIn('w:jc w:val="center"', document_xml)

    def test_cover_letter_docx_includes_recipient_salutation_and_closing(self):
        document_xml = self._docx_xml(render_structured_document_docx(self.structured))
        self.assertIn("Hiring Team", document_xml)
        self.assertIn("Howden", document_xml)
        self.assertIn("Junior Data Analyst", document_xml)
        self.assertIn("Dear Hiring Team", document_xml)
        self.assertIn("Kind regards", document_xml)
        self.assertIn(COVER_LETTER_CONTACT_LINE.replace("&", "&amp;"), document_xml)

    def test_cover_letter_export_is_employer_facing_only(self):
        document_xml = self._docx_xml(render_structured_document_docx(self.structured))
        self.assertIn("BakeOps Intelligence", document_xml)
        self.assertIn("CareerFunnel Tracker", document_xml)
        self.assertIn("771 automated tests", document_xml)
        self.assertIn("skill-gap tracking", document_xml)
        self.assertIn("financial services", document_xml.lower())
        self.assertIn("FX", document_xml)
        self.assertIn("reconciliation", document_xml.lower())
        for excluded in (
            "Review before use",
            "Draft/manual-review",
            "Tailoring notes",
            "Project evidence",
            "Claim-safety notes",
            "Quick call notes",
            "Document type",
            "Status",
            "Source",
            "Skill Intelligence",
            "828 automated tests",
        ):
            self.assertNotIn(excluded, document_xml)

    def test_cover_letter_pdf_is_single_page_employer_facing(self):
        pdf_bytes = render_structured_document_pdf(self.structured)
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))
        self.assertIn(b"Dear Hiring Team", pdf_bytes)
        self.assertIn(b"Howden", pdf_bytes)
        self.assertEqual(count_pdf_pages(pdf_bytes), 1)
        self.assertNotIn(b"Review before use", pdf_bytes)


class DocumentExportsAlignmentTests(TestCase):
    def _docx_xml(self, docx_bytes: bytes) -> str:
        with zipfile.ZipFile(BytesIO(docx_bytes)) as archive:
            return archive.read("word/document.xml").decode("utf-8")

    def setUp(self):
        self.user = User.objects.create_user(username="doc-export", password="StrongPass12345")
        self.application = JobApplication.objects.create(
            user=self.user,
            company_name="Howden",
            job_title="Junior Data Analyst",
            date_applied=date(2026, 5, 10),
            required_skills="Python SQL Excel",
            job_description="Junior BI reporting role with KPI dashboards.",
        )
        drafts = build_application_document_drafts(self.application)
        self.cv_document = ApplicationDocument.objects.create(
            application=self.application,
            document_type=DocumentType.CV,
            name=drafts.cv_tailoring.recommended_cv_filename,
            status=DocumentStatus.DRAFT,
            source=DocumentSource.JOB_ANALYZER,
            content=build_complete_cv_content(self.application, drafts),
            cv_baseline_name=drafts.cv_tailoring.master_cv_baseline,
        )
        self.cover_letter_document = ApplicationDocument.objects.create(
            application=self.application,
            document_type=DocumentType.COVER_LETTER,
            name="Aminul_Islam_Cover_Letter_Howden_Junior_Data_Analyst",
            status=DocumentStatus.DRAFT,
            source=DocumentSource.JOB_ANALYZER,
            content=build_clean_cover_letter_content(
                company_name=self.application.company_name,
                job_title=self.application.job_title,
                body=(
                    "I am writing to express my interest in the Junior Data Analyst "
                    "role at Howden. "
                    "My portfolio includes CareerFunnel Tracker with skill-gap tracking and "
                    "771 automated tests.\n\n"
                    "I would welcome the opportunity to discuss how my background could support "
                    "Howden's data and reporting work."
                ),
            ),
        )

    def test_application_document_docx_delegates_to_professional_renderer(self):
        from apps.applications.document_exports import render_application_document_docx

        with patch(
            "apps.applications.cv_template_exports.master_cv_files.read_master_cv_template_if_available",
            return_value=None,
        ):
            document_xml = self._docx_xml(render_application_document_docx(self.cv_document))
        self.assertIn("771 automated tests", document_xml)
        self.assertIn("GBP 30,000", document_xml)
        self.assertNotIn("828 automated tests", document_xml)
        self.assertNotIn("Tailoring notes", document_xml)

    def test_application_document_pdf_delegates_to_professional_renderer(self):
        from apps.applications.document_exports import render_application_document_pdf

        pdf_bytes = render_application_document_pdf(self.cover_letter_document)
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))
        self.assertIn(b"Dear Hiring Team", pdf_bytes)
        self.assertIn(b"Howden", pdf_bytes)
        self.assertIn(b"771 automated tests", pdf_bytes)
        self.assertNotIn(b"Review before use", pdf_bytes)
        self.assertNotIn(b"828 automated tests", pdf_bytes)

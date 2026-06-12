from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from django.conf import settings

from apps.applications.choices import DEFAULT_CV_BASELINE_NAME
from apps.job_intelligence.services import LOCKED_CV

MASTER_CV_BASENAME = DEFAULT_CV_BASELINE_NAME
MASTER_CV_DISPLAY_NAME = "AMINUL ISLAM"
MASTER_CV_HEADLINE = (
    "Data Analyst | BI Analyst | Python, SQL, Excel, Django | FX & FinTech Operations"
)
MASTER_CV_CONTACT_LINES = (
    "Purley, London | 07443 360827 | aminulislamkhan.tech@gmail.com",
    (
        "GitHub: github.com/aminul-portfolio | "
        "LinkedIn: linkedin.com/in/aminul-islam-a71a871a2 | "
        "UK work authorisation: ILR"
    ),
)
MASTER_CV_CONTACT_LINE = " | ".join(MASTER_CV_CONTACT_LINES)
COVER_LETTER_CONTACT_LINE = (
    "Purley, London | 07443 360827 | aminulislamkhan.tech@gmail.com | "
    "github.com/aminul-portfolio | linkedin.com/in/aminul-islam-a71a871a2 | "
    "UK work authorisation: ILR"
)

BASELINE_PROFILE_PORTFOLIO_SENTENCE = (
    "Developed a Python/Django analytics portfolio focused on data quality, KPI reporting, "
    "FinTech analytics, and reproducible methodology."
)

BASELINE_PROFILE_PARAGRAPH = (
    "Data Analyst candidate with 15 years of UK work experience spanning financial "
    "services, FX operations, reconciliation, KPI reporting, and technology platform "
    "support. Built an in-house multi-currency Excel reconciliation system managing "
    "daily cash volumes of around GBP 30,000 across remittance providers, FX positions, "
    "and audit workflows. Supported approximately 800 agents on a Python-based sales "
    "platform, producing stakeholder KPI reports and translating user issues into "
    "development priorities. "
    f"{BASELINE_PROFILE_PORTFOLIO_SENTENCE} "
    "BA (Hons) Business Management & Entrepreneurship in progress at LCCA; eligible "
    "to work in the UK without sponsorship."
)

DEFAULT_PROJECT_ORDER = (
    "BakeOps Intelligence",
    "CareerFunnel Tracker",
    "TradeIntel 360",
    "DataBridge Market API / MarketVista Dashboard",
)

PORTFOLIO_PROJECTS_INTRO = (
    "Self-built Python and Django data products. Full source and documentation "
    "available at github.com/aminul-portfolio."
)

PORTFOLIO_PROJECT_TAGLINES: dict[str, str] = {
    "BakeOps Intelligence": "BakeOps Intelligence - Django | Python | KPI dashboards | BI exports",
    "CareerFunnel Tracker": (
        "CareerFunnel Tracker - Django | Python | analytics workflow | test discipline"
    ),
    "TradeIntel 360": "TradeIntel 360 - Pandas | Plotly | Excel/PDF exports | Django",
    "DataBridge Market API / MarketVista Dashboard": (
        "DataBridge Market API / MarketVista Dashboard - Python | API ingestion | ETL | "
        "Django dashboards"
    ),
}

PORTFOLIO_PROJECT_BULLETS: dict[str, tuple[str, ...]] = {
    "BakeOps Intelligence": (
        "Operations analytics platform generating KPI dashboards, gold-layer metric "
        "snapshots, and BI-ready CSV exports from seeded bakery operational data.",
        "Surfaced a rank-inversion finding: the highest-revenue product ranked fourth on "
        "waste-adjusted margin, documented with reproducible methodology.",
        "Includes deterministic metric build pipeline, lineage documentation, "
        "reviewer-verifiable outputs, and 37 passing tests.",
    ),
    "CareerFunnel Tracker": (
        "Job-search analytics tracker with structured application records, funnel-stage "
        "metrics, source-performance reporting, and data-quality warnings.",
        "Includes a documented manual intake workflow with rule-based review, field audit, "
        "decision-evidence logging, skill-gap tracking, application readiness checks, and "
        "Application Document Pack workflow.",
        "Validated with 771 automated tests, Ruff checks, Django system checks, migration "
        "dry-run discipline, and documented sprint-based delivery.",
    ),
    "TradeIntel 360": (
        "Calculates 17 trading KPIs from session-driven CSV uploads with configurable "
        "Excel/PDF reporting and transparent Sharpe methodology documentation.",
        "Covers performance, expectancy, risk/reward, drawdown, and session-level trading "
        "analysis.",
        "Includes honest framing of trade-series Sharpe versus annualised institutional "
        "Sharpe in the documentation.",
    ),
    "DataBridge Market API / MarketVista Dashboard": (
        "Read-only market data ingestion and monitoring workflow using yfinance, ccxt, and "
        "Twelve Data, with run logging, normalised storage, and dashboard inspection layers.",
        "Demonstrates API ingestion, structured data handling, ETL-style thinking, "
        "watchlists, alert-style signals, and analyst-facing market visibility.",
    ),
}

TECHNICAL_SKILL_GROUPS: dict[str, tuple[str, ...]] = {
    "Analysis & reporting": (
        "Python",
        "Pandas",
        "NumPy",
        "SQL",
        "Excel",
        "Power Query",
        "DAX",
        "VBA",
        "Pivot Tables",
        "Plotly",
        "Matplotlib",
        "Chart.js",
    ),
    "Data platforms & engineering": (
        "Django",
        "Django ORM",
        "REST APIs",
        "CSV/Excel/JSON ingestion",
        "ETL workflows",
        "Streamlit",
        "Git/GitHub",
    ),
    "BI, reporting & delivery": (
        "Data analysis",
        "KPI dashboards",
        "data visualisation",
        "BI-ready CSV exports",
        "metric definitions",
        "data-quality checks",
        "lineage documentation",
    ),
    "Domain": (
        "Foreign exchange operations",
        "AML procedures",
        "multi-currency reconciliation",
        "operational reporting",
        "FinTech analytics",
    ),
}

EXPERIENCE_MONEY_TRANSFER_FX_TITLE = (
    "Money Transfer & FX Specialist - Acaelus Services Ltd, Croydon | May 2020 - October 2025"
)
EXPERIENCE_MONEY_TRANSFER_FX_BULLETS = (
    "Designed and built an in-house multi-currency Excel reconciliation system from scratch, "
    "covering currency stock tracking, FX buy/sell transactions, remittance-provider "
    "movements, daily balancing, and reporting, replacing manual processes and improving "
    "visibility for end-of-day controls.",
    "Delivered end-to-end remittance and FX services using Western Union and Ria workflows, "
    "serving approximately 200 customers and processing high-volume transactions with "
    "strong accuracy.",
    "Managed daily cash volumes of around GBP 30,000, maintaining disciplined controls across "
    "cash intake, customer payouts, balancing, and audit-ready cash handling.",
    "Performed daily and weekly reconciliations, discrepancy reviews, and end-of-day "
    "balancing; supported compliance through customer verification, AML controls, and "
    "accurate record keeping aligned with UK data protection requirements.",
)

EXPERIENCE_AREA_MANAGER_TITLE = (
    "Area Manager (Software Solutions) - Bliss Services Ltd, London | August 2016 - April 2020"
)
EXPERIENCE_AREA_MANAGER_BULLETS = (
    "Managed and supported a UK-wide network of approximately 800 agents on the company's "
    "Python-based sales platform, ensuring consistent service delivery, software adoption, "
    "and training quality across multiple territories.",
    "Produced monthly stakeholder KPI reports on agent activity, market trends, and "
    "operational risk, supporting platform adoption and process-improvement decisions "
    "across the agent network.",
    "Acted as the technical bridge between non-technical shopkeepers and the software "
    "development team, translating user issues into clear feedback so bugs, workflow "
    "problems, and platform improvements could be resolved efficiently.",
)

EXPERIENCE_EARLIER_TITLE = "Earlier Roles | July 2010 - July 2016"
EXPERIENCE_EARLIER_BULLETS = (
    "Commis Waiter, Pied a Terre, London, Michelin-starred restaurant, 2010-2014; Sandwich "
    "Artist, Subway Restaurants, London, 2014-2016. Detail-focused hospitality experience "
    "alongside continued self-directed technical study.",
)

EDUCATION_ENTRIES = (
    "BA (Hons) Business Management & Entrepreneurship - LCCA, London | September 2023 - "
    "present; final year expected September 2026.",
    "BA (Hons) Business Studies - University of Greenwich, London | 2012 - 2014.",
    "BTEC Level 5 HND Business - Nelson College London | 2011 - 2012.",
    "Advanced Diploma in Information Technology - London East Bank College, London | "
    "2009 - 2011; studied HTML, CSS, Java, IT theory, and web development fundamentals; "
    "course not completed due to financial circumstances.",
    "HSC and SSC - Bangladesh | HSC 2008 | SSC 2006; Mathematics, Computer Studies, and "
    "Sciences.",
)

ADDITIONAL_INFORMATION_LINES = (
    "Self-directed learning: Python, Python for Data Science and Machine Learning, Django, "
    "Excel Beginner to Advanced, Excel Macros & VBA, Power Query, DAX, and Pivot Tables.",
    "Languages: English, fluent; Bengali, native.",
    "Domain interests: Financial markets trading since 2016, including FTMO-funded-trader "
    "experience as FinTech domain context.",
    "Personal interests: Competitive badminton and tennis; organised a 28-team badminton "
    "tournament. Long-running interest in mathematics and problem-solving.",
)

DocumentBlockKind = Literal[
    "name",
    "headline",
    "contact",
    "recipient",
    "salutation",
    "closing_line",
    "closing_name",
    "section",
    "subheading",
    "paragraph",
    "bullet",
    "blank",
]


@dataclass(frozen=True)
class DocumentBlock:
    kind: DocumentBlockKind
    text: str = ""


@dataclass(frozen=True)
class StructuredDocument:
    blocks: tuple[DocumentBlock, ...]


def get_master_cv_template_candidates(extension: str) -> tuple[Path, ...]:
    normalized = extension.lower().lstrip(".")
    candidates: list[Path] = []
    if normalized == "docx":
        configured = getattr(settings, "MASTER_CV_TEMPLATE_DOCX_PATH", "") or getattr(
            settings, "MASTER_CV_FILE_PATH", ""
        )
    elif normalized == "pdf":
        configured = getattr(settings, "MASTER_CV_TEMPLATE_PDF_PATH", "") or getattr(
            settings, "MASTER_CV_FILE_PATH", ""
        )
    else:
        configured = getattr(settings, "MASTER_CV_FILE_PATH", "")

    if configured:
        configured_path = Path(configured)
        if configured_path.suffix.lower() == f".{normalized}":
            candidates.append(configured_path)
        else:
            candidates.append(configured_path.with_suffix(f".{normalized}"))

    running_tests = "test" in sys.argv
    if not running_tests:
        candidates.append(
            Path.home()
            / "workflow_tools"
            / "master_cv_reference"
            / f"{MASTER_CV_BASENAME}.{normalized}"
        )
    return tuple(candidates)


def get_master_cv_candidate_paths(extension: str) -> tuple[Path, ...]:
    return get_master_cv_template_candidates(extension)


def read_master_cv_template_if_available(extension: str) -> bytes | None:
    for path in get_master_cv_template_candidates(extension):
        if path.is_file() and path.stat().st_size > 0:
            return path.read_bytes()
    return None


def read_master_cv_file_if_available(extension: str) -> bytes | None:
    return read_master_cv_template_if_available(extension)


def master_cv_file_is_available(extension: str) -> bool:
    return read_master_cv_file_if_available(extension) is not None


def any_master_cv_file_is_available() -> bool:
    return master_cv_file_is_available("pdf") or master_cv_file_is_available("docx")


def _ordered_skills_in_group(
    group_skills: tuple[str, ...],
    prioritize: tuple[str, ...],
) -> tuple[str, ...]:
    ordered: list[str] = []
    remaining = list(group_skills)
    for skill in prioritize:
        skill_lower = skill.lower()
        for index, baseline in enumerate(remaining):
            baseline_lower = baseline.lower()
            if skill_lower in baseline_lower or baseline_lower in skill_lower:
                ordered.append(remaining.pop(index))
                break
    ordered.extend(remaining)
    return tuple(ordered)


def build_profile_paragraph(
    *,
    profile_angle: str,
    skills_to_prioritise: tuple[str, ...],
) -> str:
    portfolio_sentence = BASELINE_PROFILE_PORTFOLIO_SENTENCE
    angle = profile_angle.lower()
    if "bi analyst angle" in angle:
        portfolio_sentence = (
            "Developed a Python/Django analytics portfolio focused on data quality, KPI "
            "reporting, BI-ready outputs, and stakeholder-ready summaries for data "
            "analyst and BI analyst roles."
        )
    elif "finance / fx / fintech" in angle:
        portfolio_sentence = (
            "Developed a Python/Django analytics portfolio focused on data quality, "
            "FinTech analytics, reconciliation-led KPI reporting, and reproducible "
            "methodology for FinTech and FX analytics roles."
        )
    elif "analytics engineer stretch" in angle:
        portfolio_sentence = (
            "Developed a Python/Django analytics portfolio focused on data quality, "
            "ETL-style portfolio evidence, governed metric definitions, and reproducible "
            "methodology for analytics-engineering stretch roles."
        )
    elif skills_to_prioritise:
        skill_text = ", ".join(skills_to_prioritise[:4])
        portfolio_sentence = (
            "Developed a Python/Django analytics portfolio focused on data quality, KPI "
            f"reporting, {skill_text}, and reproducible methodology."
        )

    return BASELINE_PROFILE_PARAGRAPH.replace(
        BASELINE_PROFILE_PORTFOLIO_SENTENCE,
        portfolio_sentence,
    )


def build_tailored_portfolio_bullets(
    *,
    skills_to_prioritise: tuple[str, ...] = (),
    role_text: str = "",
) -> dict[str, tuple[str, ...]]:
    """Return baseline project bullets; CareerFunnel wording is fixed in the baseline."""
    _ = skills_to_prioritise, role_text
    return {project: tuple(lines) for project, lines in PORTFOLIO_PROJECT_BULLETS.items()}


def build_structured_master_cv(
    *,
    profile_angle: str = "",
    skills_to_prioritise: tuple[str, ...] = (),
    project_bullets: dict[str, tuple[str, ...]] | None = None,
) -> StructuredDocument:
    portfolio_bullets = project_bullets or PORTFOLIO_PROJECT_BULLETS
    blocks: list[DocumentBlock] = [
        DocumentBlock("name", MASTER_CV_DISPLAY_NAME),
        DocumentBlock("headline", MASTER_CV_HEADLINE),
        DocumentBlock("contact", MASTER_CV_CONTACT_LINES[0]),
        DocumentBlock("contact", MASTER_CV_CONTACT_LINES[1]),
        DocumentBlock("section", "PROFILE"),
        DocumentBlock(
            "paragraph",
            build_profile_paragraph(
                profile_angle=profile_angle,
                skills_to_prioritise=skills_to_prioritise,
            ),
        ),
        DocumentBlock("section", "TECHNICAL SKILLS"),
    ]
    for group_name, group_skills in TECHNICAL_SKILL_GROUPS.items():
        ordered = _ordered_skills_in_group(group_skills, skills_to_prioritise)
        blocks.append(DocumentBlock("paragraph", f"{group_name}: {', '.join(ordered)}."))

    blocks.append(DocumentBlock("section", "PROFESSIONAL EXPERIENCE"))
    blocks.append(DocumentBlock("subheading", EXPERIENCE_MONEY_TRANSFER_FX_TITLE))
    for line in EXPERIENCE_MONEY_TRANSFER_FX_BULLETS:
        blocks.append(DocumentBlock("bullet", line))
    blocks.append(DocumentBlock("subheading", EXPERIENCE_AREA_MANAGER_TITLE))
    for line in EXPERIENCE_AREA_MANAGER_BULLETS:
        blocks.append(DocumentBlock("bullet", line))
    blocks.append(DocumentBlock("subheading", EXPERIENCE_EARLIER_TITLE))
    for line in EXPERIENCE_EARLIER_BULLETS:
        blocks.append(DocumentBlock("bullet", line))

    blocks.append(DocumentBlock("section", "EDUCATION"))
    for line in EDUCATION_ENTRIES:
        blocks.append(DocumentBlock("bullet", line))

    blocks.append(DocumentBlock("section", "PORTFOLIO PROJECTS"))
    blocks.append(DocumentBlock("paragraph", PORTFOLIO_PROJECTS_INTRO))
    for project in DEFAULT_PROJECT_ORDER:
        blocks.append(DocumentBlock("subheading", PORTFOLIO_PROJECT_TAGLINES[project]))
        for bullet in portfolio_bullets.get(project, PORTFOLIO_PROJECT_BULLETS[project]):
            blocks.append(DocumentBlock("bullet", bullet))

    blocks.append(DocumentBlock("section", "ADDITIONAL INFORMATION"))
    for line in ADDITIONAL_INFORMATION_LINES:
        blocks.append(DocumentBlock("bullet", line))

    return StructuredDocument(blocks=tuple(blocks))


COVER_LETTER_INTERNAL_PHRASES = (
    "review before use",
    "draft/manual-review",
    "draft cover letter",
    "tailoring notes",
    "project evidence",
    "claim-safety notes",
    "quick call notes",
    "document type",
    "review the company and role details manually before use",
    "review project evidence manually before use",
)


COVER_LETTER_BODY_MISSING_MESSAGE = (
    "Cover letter body is missing. Paste, upload, or generate cover-letter text "
    "before downloading."
)
COVER_LETTER_DUPLICATE_STRUCTURE_MESSAGE = (
    "Cover letter structure could not be cleaned for export. "
    "Review the draft and try applying recommended fixes again."
)
COVER_LETTER_MIN_BODY_CHARACTERS = 250
COVER_LETTER_MIN_BODY_PARAGRAPHS = 2

_WEAK_GENERATED_OPENING_PATTERN = re.compile(
    r"^i am applying for (?:the |this ).*(?:role )?and can connect my finance",
    re.IGNORECASE,
)
_OPENING_STARTERS = (
    "i am writing to express",
    "i am particularly interested",
    "i am applying for",
)
_OPENING_MERGE_STARTERS = (
    "i am writing to express",
    "i am applying for",
)
_BACKGROUND_OPENING_PREFIX = "my background"

COVER_LETTER_GREETING_PATTERN = re.compile(r"^dear\s+", re.IGNORECASE)
COVER_LETTER_CLOSING_PATTERN = re.compile(
    r"^(kind regards|yours sincerely|best regards|sincerely),?$",
    re.IGNORECASE,
)
COVER_LETTER_SIGNATURE_PATTERN = re.compile(r"^aminul\s+islam\.?$", re.IGNORECASE)

_REPEATED_PHRASE_FIXES: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bfor the this\b", re.IGNORECASE), "for this"),
    (re.compile(r"\bthe this\b", re.IGNORECASE), "this"),
    (re.compile(r"\brole role\b", re.IGNORECASE), "role"),
    (re.compile(r"\bthe the\b", re.IGNORECASE), "the"),
    (re.compile(r"\bto to\b", re.IGNORECASE), "to"),
)
_ADJACENT_DUPLICATE_WORD = re.compile(r"\b([a-z]{3,})\s+\1\b", re.IGNORECASE)


def clean_repeated_cover_letter_phrases(text: str) -> str:
    cleaned = text or ""
    if "\n\n" in cleaned:
        paragraphs: list[str] = []
        for paragraph in cleaned.split("\n\n"):
            normalized = paragraph
            for pattern, replacement in _REPEATED_PHRASE_FIXES:
                normalized = pattern.sub(replacement, normalized)
            normalized = _ADJACENT_DUPLICATE_WORD.sub(r"\1", normalized)
            normalized = re.sub(r" {2,}", " ", normalized).strip()
            if normalized:
                paragraphs.append(normalized)
        return "\n\n".join(paragraphs)
    for pattern, replacement in _REPEATED_PHRASE_FIXES:
        cleaned = pattern.sub(replacement, cleaned)
    cleaned = _ADJACENT_DUPLICATE_WORD.sub(r"\1", cleaned)
    return re.sub(r" {2,}", " ", cleaned).strip()


def _is_structural_cover_letter_line(
    line: str,
    *,
    company_name: str = "",
    job_title: str = "",
) -> bool:
    lowered = line.lower().strip().rstrip(",")
    if not lowered:
        return True
    if _is_cover_letter_header_line(line):
        return True
    if COVER_LETTER_GREETING_PATTERN.match(lowered):
        return True
    if COVER_LETTER_CLOSING_PATTERN.match(lowered):
        return True
    if COVER_LETTER_SIGNATURE_PATTERN.match(lowered):
        return True
    if lowered in {"hiring team", "dear hiring team", "dear hiring manager"}:
        return True
    if lowered == MASTER_CV_HEADLINE.lower():
        return True
    if lowered == COVER_LETTER_CONTACT_LINE.lower():
        return True
    for contact_line in MASTER_CV_CONTACT_LINES:
        if lowered == contact_line.lower():
            return True
    company = (company_name or "").strip().lower()
    role = (job_title or "").strip().lower()
    if company and lowered == company:
        return True
    if role and lowered == role:
        return True
    if "aminulislamkhan.tech@gmail.com" in lowered:
        return True
    if "07443 360827" in lowered and "purley" in lowered:
        return True
    if lowered.startswith("github.com/aminul-portfolio"):
        return True
    if lowered.startswith("linkedin.com/in/aminul"):
        return True
    return False


def _filter_structural_lines(
    lines: list[str],
    *,
    company_name: str = "",
    job_title: str = "",
) -> list[str]:
    return [
        line
        for line in lines
        if not _is_structural_cover_letter_line(
            line,
            company_name=company_name,
            job_title=job_title,
        )
    ]


def _dedupe_cover_letter_paragraphs(paragraphs: list[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for paragraph in paragraphs:
        normalized = re.sub(r"\s+", " ", paragraph.lower()).strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        unique.append(paragraph)
    return unique


def _is_cover_letter_header_line(line: str) -> bool:
    lowered = line.lower().strip()
    if lowered in {"aminul islam", "hiring team"}:
        return True
    if "data analyst | bi analyst" in lowered:
        return True
    if "purley, london" in lowered and "07443" in lowered:
        return True
    if "github.com/aminul-portfolio" in lowered or "linkedin.com/in/aminul" in lowered:
        return True
    if "uk work authorisation" in lowered:
        return True
    return False


def _is_internal_cover_letter_paragraph(paragraph: str) -> bool:
    lowered = paragraph.lower().strip()
    if lowered.startswith("the role highlights ") and "i can connect these tools" in lowered:
        return True
    for phrase in COVER_LETTER_INTERNAL_PHRASES:
        if lowered == phrase:
            return True
        if lowered.startswith(f"{phrase}:"):
            return True
        if lowered.startswith(f"{phrase} -"):
            return True
    return False


def _normalize_cover_letter_paragraphs(body: str) -> list[str]:
    text = (body or "").replace("\r\n", "\n").strip()
    if not text:
        return []
    if "\n\n" in text:
        return [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    return [line.strip() for line in text.split("\n") if line.strip()]


def build_clean_cover_letter_body(
    draft_text: str,
    *,
    company_name: str = "",
    job_title: str = "",
    recommended_fixes: tuple[str, ...] | None = None,
) -> str:
    """Return cleaned employer-facing body paragraphs only (no letter structure)."""
    del recommended_fixes  # reserved for callers that pass checker context
    return extract_cover_letter_body_for_export(
        draft_text,
        company_name=company_name,
        job_title=job_title,
    )


def _is_standalone_recipient_paragraph(
    paragraph: str,
    *,
    company_name: str = "",
    job_title: str = "",
) -> bool:
    stripped = paragraph.strip()
    if not stripped:
        return True
    if _is_structural_cover_letter_line(
        stripped,
        company_name=company_name,
        job_title=job_title,
    ):
        return True
    role = (job_title or "").strip()
    if role and stripped.lower().startswith(role.lower() + "."):
        remainder = stripped[len(role) :].lstrip(".").strip().lower()
        if not remainder or remainder.startswith("i can connect"):
            return True
    return False


def _strip_role_title_prefix(paragraph: str, job_title: str) -> str:
    role = (job_title or "").strip()
    if not role:
        return paragraph
    stripped = paragraph.strip()
    if stripped.lower().startswith(role.lower() + "."):
        return stripped[len(role) + 1 :].strip()
    return paragraph


def normalize_cover_letter_body_paragraphs(
    paragraphs: list[str],
    *,
    company_name: str = "",
    job_title: str = "",
) -> list[str]:
    """Drop recipient-only lines and role-prefixed fragments from body paragraphs."""
    cleaned: list[str] = []
    for paragraph in paragraphs:
        text = paragraph.strip()
        if not text or _is_standalone_recipient_paragraph(
            text,
            company_name=company_name,
            job_title=job_title,
        ):
            continue
        text = _strip_role_title_prefix(text, job_title)
        if text:
            cleaned.append(text)
    cleaned = remove_weak_generated_cover_letter_paragraphs(cleaned)
    cleaned = merge_cover_letter_opening_paragraphs(cleaned)
    return _dedupe_cover_letter_paragraphs(cleaned)


def build_clean_cover_letter_paragraphs(
    draft_text: str,
    *,
    company_name: str = "",
    job_title: str = "",
) -> list[str]:
    body = build_clean_cover_letter_body(
        draft_text,
        company_name=company_name,
        job_title=job_title,
    )
    return normalize_cover_letter_body_paragraphs(
        [part.strip() for part in body.split("\n\n") if part.strip()],
        company_name=company_name,
        job_title=job_title,
    )


def remove_weak_generated_cover_letter_paragraphs(paragraphs: list[str]) -> list[str]:
    cleaned: list[str] = []
    for paragraph in paragraphs:
        if _WEAK_GENERATED_OPENING_PATTERN.match(paragraph.strip()):
            continue
        cleaned.append(paragraph)
    return cleaned


def merge_cover_letter_opening_paragraphs(paragraphs: list[str]) -> list[str]:
    if len(paragraphs) < 2:
        return paragraphs
    merged: list[str] = []
    opening_used = False
    for paragraph in paragraphs:
        lowered = paragraph.lower().strip()
        is_opening = any(lowered.startswith(starter) for starter in _OPENING_MERGE_STARTERS)
        if is_opening and not opening_used:
            opening_used = True
            merged.append(paragraph)
            continue
        if is_opening and opening_used and merged:
            merged[0] = clean_repeated_cover_letter_phrases(f"{merged[0]} {paragraph}")
            continue
        merged.append(paragraph)
    return merged


def consolidate_cover_letter_opening_paragraphs(
    paragraphs: list[str],
    *,
    company_name: str = "",
    job_title: str = "",
) -> list[str]:
    """Merge writing, interest, and immediate background lines into one opening paragraph."""
    normalized = normalize_cover_letter_body_paragraphs(
        paragraphs,
        company_name=company_name,
        job_title=job_title,
    )
    if not normalized:
        return []
    writing_index = next(
        (
            index
            for index, paragraph in enumerate(normalized)
            if paragraph.lower().startswith("i am writing to express my interest")
        ),
        0,
    )
    opening = normalized[writing_index]
    remainder: list[str] = []
    for index, paragraph in enumerate(normalized):
        if index == writing_index:
            continue
        lowered = paragraph.lower().strip()
        if lowered.startswith(("i am particularly interested", "i am applying for")):
            opening = clean_repeated_cover_letter_phrases(f"{opening} {paragraph}")
            continue
        if (
            index == writing_index + 1
            and lowered.startswith(_BACKGROUND_OPENING_PREFIX)
            and len(remainder) == 0
        ):
            opening = clean_repeated_cover_letter_phrases(f"{opening} {paragraph}")
            continue
        remainder.append(paragraph)
    return [opening, *remainder]


def extract_cover_letter_body_for_export(
    body: str,
    *,
    company_name: str = "",
    job_title: str = "",
) -> str:
    """Extract employer-facing body paragraphs from draft or adjusted cover letter text."""
    paragraphs = _normalize_cover_letter_paragraphs(body)
    cleaned: list[str] = []

    for paragraph in paragraphs:
        lines = [line.strip() for line in paragraph.splitlines() if line.strip()]
        if not lines:
            continue

        if COVER_LETTER_GREETING_PATTERN.match(lines[0]):
            lines = lines[1:]

        lines = _filter_structural_lines(
            lines,
            company_name=company_name,
            job_title=job_title,
        )
        if not lines:
            continue

        truncated: list[str] = []
        for line in lines:
            lowered = line.lower().strip().rstrip(",")
            if COVER_LETTER_CLOSING_PATTERN.match(lowered) or COVER_LETTER_SIGNATURE_PATTERN.match(
                lowered
            ):
                break
            truncated.append(line)
        if not truncated:
            continue

        paragraph_text = clean_repeated_cover_letter_phrases(" ".join(truncated))
        if not paragraph_text or _is_internal_cover_letter_paragraph(paragraph_text):
            continue
        cleaned.append(paragraph_text)

    return sanitize_cover_letter_body(
        "\n\n".join(_dedupe_cover_letter_paragraphs(cleaned)),
        company_name=company_name,
        job_title=job_title,
    )


def validate_cover_letter_export_body(
    body: str,
    *,
    company_name: str = "",
    job_title: str = "",
) -> str | None:
    text = (body or "").strip()
    paragraphs = [part.strip() for part in text.split("\n\n") if part.strip()]
    if len(paragraphs) < COVER_LETTER_MIN_BODY_PARAGRAPHS:
        if len(text) < COVER_LETTER_MIN_BODY_CHARACTERS:
            return COVER_LETTER_BODY_MISSING_MESSAGE

    lowered = text.lower()
    if "dear hiring team" in lowered or "dear hiring manager" in lowered:
        return COVER_LETTER_DUPLICATE_STRUCTURE_MESSAGE
    if "kind regards" in lowered or "yours sincerely" in lowered:
        return COVER_LETTER_DUPLICATE_STRUCTURE_MESSAGE

    company = (company_name or "").strip()
    role = (job_title or "").strip()
    for paragraph in paragraphs:
        stripped = paragraph.strip()
        if company and stripped == company:
            return COVER_LETTER_DUPLICATE_STRUCTURE_MESSAGE
        if role and stripped == role:
            return COVER_LETTER_DUPLICATE_STRUCTURE_MESSAGE
        if role and stripped.lower().startswith(role.lower() + "."):
            return COVER_LETTER_DUPLICATE_STRUCTURE_MESSAGE

    if "for the this" in lowered or "role role" in lowered:
        return COVER_LETTER_DUPLICATE_STRUCTURE_MESSAGE
    if "my background. i am" in lowered:
        return COVER_LETTER_DUPLICATE_STRUCTURE_MESSAGE

    opening_count = sum(
        1
        for paragraph in paragraphs
        if any(paragraph.lower().startswith(starter) for starter in _OPENING_STARTERS)
    )
    if opening_count > 1:
        return COVER_LETTER_DUPLICATE_STRUCTURE_MESSAGE

    return None


def sanitize_cover_letter_body(
    body: str,
    *,
    company_name: str = "",
    job_title: str = "",
) -> str:
    """Remove internal/manual-review wording from employer-facing cover letter body."""
    paragraphs: list[str] = []
    for paragraph in _normalize_cover_letter_paragraphs(body):
        lines = _filter_structural_lines(
            [line.strip() for line in paragraph.splitlines() if line.strip()],
            company_name=company_name,
            job_title=job_title,
        )
        if not lines:
            if _is_structural_cover_letter_line(
                paragraph,
                company_name=company_name,
                job_title=job_title,
            ):
                continue
            lines = [paragraph.strip()]
        cleaned = clean_repeated_cover_letter_phrases(" ".join(lines))
        if not cleaned or _is_internal_cover_letter_paragraph(cleaned):
            continue
        paragraphs.append(cleaned)
    return "\n\n".join(
        normalize_cover_letter_body_paragraphs(
            paragraphs,
            company_name=company_name,
            job_title=job_title,
        )
    )


def is_cover_letter_layout_structured(document: StructuredDocument) -> bool:
    for block in document.blocks:
        if block.kind == "salutation":
            return True
        if block.kind == "paragraph" and block.text.strip() in {
            "Dear Hiring Team,",
            "Dear Hiring Manager,",
        }:
            return True
    return False


def build_structured_cover_letter(
    *,
    company_name: str,
    job_title: str,
    body: str,
) -> StructuredDocument:
    company = (company_name or "").strip() or "Not specified"
    role = (job_title or "").strip() or "Not specified"
    blocks: list[DocumentBlock] = [
        DocumentBlock("name", "Aminul Islam"),
        DocumentBlock("headline", MASTER_CV_HEADLINE),
        DocumentBlock("contact", COVER_LETTER_CONTACT_LINE),
        DocumentBlock("recipient", "Hiring Team"),
    ]
    if company != "Not specified":
        blocks.append(DocumentBlock("recipient", company))
    if role != "Not specified":
        blocks.append(DocumentBlock("recipient", role))
    blocks.append(DocumentBlock("salutation", "Dear Hiring Team,"))
    export_body = extract_cover_letter_body_for_export(
        body,
        company_name=company,
        job_title=role,
    )
    for paragraph in export_body.split("\n\n"):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        if COVER_LETTER_GREETING_PATTERN.match(paragraph):
            continue
        if _is_standalone_recipient_paragraph(
            paragraph,
            company_name=company,
            job_title=role,
        ):
            continue
        blocks.append(DocumentBlock("paragraph", paragraph))
    blocks.append(DocumentBlock("closing_line", "Kind regards,"))
    blocks.append(DocumentBlock("closing_name", "Aminul Islam"))
    return StructuredDocument(blocks=tuple(blocks))


_PLAIN_TEXT_BLOCK_KINDS = frozenset(
    {
        "name",
        "headline",
        "contact",
        "recipient",
        "salutation",
        "closing_line",
        "closing_name",
        "section",
        "subheading",
        "paragraph",
    }
)


def structured_document_to_plain_text(document: StructuredDocument) -> str:
    lines: list[str] = []
    for block in document.blocks:
        if block.kind == "blank":
            lines.append("")
        elif block.kind == "bullet":
            lines.append(f"- {block.text}")
        elif block.kind in _PLAIN_TEXT_BLOCK_KINDS:
            lines.append(block.text)
    return "\n".join(lines).strip() + "\n"


_LEGACY_SECTION_MAP = {
    "professional profile": "PROFILE",
    "profile": "PROFILE",
    "core skills": None,
    "technical skills": "TECHNICAL SKILLS",
    "professional experience": "PROFESSIONAL EXPERIENCE",
    "education": "EDUCATION",
    "selected projects": "PORTFOLIO PROJECTS",
    "portfolio projects": "PORTFOLIO PROJECTS",
    "additional information": "ADDITIONAL INFORMATION",
}

MASTER_CV_LAYOUT_SECTIONS = (
    "PROFILE",
    "TECHNICAL SKILLS",
    "PROFESSIONAL EXPERIENCE",
    "EDUCATION",
    "PORTFOLIO PROJECTS",
    "ADDITIONAL INFORMATION",
)


def is_master_cv_layout_content(content: str) -> bool:
    upper = (content or "").upper()
    if "AMINUL ISLAM" not in upper and "AMINUL" not in upper:
        return False
    markers = (
        "PROFILE",
        "PROFESSIONAL PROFILE",
        "TECHNICAL SKILLS",
        "PROFESSIONAL EXPERIENCE",
        "PORTFOLIO PROJECTS",
    )
    return sum(1 for marker in markers if marker in upper) >= 3


def is_master_cv_layout_structured(document: StructuredDocument) -> bool:
    sections = [block.text for block in document.blocks if block.kind == "section"]
    if all(section in sections for section in MASTER_CV_LAYOUT_SECTIONS):
        return True
    legacy_sections = {
        _LEGACY_SECTION_MAP.get(section.lower(), section)
        for section in sections
    }
    return all(section in legacy_sections for section in MASTER_CV_LAYOUT_SECTIONS)


def _headline_from_structured_blocks(blocks: tuple[DocumentBlock, ...]) -> str:
    for block in blocks:
        if block.kind == "headline" and block.text.strip():
            return block.text.strip()
    return MASTER_CV_HEADLINE


def _extract_master_cv_body_blocks(blocks: tuple[DocumentBlock, ...]) -> tuple[DocumentBlock, ...]:
    body: list[DocumentBlock] = []
    for block in blocks:
        if block.kind == "section" and block.text == "PROFILE":
            body = [block]
            continue
        if body:
            body.append(block)
    return tuple(body)


def _normalize_master_cv_body_blocks(
    blocks: tuple[DocumentBlock, ...],
) -> tuple[DocumentBlock, ...]:
    normalized: list[DocumentBlock] = []
    for block in blocks:
        if block.kind == "blank":
            continue
        if block.kind == "section":
            mapped = _LEGACY_SECTION_MAP.get(block.text.lower(), block.text)
            if mapped:
                normalized.append(DocumentBlock("section", mapped))
            continue
        normalized.append(block)
    return tuple(normalized)


def canonicalize_master_cv_structured(document: StructuredDocument) -> StructuredDocument:
    """Apply the canonical master CV header while preserving tailored body content."""
    body_blocks = _normalize_master_cv_body_blocks(_extract_master_cv_body_blocks(document.blocks))
    if not body_blocks:
        return document
    header = (
        DocumentBlock("name", MASTER_CV_DISPLAY_NAME),
        DocumentBlock("headline", _headline_from_structured_blocks(document.blocks)),
        DocumentBlock("contact", MASTER_CV_CONTACT_LINES[0]),
        DocumentBlock("contact", MASTER_CV_CONTACT_LINES[1]),
    )
    return StructuredDocument(blocks=header + body_blocks)


def should_use_master_cv_layout(
    content: str,
    structured: StructuredDocument,
    *,
    cv_baseline_name: str = "",
    document_name: str = "",
) -> bool:
    if cv_baseline_name == LOCKED_CV:
        return True
    if document_name == MASTER_CV_BASENAME or document_name.startswith(f"{MASTER_CV_BASENAME}_"):
        return True
    if is_master_cv_layout_content(content):
        return True
    return is_master_cv_layout_structured(structured)


def build_structured_cv_for_export(
    content: str,
    *,
    cv_baseline_name: str = "",
    document_name: str = "",
) -> StructuredDocument:
    stripped = (content or "").strip()
    if not stripped:
        return StructuredDocument(blocks=(DocumentBlock("paragraph", "Not saved."),))
    structured = parse_cv_plain_text_to_structured(stripped)
    if should_use_master_cv_layout(
        stripped,
        structured,
        cv_baseline_name=cv_baseline_name,
        document_name=document_name,
    ):
        return canonicalize_master_cv_structured(structured)
    return structured


def parse_cv_plain_text_to_structured(content: str) -> StructuredDocument:
    stripped = (content or "").strip()
    if not stripped:
        return StructuredDocument(blocks=(DocumentBlock("paragraph", "Not saved."),))

    lines = stripped.splitlines()
    blocks: list[DocumentBlock] = []
    current_section = ""
    index = 0

    while index < len(lines) and lines[index].strip():
        line = lines[index].strip()
        if line.upper() == MASTER_CV_DISPLAY_NAME or line.startswith("Aminul Islam"):
            if "/" in line and not line.upper().startswith(MASTER_CV_DISPLAY_NAME):
                name_part, headline_part = line.split("/", 1)
                blocks.append(DocumentBlock("name", name_part.strip()))
                blocks.append(DocumentBlock("headline", headline_part.strip()))
            else:
                blocks.append(
                    DocumentBlock(
                        "name",
                        MASTER_CV_DISPLAY_NAME if line.upper() == MASTER_CV_DISPLAY_NAME else line,
                    )
                )
            index += 1
            continue
        if not blocks and line == MASTER_CV_HEADLINE:
            blocks.append(DocumentBlock("name", MASTER_CV_DISPLAY_NAME))
            blocks.append(DocumentBlock("headline", line))
            index += 1
            continue
        if any(
            marker in line.lower()
            for marker in (
                "github",
                "purley",
                "london",
                "uk ilr",
                "eligible to work",
                "07443",
                "aminulislamkhan",
            )
        ):
            blocks.append(DocumentBlock("contact", line))
            index += 1
            continue
        if line == MASTER_CV_HEADLINE or (
            blocks
            and blocks[-1].kind == "name"
            and "|" in line
            and line.lower() not in _LEGACY_SECTION_MAP
        ):
            blocks.append(DocumentBlock("headline", line))
            index += 1
            continue
        break

    if blocks and blocks[-1].kind != "blank":
        blocks.append(DocumentBlock("blank"))

    while index < len(lines):
        raw = lines[index].strip()
        index += 1
        if not raw:
            continue
        normalized = raw.lower()
        if normalized in _LEGACY_SECTION_MAP:
            mapped = _LEGACY_SECTION_MAP[normalized]
            if mapped is None:
                current_section = ""
                while index < len(lines) and lines[index].strip().startswith("-"):
                    index += 1
                continue
            current_section = mapped
            blocks.append(DocumentBlock("section", mapped))
            continue
        if raw.startswith("- "):
            blocks.append(DocumentBlock("bullet", raw[2:].strip()))
            continue
        if current_section == "PORTFOLIO PROJECTS" and raw in PORTFOLIO_PROJECT_TAGLINES.values():
            blocks.append(DocumentBlock("subheading", raw))
            continue
        if current_section == "PORTFOLIO PROJECTS" and raw in PORTFOLIO_PROJECT_BULLETS:
            blocks.append(DocumentBlock("subheading", PORTFOLIO_PROJECT_TAGLINES.get(raw, raw)))
            continue
        if current_section == "PROFESSIONAL EXPERIENCE" and (
            raw.startswith("Money Transfer")
            or raw.startswith("Area Manager")
            or raw.startswith("Earlier Roles")
        ):
            blocks.append(DocumentBlock("subheading", raw))
            continue
        if current_section == "TECHNICAL SKILLS" and any(
            raw.startswith(f"{group}:") for group in TECHNICAL_SKILL_GROUPS
        ):
            blocks.append(DocumentBlock("paragraph", raw))
            continue
        blocks.append(DocumentBlock("paragraph", raw))

    if not blocks:
        return StructuredDocument(blocks=(DocumentBlock("paragraph", stripped),))
    return StructuredDocument(blocks=tuple(blocks))


def parse_cover_letter_plain_text_to_structured(content: str) -> StructuredDocument:
    stripped = (content or "").strip()
    if not stripped:
        return StructuredDocument(blocks=(DocumentBlock("paragraph", "Not saved."),))
    return build_structured_cover_letter(
        company_name="",
        job_title="",
        body=stripped,
    )


CV_MISSING_MESSAGE = "No CV draft available yet"


def build_missing_cv_document(message: str) -> StructuredDocument:
    return StructuredDocument(
        blocks=(
            DocumentBlock("section", "CV Download"),
            DocumentBlock("paragraph", message),
        )
    )


def cv_baseline_is_master(document) -> bool:
    baseline = getattr(document, "cv_baseline_name", "") or ""
    if baseline == LOCKED_CV:
        return True
    name = getattr(document, "name", "") or ""
    return name == MASTER_CV_BASENAME or name.startswith(f"{MASTER_CV_BASENAME}_")

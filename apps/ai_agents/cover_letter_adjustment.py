from __future__ import annotations

import re
from dataclasses import dataclass

from apps.ai_agents.services import CoverLetterQualityResult
from apps.applications.master_cv import (
    build_clean_cover_letter_paragraphs,
    clean_repeated_cover_letter_phrases,
    consolidate_cover_letter_opening_paragraphs,
    extract_cover_letter_body_for_export,
    normalize_cover_letter_body_paragraphs,
    sanitize_cover_letter_body,
)

INTERNAL_WORDING_PATTERNS = (
    r"\bmanual review only\b",
    r"\binternal baseline\b",
    r"\btracker label\b",
    r"\bdraft only\b",
    r"\btodo\b",
    r"\bno ab data\b",
    r"\bpromising\b",
    r"\bunderperforming\b",
)

RISKY_CLAIM_REPLACEMENTS = {
    "guaranteed": "evidence-based",
    "best candidate": "strong candidate",
    "expert": "practical",
    "master": "confident",
    "10 years of data": "structured analytics experience",
}

CHECKER_LABEL_PATTERNS = (
    r"\bquality score\b",
    r"\bbest fix\b",
    r"\brecommended fixes?\b",
    r"\bstrengths?\b",
    r"\bweaknesses?\b",
    r"\bclaim-safety\b",
    r"\breview before use\b",
)

_APPLYING_REDUNDANCY_PATTERN = re.compile(
    r"\s*I am applying for the[^.]+\.\s*",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class AdjustedCoverLetterResult:
    body: str
    changes_applied: tuple[str, ...]


def _clean_internal_wording(text: str) -> str:
    cleaned = text or ""
    for pattern in INTERNAL_WORDING_PATTERNS:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
    for pattern in CHECKER_LABEL_PATTERNS:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def _join_paragraphs(paragraphs: list[str]) -> str:
    return "\n\n".join(part for part in paragraphs if part.strip())


def _paragraphs_contain(paragraphs: list[str], *needles: str) -> bool:
    joined = " ".join(paragraphs).lower()
    return any(needle.lower() in joined for needle in needles if needle)


def _dedupe_paragraphs(paragraphs: list[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for paragraph in paragraphs:
        key = re.sub(r"\s+", " ", paragraph.lower()).strip()
        if key in seen:
            continue
        seen.add(key)
        unique.append(paragraph)
    return unique


def _merge_sentence_into_paragraph(paragraph: str, sentence: str) -> str:
    cleaned_paragraph = paragraph.strip()
    cleaned_sentence = sentence.strip()
    if not cleaned_sentence:
        return cleaned_paragraph
    if not cleaned_paragraph:
        return cleaned_sentence
    if cleaned_sentence.lower() in cleaned_paragraph.lower():
        return cleaned_paragraph
    return f"{cleaned_paragraph} {cleaned_sentence}"


def _merge_into_paragraph_at_index(
    paragraphs: list[str],
    index: int,
    sentence: str,
) -> list[str]:
    if _paragraphs_contain(paragraphs, sentence[:48]):
        return paragraphs
    updated = list(paragraphs)
    if not updated:
        updated.append(sentence)
        return updated
    target = min(max(index, 0), len(updated) - 1)
    updated[target] = _merge_sentence_into_paragraph(updated[target], sentence)
    return updated


def _append_paragraph_if_missing(paragraphs: list[str], sentence: str) -> list[str]:
    if _paragraphs_contain(paragraphs, sentence[:48]):
        return paragraphs
    updated = list(paragraphs)
    updated.append(sentence)
    return updated


def _company_relevance_sentence(company_name: str, *, company_in_opening: bool = False) -> str:
    company = (company_name or "").strip()
    if company and not company_in_opening:
        return (
            f"I am particularly interested in {company} because this role aligns with "
            "my background in data analysis, reporting, and stakeholder-facing insight work."
        )
    return (
        "I am particularly interested in this role because it combines data analysis, "
        "reporting, and stakeholder-facing insight work."
    )


def _role_evidence_sentence() -> str:
    return (
        "I can connect my finance and operations background with practical Python, Excel, "
        "SQL, and dashboard project evidence."
    )


def _project_evidence_sentence(job_description: str) -> str:
    job_text = (job_description or "").lower()
    if any(word in job_text for word in ["finance", "risk", "bank", "market"]):
        project = "MarketVista Dashboard"
    elif any(word in job_text for word in ["operations", "kpi", "margin", "product"]):
        project = "BakeOps Intelligence"
    else:
        project = "CareerFunnel Tracker"
    return (
        f"My {project} project demonstrates practical reporting discipline, structured "
        "workflow design, and evidence-based analytics delivery."
    )


def _business_value_sentence(job_description: str) -> str:
    keywords = []
    for term in ("kpi", "reporting", "dashboard", "stakeholder", "analysis", "operations"):
        if term in (job_description or "").lower():
            keywords.append(term)
    if keywords:
        joined = ", ".join(keywords[:3])
        return (
            f"I can contribute to {joined} work with accurate reporting, clear KPI "
            "communication, and careful validation before sharing outputs."
        )
    return (
        "I can contribute through accurate reporting, clear KPI communication, and "
        "careful validation before sharing outputs."
    )


def _closing_interest_sentence() -> str:
    return (
        "Thank you for considering my application. I would welcome the opportunity "
        "to discuss how my reporting discipline and project evidence can support "
        "your team."
    )


def _soften_risky_claims(text: str) -> tuple[str, bool]:
    updated = text
    changed = False
    for risky, replacement in RISKY_CLAIM_REPLACEMENTS.items():
        if risky in updated.lower():
            updated = re.sub(re.escape(risky), replacement, updated, flags=re.IGNORECASE)
            changed = True
    return updated, changed


def _role_is_present(text_lower: str, job_title: str) -> bool:
    role = (job_title or "").strip().lower()
    if not role:
        return False
    if role in text_lower:
        return True
    tokens = [token for token in role.split() if len(token) > 3]
    if not tokens:
        return False
    return all(token in text_lower for token in tokens)


def _opening_with_role_and_company(company_name: str, job_title: str) -> str:
    role = (job_title or "").strip()
    company = (company_name or "").strip()
    if role and company:
        return f"I am writing to express my interest in the {role} role at {company}."
    if role:
        return f"I am writing to express my interest in the {role} role."
    if company:
        return f"I am writing to express my interest in opportunities at {company}."
    return "I am writing to express my interest in this opportunity."


def _strip_redundant_applying_clause(text: str) -> str:
    if "i am writing to express my interest" in text.lower():
        return _APPLYING_REDUNDANCY_PATTERN.sub(" ", text).strip()
    return text


def _opening_paragraph_index(paragraphs: list[str]) -> int:
    for index, paragraph in enumerate(paragraphs):
        lowered = paragraph.lower()
        if lowered.startswith(
            ("i am writing to express", "i am particularly interested", "i am applying for")
        ):
            return index
    return 0


def _ensure_professional_opening(
    paragraphs: list[str],
    *,
    company_name: str,
    job_title: str,
) -> list[str]:
    if not paragraphs:
        return [_opening_with_role_and_company(company_name, job_title)]
    updated = list(paragraphs)
    index = _opening_paragraph_index(updated)
    opening = updated[index]
    text_lower = " ".join(updated).lower()
    if opening.lower().startswith("i am applying for") and not opening.lower().startswith(
        "i am writing to express"
    ):
        updated[index] = _opening_with_role_and_company(company_name, job_title)
    elif not opening.lower().startswith("i am writing to express my interest"):
        if job_title.lower() not in text_lower:
            updated[index] = _merge_sentence_into_paragraph(
                _opening_with_role_and_company(company_name, job_title),
                opening,
            )
    updated[index] = _strip_redundant_applying_clause(updated[index])
    return updated


def apply_cover_letter_recommended_fixes(
    *,
    company_name: str,
    job_title: str,
    job_description: str,
    cover_letter: str,
    quality_result: CoverLetterQualityResult | None = None,
) -> AdjustedCoverLetterResult:
    changes: list[str] = []
    cleaned_draft = _clean_internal_wording(cover_letter)
    if cleaned_draft != (cover_letter or "").strip():
        changes.append("Removed internal or manual-review wording.")

    cleaned_draft, softened = _soften_risky_claims(cleaned_draft)
    if softened:
        changes.append("Softened exaggerated wording.")

    body_paragraphs = build_clean_cover_letter_paragraphs(
        cleaned_draft,
        company_name=company_name,
        job_title=job_title,
    )
    if not body_paragraphs and cleaned_draft.strip():
        body_paragraphs = [
            paragraph.strip()
            for paragraph in cleaned_draft.split("\n\n")
            if paragraph.strip()
        ]

    body_paragraphs = normalize_cover_letter_body_paragraphs(
        body_paragraphs,
        company_name=company_name,
        job_title=job_title,
    )
    body_paragraphs = _ensure_professional_opening(
        body_paragraphs,
        company_name=company_name,
        job_title=job_title,
    )

    text_lower = " ".join(body_paragraphs).lower()
    del quality_result  # fixes are applied deterministically from content gaps only
    opening_index = _opening_paragraph_index(body_paragraphs)
    company_in_opening = bool(company_name) and company_name.lower() in text_lower

    needs_company = bool(company_name) and company_name.lower() not in text_lower
    needs_role = bool(job_title) and not _role_is_present(text_lower, job_title)
    project_terms = (
        "bakeops",
        "marketvista",
        "careerfunnel",
        "tradeintel",
        "databridge",
        "riskwise",
    )
    needs_project = not any(term in text_lower for term in project_terms)
    needs_business = not any(
        term in text_lower
        for term in ("kpi", "reporting", "dashboard", "stakeholder", "analysis")
    )
    has_strong_opening = _paragraphs_contain(
        body_paragraphs,
        "i am writing to express my interest",
    )

    if needs_company or (
        has_strong_opening
        and not _paragraphs_contain(body_paragraphs, "particularly interested in")
    ):
        body_paragraphs = _merge_into_paragraph_at_index(
            body_paragraphs,
            opening_index,
            _company_relevance_sentence(company_name, company_in_opening=company_in_opening),
        )
        changes.append("Added company/domain relevance sentence.")

    if not _paragraphs_contain(body_paragraphs, "finance and operations background"):
        body_paragraphs = _merge_into_paragraph_at_index(
            body_paragraphs,
            opening_index,
            _role_evidence_sentence(),
        )
        if needs_role and not has_strong_opening:
            changes.append("Made role alignment explicit.")
        else:
            changes.append("Strengthened finance/operations evidence in the body.")

    if needs_business:
        target_index = opening_index if len(body_paragraphs) <= 1 else min(
            opening_index + 1, len(body_paragraphs) - 1
        )
        body_paragraphs = _merge_into_paragraph_at_index(
            body_paragraphs,
            target_index,
            _business_value_sentence(job_description),
        )
        changes.append("Connected business/reporting value to the role.")

    if needs_project:
        body_paragraphs = _append_paragraph_if_missing(
            body_paragraphs,
            _project_evidence_sentence(job_description),
        )
        changes.append("Strengthened portfolio project connection.")

    body_paragraphs = consolidate_cover_letter_opening_paragraphs(
        body_paragraphs,
        company_name=company_name,
        job_title=job_title,
    )
    body_paragraphs = _dedupe_paragraphs(body_paragraphs)

    word_count = len(_join_paragraphs(body_paragraphs).split())
    if word_count < 120 or word_count > 320:
        if not _paragraphs_contain(body_paragraphs, "thank you for considering"):
            body_paragraphs.append(_closing_interest_sentence())
            changes.append("Added concise closing paragraph for structure and length.")

    final_body = sanitize_cover_letter_body(
        _join_paragraphs(body_paragraphs),
        company_name=company_name,
        job_title=job_title,
    )
    final_body = extract_cover_letter_body_for_export(
        clean_repeated_cover_letter_phrases(final_body),
        company_name=company_name,
        job_title=job_title,
    )
    if not changes:
        changes.append("Applied rule-based polish while preserving the original draft structure.")
    return AdjustedCoverLetterResult(body=final_body, changes_applied=tuple(changes))

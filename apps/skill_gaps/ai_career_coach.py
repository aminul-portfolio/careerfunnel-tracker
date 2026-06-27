from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

EVIDENCE_PAYLOAD_KEYS = (
    "verified_skills",
    "learning_target_skills",
    "studying_skills",
    "no_evidence_skills",
    "not_in_ledger_terms",
    "matched_gap_rows",
    "project_evidence",
    "safety_rules",
)

RESPONSE_LIST_KEYS = (
    "evidence_backed_strengths",
    "skills_needing_evidence",
    "learning_targets",
    "claim_safety_warnings",
    "recommended_next_actions",
)

EVIDENCE_REFERENCED_RESPONSE_KEYS = (
    "evidence_backed_strengths",
    "skills_needing_evidence",
    "learning_targets",
    "recommended_next_actions",
)

REQUIRED_PROMPT_SAFETY_RULES = (
    "Use only supplied evidence.",
    "Do not infer missing experience.",
    "Do not upgrade evidence levels.",
    "Do not describe LEARNING_TARGET as current proficiency.",
    "Do not describe NO_EVIDENCE as evidence-backed.",
    "Return JSON only.",
    "Every recommendation must reference supplied evidence.",
)

DEFAULT_SAFETY_RULES = (
    "Skill gap signals are advisory only.",
    "Learning recommendations are planning aids.",
    "Evidence levels must not be upgraded.",
    "Manual review is always required.",
    *REQUIRED_PROMPT_SAFETY_RULES,
)

EXPECTED_RESPONSE_SCHEMA = {
    "evidence_backed_strengths": [],
    "skills_needing_evidence": [],
    "learning_targets": [],
    "claim_safety_warnings": [],
    "recommended_next_actions": [],
    "manual_review_required": True,
}

STATUS_TO_PAYLOAD_KEY = {
    "VERIFIED": "verified_skills",
    "LEARNING_TARGET": "learning_target_skills",
    "STUDYING": "studying_skills",
    "NO_EVIDENCE": "no_evidence_skills",
    "NOT_IN_LEDGER": "not_in_ledger_terms",
}

PRIVATE_EVIDENCE_FIELDS = {
    "company_name",
    "employer_name",
    "email",
    "notes",
    "private_notes",
    "cv_content",
    "cover_letter",
}

PROFICIENCY_OVERCLAIM_TERMS = (
    "current proficiency",
    "proficient",
    "expert",
    "mastery",
    "production-ready",
)

VERIFIED_OVERCLAIM_TERMS = (
    "verified",
    "evidence-backed",
    "evidence backed",
    "portfolio-backed",
    "portfolio backed",
)

FORBIDDEN_OUTCOME_TERMS = (
    "salary prediction",
    "offer prediction",
    "interview prediction",
    "hiring outcome",
    "will get hired",
    "meets employer requirement",
    "meets a specific employer requirement",
)


@dataclass(frozen=True)
class CareerCoachValidationResult:
    is_valid: bool
    errors: tuple[str, ...]
    parsed_response: dict[str, Any] | None = None
    safe_response: dict[str, Any] | None = None


def _normalise_text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _evidence_reference(status: str, term: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", term.lower()).strip("-")
    return f"{status}:{slug or 'unknown'}"


def _safe_project_evidence_item(item: dict[str, Any]) -> dict[str, str]:
    safe_item: dict[str, str] = {}
    for key in ("evidence_reference", "title", "evidence_type", "summary"):
        value = _normalise_text(item.get(key))
        if value:
            safe_item[key] = value
    return safe_item


def _safe_gap_row(row: dict[str, Any]) -> dict[str, str | bool]:
    term = _normalise_text(row.get("term") or row.get("skill_name"))
    status = _normalise_text(row.get("ledger_status"))
    matched_skill_name = _normalise_text(row.get("matched_skill_name"))
    display_label = _normalise_text(row.get("display_label") or status)
    evidence_reference = _normalise_text(row.get("evidence_reference"))
    if not evidence_reference:
        evidence_reference = _evidence_reference(status, term)
    return {
        "term": term,
        "ledger_status": status,
        "display_label": display_label,
        "matched_skill_name": matched_skill_name,
        "is_in_ledger": bool(row.get("is_in_ledger")),
        "evidence_reference": evidence_reference,
    }


def build_evidence_payload(
    *,
    matched_gap_rows: list[dict[str, Any]] | tuple[dict[str, Any], ...],
    project_evidence: list[dict[str, Any]] | tuple[dict[str, Any], ...] = (),
    safety_rules: list[str] | tuple[str, ...] = (),
) -> dict[str, Any]:
    payload: dict[str, Any] = {key: [] for key in EVIDENCE_PAYLOAD_KEYS}
    payload["safety_rules"] = list(
        dict.fromkeys((*DEFAULT_SAFETY_RULES, *safety_rules)),
    )

    for row in matched_gap_rows:
        safe_row = _safe_gap_row(row)
        payload["matched_gap_rows"].append(safe_row)
        bucket = STATUS_TO_PAYLOAD_KEY.get(str(safe_row["ledger_status"]))
        if bucket == "not_in_ledger_terms":
            payload[bucket].append(safe_row["term"])
        elif bucket:
            payload[bucket].append(
                {
                    "skill_name": safe_row["matched_skill_name"] or safe_row["term"],
                    "evidence_reference": safe_row["evidence_reference"],
                },
            )

    payload["project_evidence"] = [
        safe_item
        for item in project_evidence
        if (safe_item := _safe_project_evidence_item(item))
    ]
    return payload


def build_controlled_prompt(evidence_payload: dict[str, Any]) -> str:
    payload = {key: evidence_payload.get(key, []) for key in EVIDENCE_PAYLOAD_KEYS}
    payload["safety_rules"] = list(
        dict.fromkeys((*DEFAULT_SAFETY_RULES, *payload["safety_rules"])),
    )
    payload_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    safety_text = "\n".join(f"- {rule}" for rule in REQUIRED_PROMPT_SAFETY_RULES)
    return (
        "AI Career Coach architecture contract.\n"
        "Use the supplied evidence payload only.\n"
        "Safety rules:\n"
        f"{safety_text}\n"
        "Expected JSON keys: "
        f"{', '.join((*RESPONSE_LIST_KEYS, 'manual_review_required'))}.\n"
        f"Evidence payload JSON:\n{payload_json}"
    )


def expected_response_schema() -> dict[str, Any]:
    return {
        key: list(value) if isinstance(value, list) else value
        for key, value in EXPECTED_RESPONSE_SCHEMA.items()
    }


def build_mocked_career_coach_response(evidence_payload: dict[str, Any]) -> dict[str, Any]:
    response = expected_response_schema()

    if evidence_payload.get("verified_skills"):
        skill = evidence_payload["verified_skills"][0]
        response["evidence_backed_strengths"].append(
            {
                "skill": skill["skill_name"],
                "summary": (
                    "This skill can be discussed as Skill Ledger evidence exists. "
                    "Keep the claim tied to the supplied portfolio proof."
                ),
                "evidence_reference": skill["evidence_reference"],
            },
        )

    if evidence_payload.get("no_evidence_skills"):
        skill = evidence_payload["no_evidence_skills"][0]
        response["skills_needing_evidence"].append(
            {
                "skill": skill["skill_name"],
                "summary": (
                    "Treat this as a planning gap until project proof, tests, "
                    "screenshots, or prior work examples are added manually."
                ),
                "evidence_reference": skill["evidence_reference"],
            },
        )
    elif evidence_payload.get("not_in_ledger_terms"):
        row = _first_row_for_status(evidence_payload, "NOT_IN_LEDGER")
        if row:
            response["skills_needing_evidence"].append(
                {
                    "skill": row["term"],
                    "summary": (
                        "This term is not present in the supplied Skill Ledger rows. "
                        "Review it manually before using it in public materials."
                    ),
                    "evidence_reference": row["evidence_reference"],
                },
            )

    if evidence_payload.get("learning_target_skills"):
        skill = evidence_payload["learning_target_skills"][0]
        response["learning_targets"].append(
            {
                "skill": skill["skill_name"],
                "summary": (
                    "Keep this framed as a learning target and avoid presenting it "
                    "as already demonstrated ability."
                ),
                "evidence_reference": skill["evidence_reference"],
            },
        )

    action_skill = _first_referenced_skill(evidence_payload)
    if action_skill:
        response["recommended_next_actions"].append(
            {
                "skill": action_skill["skill_name"],
                "summary": (
                    "Review the linked evidence, then decide manually whether the "
                    "skill belongs in CV, profile, or interview notes."
                ),
                "evidence_reference": action_skill["evidence_reference"],
            },
        )

    if not any(response[key] for key in RESPONSE_LIST_KEYS if key != "claim_safety_warnings"):
        response["claim_safety_warnings"].append(
            {
                "summary": (
                    "No supplied Skill Ledger or gap rows were available for this "
                    "mocked planning run. Add manual evidence before making claims."
                ),
            },
        )
    else:
        response["claim_safety_warnings"].append(
            {
                "summary": (
                    "Manual review is required before using any wording in a CV, "
                    "profile, application, or interview preparation."
                ),
            },
        )

    response["manual_review_required"] = True
    return response


def _first_row_for_status(
    evidence_payload: dict[str, Any],
    status: str,
) -> dict[str, Any] | None:
    for row in evidence_payload.get("matched_gap_rows", []):
        if row.get("ledger_status") == status:
            return row
    return None


def _first_referenced_skill(evidence_payload: dict[str, Any]) -> dict[str, str] | None:
    for key in (
        "verified_skills",
        "learning_target_skills",
        "studying_skills",
        "no_evidence_skills",
    ):
        if evidence_payload.get(key):
            return evidence_payload[key][0]
    row = _first_row_for_status(evidence_payload, "NOT_IN_LEDGER")
    if row:
        return {
            "skill_name": row["term"],
            "evidence_reference": row["evidence_reference"],
        }
    return None


def _parse_response(
    response: str | dict[str, Any],
) -> tuple[dict[str, Any] | None, str | None]:
    if isinstance(response, str):
        if not response.strip():
            return None, "empty_response"
        try:
            parsed = json.loads(response)
        except json.JSONDecodeError:
            return None, "non_json_response"
    elif isinstance(response, dict):
        parsed = response
    else:
        return None, "unsafe_response_shape"
    if not parsed:
        return None, "empty_response"
    if not isinstance(parsed, dict):
        return None, "unsafe_response_shape"
    return parsed, None


def _collect_supported_values(
    payload: dict[str, Any],
) -> tuple[set[str], set[str], set[str], set[str], set[str]]:
    skill_names: set[str] = set()
    learning_targets: set[str] = set()
    studying_skills: set[str] = set()
    no_evidence_skills: set[str] = set()
    evidence_references: set[str] = set()

    for key, target_set in (
        ("verified_skills", skill_names),
        ("learning_target_skills", learning_targets),
        ("studying_skills", studying_skills),
        ("no_evidence_skills", no_evidence_skills),
    ):
        for item in payload.get(key, []):
            name = _normalise_text(item.get("skill_name"))
            reference = _normalise_text(item.get("evidence_reference"))
            if name:
                skill_names.add(name.lower())
                target_set.add(name.lower())
            if reference:
                evidence_references.add(reference)

    for term in payload.get("not_in_ledger_terms", []):
        value = _normalise_text(term)
        if value:
            skill_names.add(value.lower())

    for row in payload.get("matched_gap_rows", []):
        reference = _normalise_text(row.get("evidence_reference"))
        if reference:
            evidence_references.add(reference)

    for item in payload.get("project_evidence", []):
        reference = _normalise_text(item.get("evidence_reference"))
        if reference:
            evidence_references.add(reference)

    return (
        skill_names,
        learning_targets,
        studying_skills,
        no_evidence_skills,
        evidence_references,
    )


def _item_text(item: dict[str, Any]) -> str:
    return " ".join(
        _normalise_text(value)
        for key, value in item.items()
        if key != "evidence_reference" and isinstance(value, str)
    ).lower()


def validate_career_coach_response(
    response: str | dict[str, Any],
    *,
    evidence_payload: dict[str, Any],
) -> CareerCoachValidationResult:
    parsed, parse_error = _parse_response(response)
    if parse_error:
        return CareerCoachValidationResult(False, (parse_error,))

    errors: list[str] = []
    expected_keys = {*RESPONSE_LIST_KEYS, "manual_review_required"}
    if set(parsed) != expected_keys:
        errors.append("unsafe_response_shape")

    if parsed.get("manual_review_required") is not True:
        errors.append("manual_review_required_false")

    for key in RESPONSE_LIST_KEYS:
        if not isinstance(parsed.get(key), list):
            errors.append(f"{key}_must_be_list")

    supported, learning_targets, studying_skills, no_evidence_skills, references = (
        _collect_supported_values(evidence_payload)
    )

    for key in RESPONSE_LIST_KEYS:
        items = parsed.get(key)
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                errors.append(f"{key}_item_shape")
                continue
            skill = _normalise_text(item.get("skill"))
            if skill and skill.lower() not in supported:
                errors.append("unsupported_skill")
            reference = _normalise_text(item.get("evidence_reference"))
            if key in EVIDENCE_REFERENCED_RESPONSE_KEYS and reference not in references:
                errors.append("missing_evidence_reference")

            text = _item_text(item)
            skill_key = skill.lower()
            if skill_key in learning_targets and any(
                term in text for term in PROFICIENCY_OVERCLAIM_TERMS
            ):
                errors.append("learning_target_current_proficiency_overclaim")
            if skill_key in studying_skills and any(
                term in text for term in VERIFIED_OVERCLAIM_TERMS
            ):
                errors.append("studying_verified_overclaim")
            if skill_key in no_evidence_skills and any(
                term in text for term in VERIFIED_OVERCLAIM_TERMS
            ):
                errors.append("no_evidence_backed_overclaim")
            if "not in ledger" in text and "lacks the skill" in text:
                errors.append("not_in_ledger_lacks_skill_overclaim")
            if "employer-verified" in text:
                errors.append("verified_employer_overclaim")
            if any(term in text for term in FORBIDDEN_OUTCOME_TERMS):
                errors.append("forbidden_outcome_prediction")

    unique_errors = tuple(dict.fromkeys(errors))
    if unique_errors:
        return CareerCoachValidationResult(False, unique_errors, parsed_response=parsed)
    return CareerCoachValidationResult(True, (), parsed_response=parsed, safe_response=parsed)

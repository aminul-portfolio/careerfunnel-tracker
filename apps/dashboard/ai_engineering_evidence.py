"""Read-only AI engineering evidence contract for CareerFunnel Tracker.

Sprint 124 Phase 2.

This module exposes presentation-safe metadata describing AI engineering
capabilities already implemented and validated elsewhere in the repository.

It deliberately does not:
- construct or call providers;
- execute evaluation runners;
- access the network;
- query or write the database;
- read API keys or environment secrets;
- write files;
- perform background work.

Historical validation statements describe closed repository states. They are
not production reliability, accuracy, or service-level guarantees.
"""

from __future__ import annotations

from dataclasses import dataclass

EXECUTION_DETERMINISTIC = "DETERMINISTIC"
EXECUTION_RULE_BASED = "RULE-BASED"
EXECUTION_RAG = "RETRIEVAL / RAG"
EXECUTION_TOOL_CALLING = "BOUNDED TOOL-CALLING"
EXECUTION_LLM_ASSISTED = "LLM-ASSISTED"
EXECUTION_CONTROLLED_LIVE = "CONTROLLED LIVE CANARY"
EXECUTION_HUMAN_REVIEW = "HUMAN REVIEW"


@dataclass(frozen=True)
class AIEngineeringEvidenceItem:
    """One immutable, recruiter-readable AI engineering evidence item."""

    capability: str
    execution_type: str
    evidence_source: str
    evaluation_mode: str
    historical_validation: str
    human_review_required: bool
    claim_boundary: str
    provenance: str


@dataclass(frozen=True)
class AIEngineeringEvidenceSummary:
    """Immutable high-level summary of the evidence contract."""

    capability_count: int
    human_review_required: bool
    autonomous_agent_claim: bool
    production_vector_database_claim: bool
    enterprise_rag_claim: bool
    autonomous_job_application_claim: bool
    production_reliability_claim: bool


AI_ENGINEERING_EVIDENCE: tuple[AIEngineeringEvidenceItem, ...] = (
    AIEngineeringEvidenceItem(
        capability="Evidence-grounded AI application workflow",
        execution_type=EXECUTION_LLM_ASSISTED,
        evidence_source=(
            "Saved application evidence, Skill Ledger evidence, deterministic "
            "context assembly, validated output contracts, and manual review "
            "boundaries."
        ),
        evaluation_mode=(
            "Offline deterministic evaluation with controlled provider-boundary "
            "testing where explicitly enabled."
        ),
        historical_validation=(
            "Validated across closed CareerFunnel AI engineering sprints using "
            "repository tests, offline evaluation harnesses, and controlled "
            "integration checks."
        ),
        human_review_required=True,
        claim_boundary=(
            "Advisory workflow only. CareerFunnel does not autonomously apply for "
            "jobs, submit applications, save applications without user action, or "
            "make hiring decisions."
        ),
        provenance=(
            "Closed CareerFunnel AI workflow, evaluation, claim-safety, and "
            "human-review sprint evidence."
        ),
    ),
    AIEngineeringEvidenceItem(
        capability="Controlled LLM provider boundary",
        execution_type=EXECUTION_LLM_ASSISTED,
        evidence_source=(
            "Central provider-composition boundary with explicit configuration "
            "gates and validated fallback behaviour."
        ),
        evaluation_mode=(
            "Provider-boundary tests covering disabled, invalid, mocked, and "
            "explicitly permitted live execution states."
        ),
        historical_validation=(
            "Closed provider-boundary work validated that provider mode is "
            "authoritative and API key presence alone is insufficient to activate "
            "live execution."
        ),
        human_review_required=True,
        claim_boundary=(
            "This demonstrates controlled provider-boundary engineering. It does "
            "not claim continuously active production AI operation."
        ),
        provenance=(
            "Closed CareerFunnel live-provider boundary and telemetry validation "
            "evidence."
        ),
    ),
    AIEngineeringEvidenceItem(
        capability="RAG and retrieval evaluation",
        execution_type=EXECUTION_RAG,
        evidence_source=(
            "Small-scale private evidence corpus, cached embeddings, deterministic "
            "retrieval contracts, source attribution, and retrieval-safety cases."
        ),
        evaluation_mode="Offline deterministic RAG evaluation.",
        historical_validation=(
            "31 offline RAG evaluation cases passed in the validated Sprint 122 "
            "repository state."
        ),
        human_review_required=True,
        claim_boundary=(
            "Offline retrieval evaluation evidence only. This is not a production "
            "accuracy guarantee and does not represent a production vector database, "
            "ANN service, or enterprise RAG infrastructure."
        ),
        provenance=(
            "Sprint 120 RAG evaluation evidence incorporated into the validated "
            "Sprint 122 AI quality lifecycle."
        ),
    ),
    AIEngineeringEvidenceItem(
        capability="Bounded read-only tool-calling",
        execution_type=EXECUTION_TOOL_CALLING,
        evidence_source=(
            "Closed read-only tool registry, bounded call budget, deterministic "
            "planning contracts, source grounding, and synthesis validation."
        ),
        evaluation_mode="Offline deterministic tool-assistant evaluation.",
        historical_validation=(
            "81 offline tool-assistant evaluation cases passed in the validated "
            "Sprint 122 repository state."
        ),
        human_review_required=True,
        claim_boundary=(
            "The implemented workflow is bounded tool-calling, not an autonomous "
            "agent. It does not independently replan, submit applications, or perform "
            "unbounded external actions."
        ),
        provenance=(
            "Sprint 121 tool-assistant evaluation evidence incorporated into the "
            "validated Sprint 122 AI quality lifecycle."
        ),
    ),
    AIEngineeringEvidenceItem(
        capability="Claim-safety controls",
        execution_type=EXECUTION_RULE_BASED,
        evidence_source=(
            "Deterministic output validation, prohibited-claim checks, safe-rejection "
            "paths, evidence-alignment rules, and regression tests."
        ),
        evaluation_mode=(
            "Offline deterministic claim-safety and evidence-alignment evaluation."
        ),
        historical_validation=(
            "Closed evaluation suites validated accepted outputs, prohibited claims, "
            "evidence-grounding requirements, prompt-injection cases, and safe "
            "rejection behaviour."
        ),
        human_review_required=True,
        claim_boundary=(
            "Claim-safety controls reduce unsupported-output risk but do not guarantee "
            "perfect model behaviour or production accuracy."
        ),
        provenance=(
            "Closed CareerFunnel claim-safety, evidence-alignment, and adversarial "
            "evaluation evidence."
        ),
    ),
    AIEngineeringEvidenceItem(
        capability="Human-in-the-loop review",
        execution_type=EXECUTION_HUMAN_REVIEW,
        evidence_source=(
            "Manual approval boundaries across job analysis, application pre-fill, "
            "tracking, document review, and advisory AI outputs."
        ),
        evaluation_mode=(
            "Deterministic workflow and regression tests preserving manual-action "
            "boundaries."
        ),
        historical_validation=(
            "Validated repository workflows preserve Analyse - Review - Approve - "
            "Pre-fill Add Application - Manual Save behaviour."
        ),
        human_review_required=True,
        claim_boundary=(
            "AI and rule-based outputs are advisory. User review remains required "
            "before saving, submitting, publishing, or using evidence externally."
        ),
        provenance=(
            "Permanent CareerFunnel human-approval and claim-safety workflow "
            "contracts."
        ),
    ),
    AIEngineeringEvidenceItem(
        capability="AI quality lifecycle",
        execution_type=EXECUTION_DETERMINISTIC,
        evidence_source=(
            "Immutable evaluation case sets, provenance hashes, regression gates, "
            "quality snapshots, and deterministic CI-oriented quality checks."
        ),
        evaluation_mode="Offline deterministic AI quality lifecycle evaluation.",
        historical_validation=(
            "54 offline AI quality evaluation cases passed in the validated Sprint "
            "122 repository state."
        ),
        human_review_required=False,
        claim_boundary=(
            "This is deterministic regression-gating evidence. It is not a "
            "production SLA, uptime guarantee, model-accuracy guarantee, or production "
            "monitoring service."
        ),
        provenance=(
            "Sprint 122 AI observability and quality lifecycle closure evidence."
        ),
    ),
    AIEngineeringEvidenceItem(
        capability="Controlled live-provider canary",
        execution_type=EXECUTION_CONTROLLED_LIVE,
        evidence_source=(
            "Synthetic live-provider integration checks with explicit activation "
            "gates, request-integrity checks, strict call limits, zero retries, "
            "telemetry, and cost controls."
        ),
        evaluation_mode="Controlled synthetic live-provider integration canary.",
        historical_validation=(
            "Closed canary evidence includes a one-call, zero-retry, explicitly "
            "authorised live integration run under constrained test conditions."
        ),
        human_review_required=True,
        claim_boundary=(
            "Controlled integration evidence only. It does not prove production "
            "reliability, continuous live operation, production-scale throughput, or "
            "service-level performance."
        ),
        provenance=(
            "Closed controlled-live canary and provider telemetry evidence, including "
            "Sprint 116 evidence-alignment canary validation."
        ),
    ),
)


def build_ai_engineering_evidence() -> tuple[AIEngineeringEvidenceItem, ...]:
    """Return the immutable Sprint 124 AI engineering evidence catalogue."""

    return AI_ENGINEERING_EVIDENCE


def build_ai_engineering_summary() -> AIEngineeringEvidenceSummary:
    """Return claim-boundary metadata for presentation and regression tests."""

    return AIEngineeringEvidenceSummary(
        capability_count=len(AI_ENGINEERING_EVIDENCE),
        human_review_required=True,
        autonomous_agent_claim=False,
        production_vector_database_claim=False,
        enterprise_rag_claim=False,
        autonomous_job_application_claim=False,
        production_reliability_claim=False,
    )


__all__ = (
    "AIEngineeringEvidenceItem",
    "AIEngineeringEvidenceSummary",
    "AI_ENGINEERING_EVIDENCE",
    "EXECUTION_CONTROLLED_LIVE",
    "EXECUTION_DETERMINISTIC",
    "EXECUTION_HUMAN_REVIEW",
    "EXECUTION_LLM_ASSISTED",
    "EXECUTION_RAG",
    "EXECUTION_RULE_BASED",
    "EXECUTION_TOOL_CALLING",
    "build_ai_engineering_evidence",
    "build_ai_engineering_summary",
)
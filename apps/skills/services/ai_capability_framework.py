"""Manual, advisory AI Capability Framework for employability skill mapping (Sprint 53 Phase 1).

Based on AI Business Education PPTX concepts. No external AI calls, automation, or integrations.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

CapabilityLevel = Literal["foundation", "applied", "agent_portfolio_ready"]

APPROVED_CAPABILITY_LEVELS: frozenset[str] = frozenset({
    "foundation",
    "applied",
    "agent_portfolio_ready",
})

TOOL_EXAMPLES_DISCLAIMER = (
    "Example tools only - not integrated into CareerFunnel Tracker."
)

FRAMEWORK_CLAIM_SAFETY_NOTE = (
    "Advisory and manual only. This framework maps employability skills for self-review; "
    "it does not connect to external AI providers or unattended automated workflows."
)


@dataclass(frozen=True)
class AICapabilityCategory:
    slug: str
    title: str
    description: str
    level: CapabilityLevel
    evidence_examples: tuple[str, ...]
    career_relevance: str
    tool_examples: tuple[str, ...]
    claim_safety_note: str


def _tool_examples(*tools: str) -> tuple[str, ...]:
    return (TOOL_EXAMPLES_DISCLAIMER, *tools)


def _category(
    slug: str,
    title: str,
    description: str,
    level: CapabilityLevel,
    evidence_examples: tuple[str, ...],
    career_relevance: str,
    tool_examples: tuple[str, ...],
) -> AICapabilityCategory:
    return AICapabilityCategory(
        slug=slug,
        title=title,
        description=description,
        level=level,
        evidence_examples=evidence_examples,
        career_relevance=career_relevance,
        tool_examples=tool_examples,
        claim_safety_note=FRAMEWORK_CLAIM_SAFETY_NOTE,
    )


AI_CAPABILITY_FRAMEWORK: tuple[AICapabilityCategory, ...] = (
    _category(
        slug="prompt-engineering-ai-tool-proficiency",
        title="Prompt Engineering and AI Tool Proficiency",
        description=(
            "Write clear prompts, iterate on outputs, and use general-purpose AI assistants "
            "for research, drafting, and analysis support under manual review."
        ),
        level="foundation",
        evidence_examples=(
            "Saved prompt templates for JD analysis and stakeholder summaries.",
            "Before-and-after examples showing prompt refinement for clearer outputs.",
            "Notes on when to use AI assist versus manual analysis for a data task.",
        ),
        career_relevance=(
            "Data analyst roles increasingly expect efficient use of AI assistants for "
            "exploration, documentation, and communication - with human verification."
        ),
        tool_examples=_tool_examples("ChatGPT", "Copilot", "Gemini"),
    ),
    _category(
        slug="building-operating-ai-agents",
        title="Building and Operating AI Agents",
        description=(
            "Understand agent workflows, tool use, and guardrails for multi-step tasks. "
            "Design manual checkpoints rather than unattended autonomous execution."
        ),
        level="agent_portfolio_ready",
        evidence_examples=(
            "Diagram or write-up of an agent workflow with explicit human approval steps.",
            "Portfolio note describing tool boundaries and failure handling for an agent demo.",
            "Checklist for validating agent outputs before use in reporting or applications.",
        ),
        career_relevance=(
            "Shows readiness for analytics teams experimenting with agent-assisted pipelines "
            "while keeping accountability and auditability."
        ),
        tool_examples=_tool_examples("HuggingFace", "Genspark"),
    ),
    _category(
        slug="critical-evaluation-ai-output",
        title="Critical Evaluation of AI Output",
        description=(
            "Verify facts, spot hallucinations, assess bias, and reject unsourced claims "
            "before using AI-generated content in work products."
        ),
        level="foundation",
        evidence_examples=(
            "Redlined example where AI output was corrected after source checking.",
            "Short rubric for rating AI answer quality before reuse.",
            "Log of rejected AI suggestions with reasons documented.",
        ),
        career_relevance=(
            "Employers need analysts who treat AI output as draft material requiring "
            "validation, especially for metrics, definitions, and regulatory contexts."
        ),
        tool_examples=_tool_examples("ChatGPT", "Gemini"),
    ),
    _category(
        slug="ethical-ai-decision-making",
        title="Ethical AI Decision-Making",
        description=(
            "Apply privacy, fairness, transparency, and proportionality when choosing "
            "whether and how to use AI on sensitive or people-impacting data."
        ),
        level="foundation",
        evidence_examples=(
            "Decision log for when not to paste confidential data into public AI tools.",
            "Summary of bias risks in a sample dataset used with AI-assisted analysis.",
            "Plain-language note on disclosure when AI assisted a deliverable.",
        ),
        career_relevance=(
            "Demonstrates professional judgment for finance, HR, and customer analytics "
            "contexts where ethical use and data handling matter."
        ),
        tool_examples=_tool_examples("ChatGPT", "Copilot"),
    ),
    _category(
        slug="workflow-project-management-ai-tools",
        title="Workflow and Project-Management AI Tools",
        description=(
            "Use AI features inside productivity suites to plan tasks, summarize status, "
            "and organize job-search or project work with manual oversight."
        ),
        level="applied",
        evidence_examples=(
            "Screenshot or export of a job-search tracker enhanced with AI-generated summaries.",
            "Weekly plan showing AI-assisted task breakdown with manual edits highlighted.",
            "Template for turning meeting notes into action items with verification steps.",
        ),
        career_relevance=(
            "Shows ability to streamline analyst delivery workflows and personal productivity "
            "without losing control of priorities and deadlines."
        ),
        tool_examples=_tool_examples("Notion AI"),
    ),
    _category(
        slug="collaborative-strategy-ideation-tools",
        title="Collaborative Strategy and Ideation Tools",
        description=(
            "Facilitate brainstorming, journey mapping, and workshop prep using AI-assisted "
            "collaboration boards under team or self-directed review."
        ),
        level="applied",
        evidence_examples=(
            "Board snapshot from a stakeholder journey or KPI ideation session.",
            "Facilitation plan showing where AI suggestions were accepted or discarded.",
            "Summary of how AI sped up workshop prep while keeping facilitator ownership.",
        ),
        career_relevance=(
            "Useful for cross-functional analytics roles involving workshops, discovery, "
            "and structured problem framing with stakeholders."
        ),
        tool_examples=_tool_examples("Miro AI"),
    ),
    _category(
        slug="ai-product-design-packaging-tools",
        title="AI Product, Design, and Packaging Tools",
        description=(
            "Apply AI-assisted design tools for mockups, packaging concepts, and visual "
            "storytelling that supports portfolio and presentation work."
        ),
        level="applied",
        evidence_examples=(
            "Portfolio thumbnail or mockup created with AI assist and manual refinement.",
            "Before-and-after of a chart or dashboard layout improved with design AI.",
            "Caption explaining human edits applied after AI-generated visuals.",
        ),
        career_relevance=(
            "Helps data analysts present insights professionally in portfolios, decks, "
            "and stakeholder-facing materials."
        ),
        tool_examples=_tool_examples("Canva AI", "Pacdora AI"),
    ),
    _category(
        slug="ai-video-media-generation-tools",
        title="AI Video and Media Generation Tools",
        description=(
            "Create short explainer clips, b-roll, or media assets to support portfolio "
            "demos and learning content, with clear manual curation."
        ),
        level="agent_portfolio_ready",
        evidence_examples=(
            "Short demo reel or clip introducing a portfolio project with AI-assisted media.",
            "Storyboard noting which segments were AI-generated versus recorded manually.",
            "Accessibility checklist applied to AI-generated captions or voiceover.",
        ),
        career_relevance=(
            "Differentiates candidates who can communicate analysis outcomes through modern "
            "media formats for interviews and portfolio reviews."
        ),
        tool_examples=_tool_examples("Canva AI", "Genspark"),
    ),
    _category(
        slug="ai-presentation-report-generation-tools",
        title="AI Presentation and Report Generation Tools",
        description=(
            "Draft slide outlines, executive summaries, and report structures using AI "
            "assistants, then validate data and messaging manually before sharing."
        ),
        level="applied",
        evidence_examples=(
            "Slide outline generated with AI and revised with verified metrics.",
            "Executive summary where every statistic was manually source-checked.",
            "Template for turning analysis notebooks into stakeholder-ready reports.",
        ),
        career_relevance=(
            "Core for analyst roles that require recurring reporting, board packs, "
            "and interview case presentations with credible numbers."
        ),
        tool_examples=_tool_examples("ChatGPT", "Copilot", "Canva AI"),
    ),
)


def get_ai_capability_framework() -> tuple[AICapabilityCategory, ...]:
    """Return the full advisory AI capability framework."""
    return AI_CAPABILITY_FRAMEWORK

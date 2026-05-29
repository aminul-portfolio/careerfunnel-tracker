# Sprint 53 - PPTX AI Capability Framework Evidence

## 1. Sprint Objective

Sprint 53 adds a manual, advisory **AI Capability Framework** to CareerFunnel Tracker. The framework is based on capability categories inspired by the uploaded AI Business Education PPTX model. This sprint creates a read-only reference surface for employability skill mapping - not scoring, job matching, recommendations, external AI calls, or automation.

**Branch:** `sprint-53-pptx-ai-capability-framework`

**Phase commits:**

| Phase | Commit | Scope |
| --- | --- | --- |
| Phase 1 | `e1e85fe` | Framework service and service tests |
| Phase 2 | `110e6cc` | Read-only page, URL, navigation, view tests |
| Phase 3 | (this document) | Evidence documentation and sprint closure prep |

---

## 2. What Sprint 53 Added

### Phase 1 - Framework foundation

- New module `apps/skills/services/ai_capability_framework.py`
- Frozen dataclass `AICapabilityCategory` with slug, title, description, level, evidence examples, career relevance, tool examples, and claim-safety note
- Nine capability categories stored as plain Python data (no database models or migrations)
- Accessor `get_ai_capability_framework()` returning the full framework tuple
- Approved learning levels: `foundation`, `applied`, `agent_portfolio_ready`

### Phase 2 - Read-only UI surface

- Login-required GET page at `/skills/ai-capability-framework/`
- View reads framework data from the Phase 1 service only (no duplicated framework data in templates or views)
- Intelligence sidebar link: **AI Capability Framework**
- Claim-safe hero copy stating manual/advisory scope and example-tool boundaries

### Phase 3 - Evidence and closure

- This evidence document
- Evidence index entry in `docs/evidence/evidence_index.md`

---

## 3. PPTX Concept Mapping

The framework is based on capability categories inspired by the PPTX AI Business Education model. CareerFunnel Tracker does not integrate with any listed tools.

| PPTX capability theme | Framework slug | Level |
| --- | --- | --- |
| Prompt engineering and AI tool proficiency | `prompt-engineering-ai-tool-proficiency` | Foundation |
| Building and operating AI agents | `building-operating-ai-agents` | Agent / portfolio-ready |
| Critical evaluation of AI output | `critical-evaluation-ai-output` | Foundation |
| Ethical AI decision-making | `ethical-ai-decision-making` | Foundation |
| Workflow and project-management AI tools | `workflow-project-management-ai-tools` | Applied |
| Collaborative strategy and ideation tools | `collaborative-strategy-ideation-tools` | Applied |
| AI product / design / packaging tools | `ai-product-design-packaging-tools` | Applied |
| AI video / media generation tools | `ai-video-media-generation-tools` | Agent / portfolio-ready |
| AI presentation and report generation tools | `ai-presentation-report-generation-tools` | Applied |

**Learning progression (PPTX-inspired, advisory only):**

- **Foundation** - core literacy: prompts, evaluation, ethics
- **Applied** - workflow, collaboration, design, and reporting use cases
- **Agent / portfolio-ready** - agent workflows and media/presentation depth suitable for portfolio evidence

**Tool names in the service are examples only.** They illustrate the type of tool a candidate might reference in portfolio evidence. They are not product integrations.

---

## 4. How to Review the Feature

1. Start local dev server and log in (existing project convention).
2. Open **Intelligence -> AI Capability Framework** in the sidebar, or navigate directly to:

```text
/skills/ai-capability-framework/
```

3. Confirm the page title **AI Capability Framework** and manual/advisory hero copy.
4. Scroll through all nine capability cards. Each should show title, level, description, evidence examples, career relevance, tool examples (with example-only disclaimer), and claim-safety note.
5. Confirm no scores, job matches, recommendations, or generated AI output appear on the page.

---

## 5. Main Implementation Evidence

| Layer | Path | Role |
| --- | --- | --- |
| Service | `apps/skills/services/ai_capability_framework.py` | Canonical framework data and `get_ai_capability_framework()` |
| Service exports | `apps/skills/services/__init__.py` | Public service imports |
| View | `apps/skills/views.py` | Login-required read-only render |
| URLs | `apps/skills/urls.py` | Route `ai-capability-framework/` |
| Project URLs | `config/urls.py` | Mount at `/skills/` |
| Template | `templates/skills/ai_capability_framework.html` | Read-only display |
| Navigation | `templates/partials/sidebar.html` | Intelligence group link |

**Not added:** models, migrations, CSS, JavaScript, scoring services, matching services, recommendation services, external AI provider calls.

---

## 6. Test Coverage Summary

**Service tests:** `apps/skills/tests/test_ai_capability_framework.py` (8 tests)

| Test focus | Proves |
| --- | --- |
| Non-empty framework | Service returns data |
| Required fields | Every capability is complete |
| Unique slugs | No duplicate identifiers |
| Approved levels only | `foundation`, `applied`, `agent_portfolio_ready` |
| Tool example labelling | Example-only disclaimer present |
| Claim-safety notes | Advisory, manual, external-AI boundary language |
| Forbidden phrase guard | Service text avoids auto-apply, scraping, Gmail, etc. |

**View tests:** `apps/skills/tests/test_ai_capability_framework_view.py` (8 tests)

| Test focus | Proves |
| --- | --- |
| HTTP 200 | Page renders when authenticated |
| Page title | "AI Capability Framework" visible |
| Service-backed content | At least one capability title from service |
| Manual/advisory copy | Page states manual and advisory scope |
| Example tools copy | "Example tools only" or equivalent |
| Forbidden phrase guard | Page HTML avoids listed claim phrases |
| Login required | Unauthenticated users redirected |
| Context integrity | View passes service framework unchanged |

**Combined `apps.skills` total:** 16 tests.

**Validation commands:**

```powershell
python manage.py test apps.skills
python manage.py test
ruff check .
python manage.py check
python manage.py makemigrations --check --dry-run
```

---

## 7. What Is Intentionally NOT Implemented Yet

Sprint 53 stops at a manual reference framework. The following are out of scope and deferred to later sprints (for example Sprint 54+):

- Readiness scoring or numeric capability scores
- Job matching against saved applications or job descriptions
- Recommendation engine or "next best capability" logic
- Dashboard widgets or funnel metrics integration
- User progress tracking or self-assessment forms
- External AI provider calls from this feature
- Autonomous agent execution
- Tool integrations (Notion AI, Miro AI, Pacdora AI, HuggingFace, Genspark, Canva AI, ChatGPT, Copilot, Gemini, or any third-party API)
- Database persistence of framework entries or user ratings
- Auto-apply, auto-send, scraping, Gmail, Calendar, billing workflows

---

## 8. Claim-Safety Boundaries

This sprint is **manual and advisory only**.

| Boundary | Sprint 53 behaviour |
| --- | --- |
| Manual and advisory | Framework is self-review reference; user decides what to cite |
| Tool names are examples only | Disclaimer on page and in service data; no integrations claimed |
| No external AI calls | Page renders static service data; no provider invoked |
| No automation | GET-only page; no background jobs or workflows triggered |
| No scoring yet | No numeric readiness or fit scores on this page |
| No job matching yet | No comparison to applications or JD text |
| No recommendations yet | No ranked actions or suggested next steps |
| No scraping | No web data collection |
| No auto-apply | No application submission |
| No auto-send | No outbound email or messaging |
| No Gmail or Calendar integration | No inbox or calendar sync |
| No billing | No payment or subscription workflow |
| No live SaaS users, customers, or production deployment | Local portfolio demo only |

**Allowed documentation wording:**

- "Tool names are examples only."
- "The framework is based on capability categories inspired by the PPTX model."
- "This sprint creates a manual, advisory framework surface."
- "No external AI provider is called by this feature."

**Forbidden documentation wording (not used in Sprint 53):**

- "CareerFunnel uses Notion AI..."
- "CareerFunnel generates AI recommendations..."
- "CareerFunnel automatically matches jobs..."
- "CareerFunnel automates applications..."
- "Production-ready AI platform..."
- "Live SaaS customers..."
- "Gmail integration..." / "Calendar integration..."

---

## 9. ASCII / Encoding Note

Sprint 53 copy uses ASCII hyphens, straight apostrophes, and plain punctuation in new service, template, and evidence text. No mojibake artifacts (for example garbled em dashes or curly punctuation) were introduced.

---

## 10. Sprint 54 Not Started

No Sprint 54 scoring, matching, recommendation, dashboard, or integration work is included in Sprint 53. Closure tag and merge steps remain for the maintainer after Phase 3 review.

# Sprint 60 - Application Document Pack Workflow Evidence / Final Closure

## Sprint objective

Sprint 60 delivers a manual-review Application Document Pack workflow on each job application record. The flow connects existing job analysis fields to rule-based draft CV tailoring notes and draft cover-letter text, saves those drafts as database records, lets the user select CV and cover-letter records for call review, and downloads text-based DOCX/PDF exports on request.

Sprint 60 does **not** add automatic job submission, file upload, media storage, Gmail/Calendar/OAuth integration, scraping, auto-apply, or external AI/API calls.

**Branch:** `sprint-60-phase-6-final-validation-docs-closure`

**Validation baseline:** **828** automated tests passing

---

## End-to-end workflow

```text
Job analysis (Smart Review / saved application fields)
-> Generate Draft Application Documents (preview only)
-> Save Drafts to Application Document Pack (ApplicationDocument records)
-> Application Detail: Application Document Pack display
-> Select saved CV and cover-letter documents
-> Quick Call Review block (selected-document context)
-> Download DOCX / Download PDF (generated on request from saved text)
-> Manual review before employer use
```

Key routes (login required):

| Step | Route |
| --- | --- |
| Application Smart Review | `/applications/<pk>/smart-review/` (`job_intelligence:application_smart_review`) |
| Application Detail / Document Pack | `/applications/<pk>/` (`applications:application_detail#document-pack`) |
| Document download | `/applications/<pk>/documents/<document_pk>/download/<docx\|pdf>/` |

---

## Completed phases 1-6

### Phase 1 - ApplicationDocument foundation

- **Model:** `ApplicationDocument` on `JobApplication` (`apps/applications/models.py`)
- **Admin:** registered in `apps/applications/admin.py`
- **Migration:** `apps/applications/migrations/0004_applicationdocument.py`
- **UI:** Application Document Pack section on Application Detail (`templates/applications/application_detail.html`)
- **Choices:** document type, status, source in `apps/applications/choices.py`

### Phase 2 - Draft CV and cover-letter generation (preview only)

- **Service:** `apps/job_intelligence/draft_documents.py` - `build_application_document_drafts()`
- **Views:** generate action on Application Smart Review and Job Posting Analyzer preview path
- **Templates:** `templates/job_intelligence/application_smart_review.html`, `templates/job_intelligence/_application_document_drafts.html`, `templates/ai_agents/job_posting_analyzer.html`
- **Behaviour:** rule-based Draft CV Tailoring Notes and Draft Cover Letter; preview only until save

### Phase 3 - Save generated drafts to document pack

- **Service:** `save_application_document_drafts()` in `apps/job_intelligence/draft_documents.py`
- **View action:** `save_drafts` POST on Application Smart Review
- **Records:** creates two `ApplicationDocument` rows (CV + cover letter), status `draft`, source `job_analyzer`

### Phase 4 - Select saved CV and cover-letter documents

- **Migration:** `apps/applications/migrations/0005_jobapplication_selected_cover_letter_document_and_more.py`
- **Form:** `ApplicationDocumentSelectionForm` (`apps/applications/forms.py`)
- **View:** `select_documents` POST on Application Detail (`apps/applications/views.py`)
- **UI:** Selected Documents, Select Documents form, Quick Call Review block

### Phase 5 - Download saved document records as DOCX/PDF

- **Service:** `apps/applications/document_exports.py` - standard-library DOCX (ZIP/OOXML) and PDF generation
- **Route:** `applications:application_document_download`
- **View:** `application_document_download` in `apps/applications/views.py`
- **No** committed export files, **no** media storage, **no** dependency changes

### Phase 6 - Final validation and closure

- Full validation stack (Ruff, Django check, migration check, **828** tests)
- End-to-end workflow verified via automated tests and manual screenshot checklist
- This evidence document and README alignment
- Claim-safety review; no new product features
- Copy drift cleanup: `CAREERFUNNEL_EVIDENCE` draft wording aligned to **828 automated tests after Sprint 60 Phase 5**

---

## Files / features changed by phase

| Phase | Primary files |
| --- | --- |
| 1 | `models.py`, `admin.py`, `choices.py`, `0004_applicationdocument.py`, `application_detail.html`, `tests.py` |
| 2 | `draft_documents.py`, `job_intelligence/views.py`, `ai_agents/views.py`, smart review + analyzer templates, `job_intelligence/tests.py` |
| 3 | `draft_documents.py` (save), `job_intelligence/views.py`, templates, tests |
| 4 | `forms.py`, `models.py`, `views.py`, `0005_...`, `application_detail.html`, `tests.py` |
| 5 | `document_exports.py`, `urls.py`, `views.py`, `application_detail.html`, `tests.py` |
| 6 | `docs/evidence/sprint_60_application_document_pack_closure.md`, README (minimal), this closure package |

---

## Validation summary

| Check | Result |
| --- | --- |
| `ruff check .` | Pass |
| `python manage.py check` | Pass (0 issues) |
| `python manage.py makemigrations --check --dry-run` | No changes detected |
| `python manage.py test` | **828** tests, OK |
| `git diff --check` | Clean |
| Generated DOCX/PDF in repo | None committed |
| Media / FileField upload | Not added |

---

## Screenshot evidence

Screenshots were **not** captured in Phase 6 (local dev server + browser capture not run from Cursor). Use the manual checklist below before external publishing.

**Target folder (create on capture):**

```text
docs/screenshots/application_documents/
```

**Required filenames and content:**

| File | Must show |
| --- | --- |
| `sprint60_01_draft_application_documents_preview.png` | Application Smart Review after **Generate Draft Application Documents** - Draft CV Tailoring Notes, Draft Cover Letter, manual-review disclaimer, no save yet |
| `sprint60_02_save_drafts_to_application_document_pack.png` | Same page after **Save Drafts to Application Document Pack** - success message and link to Document Pack |
| `sprint60_03_application_document_pack_saved_records.png` | Application Detail `#document-pack` - table with saved CV and cover-letter record names, status, source |
| `sprint60_04_selected_cv_cover_letter_workflow.png` | Select Documents form with CV and cover-letter dropdowns; Selected Documents showing chosen names |
| `sprint60_05_download_docx_pdf_links.png` | Document Pack table **Downloads** column with Download DOCX and Download PDF links |
| `sprint60_06_quick_call_review_selected_documents.png` | Quick Call Review block with selected CV/cover-letter names and claim-safety / manual-review wording |

Do not commit placeholder images. Only add real local browser captures.

---

## Claim-safety confirmation

- Draft records only - not labelled as final CV or final cover letter
- Rule-based generation from saved application/job-analysis fields; no external AI/API calls in this sprint
- User must review manually before uploading or sending to employers
- No automatic submission, auto-apply, scraping, Gmail, Calendar, or OAuth
- No file upload or media storage; downloads generated on request from database text
- No live SaaS, production-user, customer, billing, or subscription claims

---

## Known limitations

- DOCX/PDF exports are **text-based renderings** of saved `ApplicationDocument` fields (title, content, tailoring notes, project evidence, claim-safety notes, quick call notes). They are not formatted Word/PDF replicas of a designed CV layout.
- Downloads are generated on each request and are **not** stored as media files.
- Job Posting Analyzer can preview drafts but saving requires an application record via Application Smart Review.
- Quick call notes appear only when saved on selected document records.

---

## Next recommended sprint (optional)

- Capture and commit the six Sprint 60 screenshots after local UI walkthrough
- Merge Sprint 60 to `main` with tag `sprint-60-application-document-pack-complete`
- Update `docs/evidence/evidence_index.md` checkpoint row when merged
- Optional: evidence-bank integration (Sprint 33+ scope) - only when explicitly instructed

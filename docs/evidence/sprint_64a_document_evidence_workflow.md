# Sprint 64A - Document Evidence Workflow

Date: 2026-06-14
Scope: Application Detail Document Pack and evidence readiness only (Phase 1)

## Issue summary

Evidence Readiness treated CV and cover letter preparation as complete only when
`application.cv_version` or `application.cover_letter_version` text fields were saved.
Selected ApplicationDocument records and uploaded/external document records were not
counted. The Document Pack UI could not create external references or upload files,
and selected CV display used a generated professional basename instead of the saved
document name.

## Root cause

1. `_has_cv_version()` and `_has_cover_letter_version()` checked manual version
   strings only.
2. Document Pack UI supported selection and download of existing records only.
3. Upload helpers existed in `document_uploads.py` but were not wired to Application
   Detail.
4. Template copy stated no upload/file storage in this phase.

## Changed files

- apps/applications/choices.py - added `EXTERNAL_REFERENCE` source and
  `DOCUMENT_PACK_UPLOAD_EXTENSIONS`
- apps/applications/services.py - expanded readiness helpers and source display labels
- apps/applications/models.py - added `evidence_source_label()` helper method
- apps/applications/document_uploads.py - external reference and document-pack upload
  helpers
- apps/applications/forms.py - external reference and upload forms
- apps/applications/views.py - Application Detail POST actions for create/upload
- templates/applications/application_detail.html - Document Pack UI and labels
- apps/applications/tests.py - readiness and workflow integration tests
- apps/applications/tests_document_upload_workflow.py - upload validation/service tests
- docs/evidence/sprint_64a_document_evidence_workflow.md

## Migration

Migration required: `0007_alter_applicationdocument_source.py`

Reason: Django `AlterField` on `ApplicationDocument.source` to register the new
`external_reference` choice value on the model field.

## Readiness logic implemented

CV readiness passes when any of:

- `application.selected_cv_document` is set
- `application.cv_version` stripped is non-empty
- an `ApplicationDocument` with `document_type=CV` exists for the application

Cover-letter readiness passes when any of:

- `application.selected_cover_letter_document` is set
- `application.cover_letter_version` stripped is non-empty
- an `ApplicationDocument` with `document_type=COVER_LETTER` exists for the application

Labels unchanged:

- "CV version saved"
- "Cover letter version saved"

## External reference workflow

Application Detail Document Pack forms:

- Create external CV reference
- Create external cover letter reference

Required: version/name. Optional: notes (stored in `tailoring_notes`).
Creates `ApplicationDocument` with source `external_reference`, status
`ready_for_manual_submission`, no uploaded file.

## Upload workflow

Application Detail Document Pack forms:

- Upload CV
- Upload cover letter

Accepts `.docx` and `.pdf` only for this UI workflow. Rejects invalid types.
Preserves original filename in `name` and `original_filename`. Source label shown as
"Manual upload". No automatic employer submission implied.

## Source UI labels

- Generated document - manual, job analyzer, master CV baseline sources
- Manual upload - user upload source
- External reference - external reference source

## Tests added/updated

Readiness:

- manual CV version text only
- manual cover letter version text only
- CV ApplicationDocument without manual version
- cover-letter ApplicationDocument without manual version
- selected CV document without manual version

Workflow:

- external CV reference without upload
- external cover letter reference without upload
- upload DOCX CV
- upload PDF cover letter
- invalid upload type rejected
- uploaded records appear in selection list
- selecting documents clears Document Pack missing display
- generated/manual/external source labels

Existing generated document selection and download tests retained.

## Manual verification notes

1. Open an application with blank CV/cover letter version fields.
2. Create an external CV reference and confirm it appears in the document table.
3. Upload a PDF cover letter and confirm it appears in the selection dropdown.
4. Select CV and cover letter documents and confirm "Selection still needed" clears.
5. Confirm Evidence Readiness shows "CV version saved" and "Cover letter version saved".
6. Confirm Assets section still distinguishes saved manual CV Version from generated
   basename when manual version is blank.

## Claim-safety

- Manual review required before employer submission
- No automatic submission
- No employer portal, Gmail, Outlook, or live AI generation claims

## Remaining limitations / backlog

- [UNKNOWN] Whether uploaded PDF/DOCX text extraction will feed AI analysis workflows
  beyond current manual-review messaging.
- Save-quality analytics warnings still key off blank `cv_version` only; document
  evidence does not yet suppress CV Version Performance analytics warnings.
- Document Pack downloads for uploaded files may still render from saved text content
  when no extracted text exists; review manually before employer use.
- TXT uploads remain supported elsewhere via `attach_uploaded_document()` but not in
  Document Pack UI (by design for this sprint).

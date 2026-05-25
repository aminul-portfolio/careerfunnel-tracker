# Sprint 40B - Source + CV Reports + Search/Filter/Pagination Evidence

## 1. Sprint Objective

Sprint 40B adds reusable reporting table, search, filter, and pagination patterns to the metrics reporting suite, and upgrades:

1. **Source Performance** report
2. **CV Version Performance** report

This sprint is **reporting-only**. It preserves Sprint 40A foundation behaviour and does not implement Sprint 40C weekly trend expansion, rejection pattern expansion, visual analytics evidence, export centre polish, dashboard/forms changes, or model/migration changes.

**Branch:** `sprint-40b-source-cv-reports-search-filter-pagination`

---

## 2. Source Performance Report Summary

**Service:** `build_source_performance_report(user, query_params)` in `apps/metrics/services.py`

| Element | Description |
| --- | --- |
| Source name | `source_label` from grouped `JobApplication` records |
| Application count | Total applications per source |
| Responses / rate | Response count and percentage |
| Interviews / rate | Interview-stage count and percentage |
| Offers / rate | Offer count and percentage |
| Advisory interpretation | Evidence-based leader summary from full source dataset |
| Manual workflow links | Application create and application list |
| Search | `src_q` - case-insensitive match on source label/code |
| Filters | `src_filter` - all, has responses, no responses, has interviews, has offers |
| Pagination | `src_page`, `src_pp` (2/5/10 rows per page) |
| Data-quality badges | Response/interview/offer rate badge classes on table cells |

---

## 3. CV Version Performance Report Summary

**Service:** `build_cv_version_performance_report(user, query_params)` in `apps/metrics/services.py`

| Element | Description |
| --- | --- |
| CV version | Grouped `cv_version` (blank -> Unspecified) |
| Application count | Total per version |
| Responses / rate | Response count and percentage |
| Interviews / rate | Interview-stage count and percentage |
| Offers / rate | Offer count and percentage |
| Advisory interpretation | Directional CV leader summary (not A/B testing) |
| Manual workflow links | Application list and evaluation queue |
| Search | `cv_q` - case-insensitive match on CV version text |
| Filters | `cv_filter` - all, has responses, no responses, unspecified, has rejections |
| Pagination | `cv_page`, `cv_pp` |
| Data-quality badges | Rate badge classes on table cells |

Underlying aggregates remain in `build_source_roi` and `build_cv_version_performance` (ORM annotations, no N+1 row queries).

---

## 4. Shared Table / Search / Filter / Pagination Pattern

**Templates:** `templates/metrics/partials/`

| Partial | Purpose |
| --- | --- |
| `report_filter_bar.html` | Search box, filter select, rows-per-page, apply + reset |
| `report_table.html` | Result count, desktop table, mobile card layout, filtered/unfiltered empty states |
| `report_pagination.html` | Previous/next links, page summary, query preservation |
| `source_performance_report.html` | Sprint 40B source section |
| `cv_version_performance_report.html` | Sprint 40B CV section |

**Shared behaviours:**

- Active filter chips when search or non-default filter is applied
- Reset filters link clears only that report's query parameters while preserving the other report's parameters
- Hidden fields preserve cross-report query parameters on filter submit
- Filtered empty state when rows exist globally but none match filters
- Result count: "Showing X of Y matching rows (Z total)"

**Query parameter prefixes:**

- Source report: `src_q`, `src_filter`, `src_page`, `src_pp`
- CV report: `cv_q`, `cv_filter`, `cv_page`, `cv_pp`

---

## 5. Pagination Safeguards

Sprint 40B uses **Django's `Paginator`** for portfolio-scale reporting (acceptable for local SQLite and single-user usage).

| Safeguard | Implementation |
| --- | --- |
| Invalid page number | Non-integer values fall back to page 1 |
| Page out of range | `EmptyPage` falls back to the last page |
| Per-page bounds | Allowed values: 2, 5, 10 (default 5) |
| Query preservation | Pagination URLs retain search, filter, per-page, and the other report's parameters |
| Read-only GET | Pagination is link-based GET only - no record mutation |

---

## 6. Manual Workflow / Action-Link Safety

- Source report links: manual application create and application list
- CV report links: manual application list and evaluation queue
- No automatic status updates, submissions, or background jobs triggered by reporting GET
- Legacy weekly trend and rejection sections remain in a dashed Sprint 40C block without expansion

---

## 7. Claim-Safety Confirmation

Reporting copy remains **advisory and evidence-based**:

- CV performance described as directional tracking, not automated A/B testing
- Interpretations reference stored records only
- Page trust note confirms reporting GET is read-only
- No auto-apply, OAuth, Gmail, calendar, live SaaS, or production deployment claims added

---

## 8. What Was Deliberately Not Changed

- Models, migrations, and database schema
- Dashboard templates and dashboard services
- Forms and export centre polish
- Recruiter email and interview prep workflow logic
- Sprint 40C rejection pattern expansion
- Sprint 40C weekly trend expansion
- Sprint 40C visual analytics / Tableau evidence
- README public claims and GitHub workflow files

---

## 9. Test Coverage Summary

**File:** `apps/metrics/tests.py`

| Test class | New tests | Focus |
| --- | ---: | --- |
| `PremiumReportingSourceCvTests` | 15 | Source/CV reports, filter bar, table, pagination, search/filter, chips/reset, query preservation, empty filtered state, mutation safety, 40C scope guard, claim safety |

Key tests:

- `test_source_performance_report_renders`
- `test_cv_version_performance_report_renders`
- `test_report_filter_bar_renders`
- `test_report_table_renders`
- `test_report_pagination_renders`
- `test_search_filters_source_report`
- `test_search_filters_cv_report`
- `test_filter_chips_and_reset_link_render`
- `test_pagination_first_second_last_page`
- `test_invalid_page_falls_back_safely`
- `test_query_parameters_preserved_across_pagination`
- `test_empty_filtered_state_renders`
- `test_reporting_get_does_not_mutate_records`
- `test_sprint_40c_scope_not_implemented`
- `test_reporting_copy_remains_claim_safe`

**Metrics suite:** **112 tests** passing (includes Sprint 40A foundation and existing service/view tests).

`PremiumReportingFoundationTests` updated for Sprint 40C primary-nav scope guard.

---

## 10. Validation Commands

```powershell
ruff check .
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test apps.metrics.tests
```

---

## Files Changed (Sprint 40B)

- `apps/metrics/services.py`
- `apps/metrics/views.py`
- `apps/metrics/tests.py`
- `templates/metrics/funnel_metrics.html`
- `templates/metrics/partials/report_filter_bar.html` (new)
- `templates/metrics/partials/report_table.html` (new)
- `templates/metrics/partials/report_pagination.html` (new)
- `templates/metrics/partials/source_performance_report.html` (new)
- `templates/metrics/partials/cv_version_performance_report.html` (new)
- `static/css/components.css`
- `docs/evidence/sprint_40b_source_cv_reports_search_filter_pagination.md`
- `docs/evidence/evidence_index.md`

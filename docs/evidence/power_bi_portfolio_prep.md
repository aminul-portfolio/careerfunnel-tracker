# Power BI Portfolio Evidence Prep

## Status banner

**Power BI artifact status: in progress / preparation only.**

This document is a preparation plan. It is not proof of completed Power BI delivery.

The following are **not approved yet**:

- No local `.pbix` file is committed or claimable.
- No Power BI screenshot evidence is approved for public use.
- No public README claim that Power BI is implemented or portfolio-complete.
- No CV claim that Power BI is a proven portfolio skill.
- No LinkedIn claim that Power BI work is finished or production-ready.

Power BI remains an in-progress target skill until a local artifact is built, evidenced, and reviewed under the checklist below.

---

## Dataset plan

Future Power BI work must use **existing demo CSV exports only**. Do not import real applicant records, job descriptions, contact details, or other private job-search data.

| File | Purpose |
|------|---------|
| `dashboards/data/applications.csv` | Application funnel, source, CV version, pipeline stage, quality flags |
| `dashboards/data/daily_logs.csv` | Daily target vs actual application activity and hours spent |

Describe these files as **demo CSVs suitable for future Power BI import**. Do not describe them as "Power BI-ready exports" or imply that a Power BI dashboard already exists.

**Privacy rules for any future export extension:**

- Demo user only (`demo` username enforced by the export command).
- No PII: no job URLs, contact names, contact emails, notes, job description text, or required skills text.
- Quality fields remain yes/no flags only, matching the current dashboard CSV schema.

---

## Reproducibility notes

Regenerate demo dashboard CSVs from the project root using the existing documented commands:

```powershell
python manage.py seed_demo_data
python manage.py export_for_dashboards
```

The export command writes:

- `dashboards/data/applications.csv`
- `dashboards/data/daily_logs.csv`

See also `dashboards/README.md` for schema details and safety notes.

If demo data is missing, run the existing documented demo-data setup first, then export dashboard CSVs. Do not invent alternate seed or export commands.

---

## Business questions

These questions guide a future local Power BI dashboard build. They do not claim that a dashboard already answers them.

1. How many applications are moving through each funnel stage?
2. Which sources generate stronger application outcomes?
3. Are daily application targets being met?
4. Which CV version is associated with better progression?
5. Where do quality flags or missing evidence create application risk?
6. How does application activity trend over time?
7. What proportion of applications are waiting for review, follow-up, or decision?
8. What share of applications meet analytics-ready quality standards?

---

## KPI index

Full definitions live in [docs/analytics/metric_definitions.md](../analytics/metric_definitions.md). Do not duplicate long definitions here. Use the canonical document when building or explaining dashboard metrics.

| KPI | Short note |
|-----|------------|
| Total Applications | Base count of logged applications |
| Response Rate | Share of applications receiving any company response |
| Interview Rate | Share progressing to interview stages |
| Daily Target Hit Rate | How often daily application targets are met |
| Source ROI | Outcome strength by application source |
| CV Version Performance | Progression patterns by CV version used |
| Analytics-Ready Rate | Share of applications meeting quality-readiness rules |
| Quality Issue Rate | Share of applications with missing or weak evidence fields |

---

## Evidence checklist

Future Power BI evidence is **not claimable** until **all** of the following are true:

- [ ] Local `.pbix` built from demo CSVs (`applications.csv`, `daily_logs.csv`)
- [ ] At least 2 screenshot pages captured (e.g. funnel/overview and quality/activity views)
- [ ] Dashboard metrics trace back to demo CSVs and [docs/analytics/metric_definitions.md](../analytics/metric_definitions.md)
- [ ] No real personal or job-contact data exposed in the workbook, screenshots, or repo
- [ ] README, CV, and LinkedIn wording reviewed separately before any public Power BI claim
- [ ] Git branch merged, tagged, pushed, and CI passed for any repository documentation changes

Until every item is checked, treat Power BI as preparation-only in all employer-facing materials.

---

## Claim-safety wording

### Allowed wording

- "Power BI portfolio artifact preparation is in progress."
- "Demo CSV exports have been identified for future Power BI import."
- "A Power BI evidence checklist has been defined."
- "Local Tableau evidence exists; Power BI work is a separate future artifact."
- "I am building Power BI skills; dashboard evidence will be added when verified."

### Blocked wording

- "Power BI dashboard implemented."
- "Power BI portfolio completed."
- "Production Power BI reporting."
- "Power BI integration."
- "Automated BI platform."
- "SaaS dashboard deployment."
- "Power BI-ready exports" (use "demo CSVs suitable for future Power BI import" instead)

**Employer-facing cover letters and draft downloads:** Follow the Sprint 61B claim-safety approach. Do not echo unproven tools (including Power BI) as if they are already evidenced in portfolio work.

**Other platforms:** Do not claim dbt, Airflow, Snowflake, BigQuery, or Power BI as current proven production skills unless separately evidenced.

---

## Sequencing

| Sprint | Scope |
|--------|--------|
| **Sprint 62** | Prep documentation (this file) |
| **Sprint 63** | Build `.pbix` offline from demo CSVs |
| **Sprint 64** | Screenshot evidence and optional README evidence line |
| **Sprint 65** | CV/LinkedIn wording only after artifact evidence exists |

Do not skip ahead. Public claims must follow evidence, not precede it.

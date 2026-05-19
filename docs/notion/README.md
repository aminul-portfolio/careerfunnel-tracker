# Career Evidence Notion Sync (Sprint 23F)

Optional metadata/status sync from the local repository to a Notion database. This keeps a reviewer-facing evidence tracker up to date without making Notion a runtime dependency of the Django app.

## What Sprint 23F sync does

- Reads local evidence paths under `docs/career_evidence/` and `docs/screenshots/career_evidence/`
- Checks filesystem existence and last-modified dates
- Reads git branch/tag context when git is available
- Upserts six tracker rows by **Name** in your Notion database:
  1. Project Evidence Report (V1)
  2. Job-Fit Matrix (V2)
  3. Recruiter Evidence Pack (V3)
  4. Career Evidence Dashboard UI (V4)
  5. Playwright Screenshots (V5)
  6. Notion Sync (V6)
- Updates metadata fields only: Category, Status, Sprint, Git Tag, Screenshot Ready, Last Updated, Local Path, Notes

## What it does NOT do

- Upload full Markdown reports, screenshots, or other binaries
- Modify Django models, settings, or dashboard runtime
- Run as a background worker, webhook, or CI job (unless you choose to wire it yourself later)
- Store or print your Notion API key
- Replace local evidence generation (`tools/` scripts, Playwright capture)

## Create a Notion connection

1. Open [Notion Integrations](https://www.notion.so/my-integrations) and create an **internal integration**.
2. Copy the **Internal Integration Secret** (this becomes `NOTION_API_KEY`).
3. Create or open your Career Evidence database in Notion.
4. Add the properties listed below if they are not already present (names must match exactly).
5. Share the database with your integration: database menu → **Connections** → select your integration.

## Required Notion database fields

| Property | Type |
|----------|------|
| Name | Title |
| Category | Select |
| Status | Select |
| Sprint | Text |
| Git Tag | Text |
| Screenshot Ready | Checkbox |
| Last Updated | Date |
| Local Path | Text |
| Notes | Text |

Suggested **Status** options: `Ready`, `In Progress`, `Missing`.

Suggested **Category** options: `Markdown Evidence`, `Dashboard`, `Screenshots`, `Sync`.

## Required environment variables

| Variable | Description |
|----------|-------------|
| `NOTION_API_KEY` | Notion internal integration secret |
| `NOTION_DATABASE_ID` | Database ID from the database URL |

Copy `docs/notion/notion_sync_example.env` as a reference only. **Do not commit real secrets.**

## Example PowerShell setup

```powershell
# From repository root (use your real values locally)
$env:NOTION_API_KEY = "your_notion_api_key_here"
$env:NOTION_DATABASE_ID = "your_notion_database_id_here"
```

Optional: load a local untracked file yourself (never commit it):

```powershell
Get-Content .env.notion.local | ForEach-Object {
  if ($_ -match '^\s*([^#][^=]+)=(.*)$') {
    [System.Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim(), 'Process')
  }
}
```

## Dry-run command

Preview planned create/update actions **without** API calls or credentials:

```powershell
python scripts/notion_sync_career_evidence.py --dry-run
```

## Live sync command

Requires both environment variables:

```powershell
python scripts/notion_sync_career_evidence.py
```

The script matches existing pages by **Name** and updates them; otherwise it creates a new page.

## Security guidance

- Never hardcode `NOTION_API_KEY` in source code or docs.
- Never commit `.env`, `.env.local`, or files containing real tokens.
- Do not paste integration secrets into issues, PRs, or screenshots.
- The script does not log authorization headers or API keys.
- Sync metadata only; keep private job-search data out of Notion.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|----------------|-----|
| Missing env var error | Variables not set in live mode | Export `NOTION_API_KEY` and `NOTION_DATABASE_ID` |
| HTTP 404 on database query | Wrong database ID or integration not connected | Re-copy ID; share database with integration |
| HTTP 400 property errors | Column names/types differ | Align Notion schema to table above |
| Status stays `Missing` | Evidence files not generated yet | Run V1–V3 tools and V5 screenshot script |
| `Screenshot Ready` false | PNGs missing | Run `scripts/capture_career_evidence_screenshots.py` |
| Git Tag shows `n/a` | Not a git checkout or no tags | Expected outside git; tag releases when ready |
| Partial failures | Network/API rate limits | Re-run; successful rows are not rolled back |

## Related local tooling

- V1–V3 markdown: `tools/career_evidence_audit.py`, `tools/career_job_fit_matrix.py`, `tools/career_recruiter_pack.py`
- V4 dashboard: `/dashboard/career-evidence/`
- V5 screenshots: `scripts/capture_career_evidence_screenshots.py`
- V6 sync: `scripts/notion_sync_career_evidence.py` (this document)

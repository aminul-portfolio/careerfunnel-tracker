# Career Evidence Dashboard Screenshots

Reviewer-ready PNG captures of the Career Evidence OS dashboard pages (Sprint 23E).

These images are generated locally with Playwright. They are evidence artifacts for portfolios, READMEs, LinkedIn posts, and recruiter packs — not production browser automation.

## Prerequisites

1. Local Django dev server running (for example `python manage.py runserver`).
2. Career Evidence markdown generated (V1–V3 tools under `tools/`).
3. A local dev user account you can log in with.

## Install Playwright

From the repository root with your virtual environment active:

```bash
pip install -r requirements.txt
playwright install chromium
```

`playwright install chromium` downloads the Chromium browser binary once per machine.

## Run screenshot capture

Set development-only credentials via environment variables (do not commit real passwords):

```powershell
# PowerShell
$env:CAREER_EVIDENCE_SCREENSHOT_USERNAME = "demo"
$env:CAREER_EVIDENCE_SCREENSHOT_PASSWORD = "your-local-dev-password"
python scripts/capture_career_evidence_screenshots.py
```

```bash
# Bash
export CAREER_EVIDENCE_SCREENSHOT_USERNAME=demo
export CAREER_EVIDENCE_SCREENSHOT_PASSWORD=your-local-dev-password
python scripts/capture_career_evidence_screenshots.py
```

Optional overrides:

| Variable | Default | Purpose |
|----------|---------|---------|
| `CAREER_EVIDENCE_SCREENSHOT_BASE_URL` | `http://127.0.0.1:8000/dashboard` | Dashboard mount for Career Evidence pages |
| `CAREER_EVIDENCE_SCREENSHOT_SITE_URL` | `http://127.0.0.1:8000` | Site root for `/accounts/login/` |
| `CAREER_EVIDENCE_SCREENSHOT_USERNAME` | *(required)* | Local dev username |
| `CAREER_EVIDENCE_SCREENSHOT_PASSWORD` | *(required)* | Local dev password |

After `python manage.py seed_demo_data`, you can use the printed demo username with your local password.

The script does **not** start Django. It assumes `runserver` is already listening.

## Expected screenshots

| File | Page |
|------|------|
| `career_evidence_overview.png` | `/dashboard/career-evidence/` |
| `project_evidence_report.png` | `/dashboard/career-evidence/project-evidence/` |
| `job_fit_matrix.png` | `/dashboard/career-evidence/job-fit-matrix/` |
| `recruiter_pack.png` | `/dashboard/career-evidence/recruiter-pack/` |

Viewport: **1440×1200**. Captures use full-page screenshots so long evidence content is not cropped.

## Reviewer-proof usage

1. Regenerate markdown evidence (`tools/career_evidence_audit.py`, `tools/career_job_fit_matrix.py`, `tools/career_recruiter_pack.py`) when the repo changes materially.
2. Start the dev server and confirm the four Career Evidence pages load in the browser while logged in.
3. Run the capture script and verify four PNG files appear in this folder.
4. Spot-check images: readable typography, no login screen, no browser devtools, no debug toolbar overlays.
5. Commit PNGs with the sprint or evidence refresh they represent.

If one page fails (missing markdown, server down), the script continues with the remaining pages and prints a summary at the end.

## GitHub and LinkedIn suggestions

- **GitHub README / docs:** Embed 1–2 representative images (overview + job-fit matrix) with alt text describing what reviewers should notice (evidence inventory, requirement mapping, recruiter pack structure).
- **LinkedIn project post:** Use the overview screenshot as the hero image; mention that evidence is generated from the repo (audit tools + dashboard viewer), not staged mockups.
- **Recruiter PDF / deck:** Pair `recruiter_pack.png` with links to `docs/career_evidence/03_recruiter_evidence_pack.md` for text-first reviewers.
- **Pull requests:** Attach before/after screenshots when Career Evidence UI or CSS changes.

Keep credentials out of commits, CI secrets, and public posts. Screenshots should reflect your local demo or dev data only.

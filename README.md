# Elise Job Finder

Academic math job tracker + application kit for Elise Catania (algebraic combinatorics).

- **pipeline/** — Python scraper: job boards → normalize → enrich (airport distance, liberal-arts classification) → `site/public/data/jobs.json`
- **site/** — Vite + React SPA, deployed to GitHub Pages, password-protected (AES-GCM encrypted personal content)
- **generate/** — Claude API script that pre-drafts per-job application materials (run locally only)
- **materials/** — Elise's CV and statements. **Gitignored — never commit.**

The site never writes to any job board's servers; it only links out to real application pages.

## Live site

**https://bcat13.github.io/elise-job-finder/** — password-protected. Data refreshes daily at ~6am Central via GitHub Actions.

## Operating it

**Change the password** (current temp password is `elise-changeme`):
```sh
cd site && PASSWORD='new-password' npm run encrypt
git commit -am "rotate password" && git push
```
Note: changing the password re-encrypts the application kits, so run this *after* any draft generation, with the same password Elise will use.

**Generate application kits** (needs `ANTHROPIC_API_KEY` set):
```sh
cd generate && npm install && node generate.mjs --limit 10   # or no limit for all matches
cd ../site && PASSWORD='the-password' npm run encrypt
git add public/data && git commit -m "update kits" && git push
```

**Run the scraper manually**: `python3 pipeline/run.py` locally, or trigger the
"Daily scrape and deploy" workflow from the GitHub Actions tab.

**Sources**: MathJobs.org (official JSON feed), AcademicJobsOnline, Canadian
Mathematical Society, Chronicle of Higher Education (math RSS), University
Affairs. AMS EIMS shut down in 2019.

## TODO
- Feed in Elise's research + teaching statements (`materials/`) and tighten the tone-matching in `generate/prompts/system.md`.
- Email alerts when new jobs match her filter (extend the Actions workflow).

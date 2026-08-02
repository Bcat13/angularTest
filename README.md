# Elise Job Finder

Academic math job tracker + application kit for Elise Catania (algebraic combinatorics).

- **pipeline/** — Python scraper: job boards → normalize → enrich (airport distance, liberal-arts classification) → `site/public/data/jobs.json`
- **site/** — Vite + React SPA, deployed to GitHub Pages, password-protected (AES-GCM encrypted personal content)
- **generate/** — Claude API script that pre-drafts per-job application materials (run locally only)
- **materials/** — Elise's CV and statements. **Gitignored — never commit.**

The site never writes to any job board's servers; it only links out to real application pages.

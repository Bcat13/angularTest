# chessPuzzles

Personal project.

- **pipeline/** — Python data pipeline → `site/public/data/jobs.json`
- **site/** — Vite + React SPA, deployed to GitHub Pages, password-protected (AES-GCM encrypted personal content)
- **generate/** — drafting script (run locally only)
- **materials/** — personal documents. **Gitignored — never commit.**

The site never writes to any external service's servers; it only links out.

## Live site

**https://bcat13.github.io/chessPuzzles/** — password-protected. Data refreshes daily at ~6am Central via GitHub Actions.

## Operating it

**Change the password**:
```sh
cd site && PASSWORD='new-password' npm run encrypt
git commit -am "rotate" && git push
```
Note: changing the password re-encrypts the drafts bundle, so run this *after* any draft generation, with the same password the user will use.

**Generate drafts** (needs `ANTHROPIC_API_KEY` set):
```sh
cd generate && npm install && node generate.mjs --limit 10   # or no limit for all matches
cd ../site && PASSWORD='the-password' npm run encrypt
git add public/data && git commit -m "update kits" && git push
```

**Run the pipeline manually**: `python3 pipeline/run.py` locally, or trigger the
"Daily scrape and deploy" workflow from the GitHub Actions tab.

## TODO
- Feed additional statements into `materials/` and tighten tone-matching in `generate/prompts/system.md`.
- Email alerts for new matches (extend the Actions workflow).
- Optional cross-device sync backend for tracker data.

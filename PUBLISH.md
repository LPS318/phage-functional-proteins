# Publish checklist (GitHub + Zenodo + Web)

## 0) What is already public
- v1.0 repo: `https://github.com/LPS318/phage-functional-proteins`
- v1.0 Zenodo DOI: `10.5281/zenodo.21971299`

This `v2.0` package is ready to publish as a **new version** on both.

---

## 1) Push to GitHub (new version on the same repo)

```bash
cd phage-functional-proteins          # this folder (already git-initialised)
git remote add origin https://github.com/LPS318/phage-functional-proteins.git
git branch -M main
git push -u origin main               # add --force only if you intend to overwrite
```

If the remote already has v1.0 history and you want a clean v2.0 commit on top:

```bash
git pull --rebase origin main   # then resolve, or push to a new branch/tag
git tag -a v2.0.0 -m "Candidate Database v2.0"
git push origin main --tags
```

## 2) Create the Zenodo record (new version)

1. Ensure the GitHub repo is **linked to Zenodo** (Zenodo → Settings →
   GitHub → flip the repo ON) so a GitHub **Release** auto-deposits.
2. On GitHub: **Releases → Draft a new release → tag `v2.0.0`** → paste the
   release notes → **Publish**.
3. Zenodo will deposit automatically; open the new record → **Edit** → check
   the metadata (title/description/creators/keywords/license) → **Publish** →
   it mints a new DOI (e.g. `10.5281/zenodo.XXXXXXX`).
   - The `.zenodo.json` in this repo pre-fills the metadata.
   - Set `related_identifiers.isNewVersionOf = 10.5281/zenodo.21971299`
     (already in `.zenodo.json`).

Manual alternative (no GitHub link): log in to Zenodo → **New upload** →
upload `PhageFP_candidatesDB_v2.0.zip` (see step 4) → fill metadata → Publish.

4) After publishing, **write the real DOI** into:
   - `CITATION.cff` → `doi:`
   - `README.md` → add a DOI badge at the top
   - manuscript → the data-availability statement

## 3) Deploy the web app

```bash
cd web
docker build -t phage-cand-db .
docker run -d -p 8000:8000 -v "$PWD/../data":/data:ro --name phage-cand-db phage-cand-db
# put nginx/Caddy in front for TLS; or deploy to Render/Fly/Railway/Aliyun ECS
```

Health check: `GET /api/stats` should return `{"total": 4117, ...}`.

## 4) Optional: a single downloadable archive for Zenodo

```bash
zip -r PhageFP_candidatesDB_v2.0.zip . \
  -x '.git/*' 'figs/*' '*.pyc'    # exclude git + (optionally) large figure set
```

## 5) Post-publish consistency

- [ ] Real DOI written to `CITATION.cff` and `README.md`
- [ ] Manuscript data-availability statement points to the DOI
- [ ] Web app reachable and returns 4,117 records
- [ ] GitHub release tag `v2.0.0` created
- [ ] (optional) Zenodo `concept DOI` recorded for future versions

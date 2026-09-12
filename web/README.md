# Web app — candidate-database search

FastAPI + SQLite, read-only over `../data/candidates_v2.0.sqlite`.

## Endpoints
- `GET /` — search UI (`index.html`)
- `GET /api/stats` — totals by category, top hosts
- `GET /api/search?q=&category=&sort=&order=&limit=&offset=` — filter + sort + paging
- `GET /api/candidate/{protein_id}` — one record
- `GET /api/export.csv?q=&category=` — CSV download

## Run locally
```bash
pip install -r requirements.txt
CAND_DB=../data/candidates_v2.0.sqlite uvicorn app:app --host 0.0.0.0 --port 8000
# open http://localhost:8000
```

## Deploy (Docker)
```bash
docker build -t phage-cand-db .
docker run -p 8000:8000 -v "$PWD/../data":/data:ro phage-cand-db
```
Then put it behind any reverse proxy (nginx/Caddy) or a PaaS (Render/Fly/Railway/
Aliyun ECS+nginx). The app is stateless; mount the SQLite read-only.

## Suggested hardening
- rate limiting / optional API key for `/api/export.csv`
- periodic refresh of the SQLite from a new candidate release
- add per-entry links to structure figures and (later) wet-lab results

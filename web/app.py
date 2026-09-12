#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phage Functional Protein Candidate Database v2.0 — search web app.
FastAPI + SQLite (read-only). Run:
    CAND_DB=../data/candidates_v2.0.sqlite uvicorn app:app --host 0.0.0.0 --port 8000
API:
    GET /                     -> search UI (index.html)
    GET /api/stats            -> totals by category / top hosts
    GET /api/search?q=&category=&sort=&order=&limit=&offset=
    GET /api/candidate/{pid}  -> one record
    GET /api/export.csv?category=&q=   -> CSV download
"""
import os, sqlite3, csv, io
from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse

DB = os.environ.get("CAND_DB", os.path.join(os.path.dirname(__file__), "..", "data", "candidates_v2.0.sqlite"))
app = FastAPI(title="Phage Functional Protein Candidate DB v2.0", version="2.0")

def cols():
    c = sqlite3.connect(f"file:{DB}?mode=ro", uri=True); cur = c.cursor()
    names = [r[1] for r in cur.execute("PRAGMA table_info(candidates)")]
    c.close()
    return names

def run_sql(sql, args=()):
    c = sqlite3.connect(f"file:{DB}?mode=ro", uri=True); cur = c.cursor()
    cur.execute(sql, args); names = [d[0] for d in cur.description]
    rows = [dict(zip(names, r)) for r in cur.fetchall()]; c.close()
    return rows

@app.get("/", response_class=HTMLResponse)
def index():
    p = os.path.join(os.path.dirname(__file__), "index.html")
    return HTMLResponse(open(p, encoding="utf-8").read())

@app.get("/api/stats")
def stats():
    c = sqlite3.connect(f"file:{DB}?mode=ro", uri=True); cur = c.cursor()
    n = cur.execute("SELECT COUNT(*) FROM candidates").fetchone()[0]
    by_cat = dict(cur.execute("SELECT category, COUNT(*) FROM candidates GROUP BY category").fetchall())
    top_hosts = dict(cur.execute(
        "SELECT host_raw, COUNT(*) FROM candidates WHERE host_raw IS NOT NULL AND host_raw!='' "
        "GROUP BY host_raw ORDER BY COUNT(*) DESC LIMIT 10").fetchall())
    scored = cur.execute("SELECT COUNT(*) FROM candidates WHERE total_score IS NOT NULL AND total_score!=''").fetchone()[0]
    c.close()
    return {"total": n, "by_category": by_cat, "top_hosts": top_hosts, "with_total_score": scored}

ALLOWED_SORT = None  # filled lazily from schema

@app.get("/api/search")
def search(q: str = Query(""), category: str = Query(""),
           sort: str = Query("total_score"), order: str = Query("desc"),
           limit: int = Query(50, le=1000), offset: int = Query(0)):
    global ALLOWED_SORT
    if ALLOWED_SORT is None: ALLOWED_SORT = set(cols())
    if sort not in ALLOWED_SORT: sort = "total_score"
    order = "ASC" if str(order).lower() == "asc" else "DESC"
    where = "WHERE 1=1"; args = []
    if q:
        where += " AND (protein_id LIKE ? OR host_raw LIKE ? OR genome_genus LIKE ? OR genome_family LIKE ?)"
        args += [f"%{q}%"] * 4
    if category:
        where += " AND category = ?"; args.append(category)
    total = run_sql(f"SELECT COUNT(*) AS n FROM candidates {where}", args)[0]["n"]
    rows = run_sql(f"SELECT * FROM candidates {where} ORDER BY CAST({sort} AS REAL) {order} LIMIT ? OFFSET ?",
                   args + [limit, offset])
    return {"count": len(rows), "total": total, "rows": rows}

@app.get("/api/candidate/{pid}")
def candidate(pid: str):
    rows = run_sql("SELECT * FROM candidates WHERE protein_id = ?", [pid])
    return JSONResponse(rows[0] if rows else {"error": "not found"}, status_code=200 if rows else 404)

@app.get("/api/export.csv")
def export(category: str = Query(""), q_: str = Query("", alias="q")):
    where = "WHERE 1=1"; args = []
    if category: where += " AND category=?"; args.append(category)
    if q_: where += " AND (protein_id LIKE ? OR host_raw LIKE ?)"; args += [f"%{q_}%"] * 2
    names = cols()
    rows = run_sql(f"SELECT * FROM candidates {where}", args)
    buf = io.StringIO(); w = csv.DictWriter(buf, fieldnames=names); w.writeheader(); w.writerows(rows)
    buf.seek(0)
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=candidates_v2.0.csv"})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))

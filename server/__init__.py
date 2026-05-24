"""
HTTP API in front of the agents library. FastAPI + SSE.

Run:
  uvicorn server.app:app --reload --port 8000

Endpoints:
  GET  /api/health
  GET  /api/packs               list packs
  GET  /api/packs/{name}        pack detail (bound skills + tools)
  GET  /api/skills              list skill frontmatter
  GET  /api/skills/{name}       skill detail (body + manifest)
  GET  /api/tools               list registered tools
  GET  /api/tools/{name}        tool detail (card + schema)
  GET  /api/runs                list known runs (audit_logs/*.jsonl)
  GET  /api/runs/{run_id}       full audit for one run
  POST /api/runs                start a run; returns {run_id}
  GET  /api/runs/{run_id}/stream live SSE event stream
  GET  /api/evals/cases         list eval cases
  POST /api/evals/run           run a subset; returns {job_id}
  GET  /api/evals/jobs/{job_id} job status + per-case results (SSE)
  GET  /api/evals/results       list past result files
"""

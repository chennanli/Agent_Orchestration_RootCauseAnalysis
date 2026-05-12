"""TEP Live Copilot backend package.

Marking `backend/` as a real Python package so `uvicorn backend.app:app`
works under Docker / production deployments. The one-click launcher
(`python backend/app.py`) still works because we adjust sys.path at the
top of `app.py` before any sibling imports run.
"""

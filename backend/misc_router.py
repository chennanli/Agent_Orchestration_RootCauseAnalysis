"""Misc endpoints: per-run export, share-by-email, KB upload (live shape).

These power the new "Misc" tab in the Live Copilot UI. They re-use what
already exists in `backend.app` and `backend.email_sender` but route it
under `/api/misc/*` so the new shell does not depend on the legacy
`/rag/*` namespace.

Endpoints
---------
GET  /api/misc/runs/{run_id}/markdown
    Render a run's trace + final advisory as a Markdown report. Plain
    `text/markdown` body so the browser triggers a download instead of
    rendering inline.

POST /api/misc/runs/{run_id}/email
    Body: {recipient, subject?}. Generates the same Markdown report and
    sends it as an attachment via the SMTP credentials in env. Returns
    {sent: bool, reason?}. Refuses to spam if SMTP_* env vars are unset.

POST /api/misc/kb/upload
    multipart/form-data: files=<PDF>[, files=<PDF>...]. Saves the PDFs
    into knowledge_base/ and re-indexes the live keyword KB. Returns the
    new KB stats.

GET  /api/misc/notes
POST /api/misc/notes
    Operator scratchpad. Stored on disk under backend/diagnostics/notes.json.
    Survives restarts. Plain string body, no schema gymnastics.
"""
from __future__ import annotations

import json
import logging
import os
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel

from backend.nat_runner import RUNS_DIR

logger = logging.getLogger("misc_router")
router = APIRouter(prefix="/api/misc")

_SAFE_ID_RE = re.compile(r"^[A-Za-z0-9_\-]+$")
_NOTES_FILE = Path(__file__).parent / "diagnostics" / "notes.json"
_KB_DIR = Path(__file__).parent.parent / "knowledge_base"


def _safe_run_id(run_id: str) -> str:
    if not _SAFE_ID_RE.fullmatch(run_id):
        raise HTTPException(status_code=400, detail=f"invalid run_id: {run_id!r}")
    return run_id


def _load_run(run_id: str) -> Dict[str, Any]:
    f = RUNS_DIR / f"{_safe_run_id(run_id)}.json"
    if not f.exists():
        raise HTTPException(status_code=404, detail=f"run not found: {run_id}")
    return json.loads(f.read_text(encoding="utf-8"))


def _render_run_markdown(run: Dict[str, Any]) -> str:
    """Plain-text Markdown report. Stays advisory-only; this is what gets
    emailed to operators or pasted into a Slack thread.
    """
    final = run.get("final_answer") or {}
    pc = final.get("policy_check") or {}
    text = final.get("text") or "(no advisory)"

    lines: List[str] = []
    lines.append(f"# TEP Live Copilot — diagnosis report")
    lines.append("")
    lines.append(f"- **Run id**: `{run.get('run_id', '?')}`")
    lines.append(f"- **Fault id**: `{run.get('fault_id', '?')}`")
    lines.append(f"- **Model**: `{run.get('model_id', '?')}`")
    lines.append(f"- **Started**: {run.get('started_at', '?')}")
    lines.append(f"- **Runtime (s)**: {run.get('runtime_seconds', '?')}")
    lines.append(f"- **Policy safe**: {pc.get('is_advisory_safe', '?')}")
    lines.append("")
    lines.append("## Final advisory")
    lines.append("")
    lines.append(text.strip())
    lines.append("")
    if final.get("safety_notice"):
        lines.append(f"> {final['safety_notice']}")
        lines.append("")

    lines.append("## Tool trace")
    lines.append("")
    for i, step in enumerate(run.get("tool_trace") or [], start=1):
        p = step.get("payload") or {}
        et = p.get("event_type", "?")
        name = p.get("name", "?")
        if et == "FUNCTION_END":
            data = p.get("data") or {}
            out = data.get("output")
            preview = json.dumps(out, default=str)
            if len(preview) > 400:
                preview = preview[:397] + "..."
            lines.append(f"{i}. **{name}** → `{preview}`")
        elif et == "FUNCTION_START":
            lines.append(f"{i}. _call_ `{name}`")
        else:
            lines.append(f"{i}. `{et}` {name}")
    lines.append("")

    followups = run.get("followups") or []
    if followups:
        lines.append("## Follow-up chat")
        lines.append("")
        for fu in followups:
            lines.append(f"**Q:** {fu.get('q', '')}")
            lines.append("")
            lines.append(fu.get("a", ""))
            lines.append("")
            if fu.get("model_id"):
                lines.append(f"_(answered by {fu['model_id']})_")
                lines.append("")

    lines.append("---")
    lines.append("")
    lines.append(
        "Advisory only — no automatic process actions. Review by a qualified "
        "operator is required before any setpoint change."
    )
    return "\n".join(lines)


@router.get("/runs/{run_id}/markdown")
def export_run_markdown(run_id: str) -> Response:
    run = _load_run(run_id)
    body = _render_run_markdown(run)
    # text/markdown so curl saves it nicely; Content-Disposition triggers
    # the browser's download dialog.
    return Response(
        content=body,
        media_type="text/markdown; charset=utf-8",
        headers={
            "Content-Disposition": (
                f'attachment; filename="{run.get("run_id", run_id)}.md"'
            )
        },
    )


class EmailRequest(BaseModel):
    recipient: str
    subject: Optional[str] = None


@router.post("/runs/{run_id}/email")
def email_run(run_id: str, req: EmailRequest) -> Dict[str, Any]:
    """Send the Markdown report as an attachment. Returns sent=False (not
    HTTP 500) when SMTP isn't configured — the UI shows a clear hint.
    """
    if not req.recipient or "@" not in req.recipient:
        raise HTTPException(status_code=400, detail="invalid recipient address")

    run = _load_run(run_id)
    body_md = _render_run_markdown(run)

    # Write the Markdown to a temp file the email sender can attach. Use a
    # path scoped to backend/diagnostics so we can find/clean it later.
    out_dir = Path(__file__).parent / "diagnostics" / "exports"
    out_dir.mkdir(parents=True, exist_ok=True)
    md_path = out_dir / f"{run.get('run_id', run_id)}.md"
    md_path.write_text(body_md, encoding="utf-8")

    subject = req.subject or f"TEP RCA report — {run.get('fault_id', run_id)}"
    final = run.get("final_answer") or {}
    conclusion = (final.get("text") or "(no advisory)")[:600]

    # Import lazily so the router still loads if SMTP libs aren't installed
    # (they are stdlib, but keep the import local for clarity).
    from backend.email_sender import (
        generate_report_email_body,
        send_report_email,
    )

    html_body = generate_report_email_body(
        snapshot_id=run.get("run_id", run_id),
        snapshot_name=run.get("fault_id", run_id),
        conclusion=conclusion,
        report_filename=md_path.name,
    )
    ok = send_report_email(
        recipient=req.recipient,
        subject=subject,
        body_html=html_body,
        attachments=[str(md_path)],
    )
    if not ok:
        # Not a server fault — most likely SMTP_* unset. Surface as 200 so
        # the UI can render a hint instead of a red error banner.
        return {
            "sent": False,
            "reason": (
                "SMTP not configured. Set SMTP_SERVER, SMTP_PORT, "
                "SMTP_USERNAME, SMTP_PASSWORD, SMTP_FROM on the server."
            ),
        }
    return {"sent": True, "report_path": str(md_path)}


# ---------------------------------------------------------------------------
# Operator notes
# ---------------------------------------------------------------------------

class NotesPayload(BaseModel):
    text: str


def _read_notes() -> Dict[str, Any]:
    if not _NOTES_FILE.exists():
        return {"text": "", "updated_at": None}
    try:
        return json.loads(_NOTES_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"text": "", "updated_at": None}


@router.get("/notes")
def get_notes() -> Dict[str, Any]:
    return _read_notes()


@router.post("/notes")
def set_notes(body: NotesPayload) -> Dict[str, Any]:
    _NOTES_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "text": body.text,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    _NOTES_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


# ---------------------------------------------------------------------------
# Knowledge-base upload (live shape — knowledge_base/, not RAG/)
# ---------------------------------------------------------------------------

@router.post("/kb/upload")
async def kb_upload(files: List[UploadFile] = File(...)) -> Dict[str, Any]:
    """Drop PDFs into knowledge_base/ and re-index the keyword KB.

    Unlike the legacy /rag/upload_build, this does NOT run the
    PDF→Markdown converter (which is heavy and brittle). The new
    Live Copilot's knowledge_manager already auto-detects markdown files,
    so the recommended workflow is: convert offline, drop .md into
    knowledge_base/, click upload. The endpoint still accepts PDFs and
    saves them alongside; they will not be searchable until converted.
    """
    if not files:
        raise HTTPException(status_code=400, detail="no files received")

    _KB_DIR.mkdir(parents=True, exist_ok=True)
    saved: List[str] = []
    for f in files:
        if not f.filename:
            continue
        # Defence against path traversal in the user-supplied filename.
        safe_name = Path(f.filename).name.replace("..", "_")
        dest = _KB_DIR / safe_name
        content = await f.read()
        dest.write_bytes(content)
        saved.append(str(dest))

    # Force the live knowledge manager to re-scan. The agent_tools layer
    # caches a singleton; we reset it so the next search picks up new docs.
    try:
        import backend.agent_tools.knowledge_tools as _kt
        _kt._KM = None  # reset the cached singleton  # noqa: SLF001
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"could not reset KM cache: {exc}")

    return {
        "saved": saved,
        "kb_dir": str(_KB_DIR.resolve()),
        "hint": (
            "PDFs are stored but not searchable until converted to Markdown. "
            "Drop pre-converted .md files into the same folder for the "
            "agent to read them on the next search."
        ),
    }

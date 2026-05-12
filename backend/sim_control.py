"""HTTP proxy from the FastAPI backend to the legacy unified_console.py
Flask app (port 9002), which owns the Fortran simulator process.

This module ONLY exposes a few small control routes (speed, IDV trigger,
status) so the new React UI can drive the simulator without talking to the
Flask app directly. Live sensor data still flows through /ingest -> /stream,
not through here.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger("sim_control")
router = APIRouter()

# Where the Flask "unified_console" Fortran simulator lives.
#   - Plain `python backend/app.py` on the laptop: localhost:9002
#   - docker-compose: http://console:9002 (set via UNIFIED_CONSOLE_URL env)
UNIFIED_CONSOLE_URL = os.environ.get(
    "UNIFIED_CONSOLE_URL", "http://127.0.0.1:9002"
)
_HTTP_TIMEOUT = httpx.Timeout(5.0, connect=2.0)


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(base_url=UNIFIED_CONSOLE_URL, timeout=_HTTP_TIMEOUT)


def _safe_json(r: httpx.Response) -> Optional[Any]:
    try:
        return r.json()
    except ValueError:
        return r.text[:240]


@router.get("/api/sim/status")
async def sim_status() -> Dict[str, Any]:
    """Best-effort liveness probe + speed/IDV state from unified_console."""
    last_err: Optional[Exception] = None
    any_path_connected = False
    async with _client() as c:
        for path in ("/api/status", "/status", "/api/state", "/"):
            try:
                r = await c.get(path)
            except httpx.RequestError as exc:
                last_err = exc
                continue
            any_path_connected = True
            if r.status_code < 400 and "html" not in r.headers.get(
                "content-type", ""
            ):
                return {
                    "sim_alive": True,
                    "source": path,
                    "payload": _safe_json(r),
                }
    if any_path_connected:
        # The server is up but doesn't expose a JSON status route. We still
        # treat that as alive; the speed/fault routes will probe their own
        # paths separately.
        return {
            "sim_alive": True,
            "source": None,
            "payload": "no JSON status endpoint exposed yet",
        }
    return {"sim_alive": False, "reason": str(last_err) if last_err else "unreachable"}


class SpeedRequest(BaseModel):
    speed: float  # 0.1 .. 50


@router.get("/api/sim/speed")
async def get_speed() -> Dict[str, Any]:
    """Best-effort read of the current speed_factor from unified_console."""
    try:
        async with _client() as c:
            for path in ("/api/speed", "/api/get_speed", "/get_speed"):
                try:
                    r = await c.get(path)
                except httpx.RequestError:
                    continue
                if r.status_code < 400:
                    return {"ok": True, "speed": _safe_json(r)}
            raise HTTPException(
                status_code=501,
                detail="unified_console.py has no speed-getter endpoint yet",
            )
    except httpx.ConnectError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"unified_console not reachable: {exc}",
        )


@router.post("/api/sim/speed")
async def set_speed(req: SpeedRequest) -> Dict[str, Any]:
    if not (0.1 <= req.speed <= 50):
        raise HTTPException(status_code=422, detail="speed must be in [0.1, 50]")
    try:
        async with _client() as c:
            for path in ("/api/speed", "/api/set_speed", "/set_speed"):
                try:
                    r = await c.post(
                        path,
                        json={"speed": req.speed, "speed_factor": req.speed},
                    )
                    if r.status_code < 400:
                        return {"ok": True, "echo": _safe_json(r)}
                except httpx.RequestError:
                    continue
            raise HTTPException(
                status_code=501,
                detail="unified_console.py has no speed-setter endpoint yet",
            )
    except httpx.ConnectError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"unified_console not reachable: {exc}",
        )


class FaultRequest(BaseModel):
    idv: int  # 0..20 (0 = clear)
    magnitude: float = 1.0


@router.post("/api/sim/fault")
async def trigger_fault(req: FaultRequest) -> Dict[str, Any]:
    if not (0 <= req.idv <= 20):
        raise HTTPException(status_code=422, detail="idv must be in [0,20]")
    # The unified_console endpoint expects {idv_num, value} where value is
    # 0 or 1 (each TEP IDV is a 0/1 disturbance flag). We map magnitude>0
    # to value=1, magnitude<=0 to value=0.
    value = 1 if req.magnitude > 0 else 0
    body = {"idv_num": req.idv, "value": value}
    try:
        async with _client() as c:
            for path in ("/api/idv/set", "/api/idv", "/api/set_idv", "/set_idv"):
                try:
                    r = await c.post(path, json=body)
                except httpx.RequestError:
                    continue
                if r.status_code < 400:
                    return {"ok": True, "echo": _safe_json(r)}
            raise HTTPException(
                status_code=501,
                detail="unified_console.py has no IDV-setter endpoint yet",
            )
    except httpx.ConnectError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"unified_console not reachable: {exc}",
        )

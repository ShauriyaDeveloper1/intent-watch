from __future__ import annotations

from fastapi import APIRouter
import hashlib
import os
import platform
from pathlib import Path
import sys
import time

from api.routes import video
from api.routes.alerts import alerts, alerts_lock

router = APIRouter()

_started_at = time.time()


def _format_uptime(seconds: int) -> str:
    seconds = max(0, int(seconds))
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, _ = divmod(rem, 60)
    if days > 0:
        return f"{days}d {hours}h"
    if hours > 0:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


@router.get("/metrics")
def get_metrics():
    now = time.time()
    uptime_seconds = int(now - _started_at)

    stream_ids = video.manager.list_streams()
    statuses = [video.manager.get_status(sid) for sid in stream_ids]

    running = [s for s in statuses if s.get("running")]
    cameras_online = sum(1 for s in running if s.get("mode") == "camera")
    streams_running = len(running)

    people_detected = 0
    for sid in stream_ids:
        st = video.manager.get_status(sid)
        if st.get("running"):
            people_detected += video.manager.get_people_count(sid)

    with alerts_lock:
        active_alerts = len(alerts)

    return {
        "uptime_seconds": uptime_seconds,
        "uptime": _format_uptime(uptime_seconds),
        "streams_running": streams_running,
        "cameras_online": cameras_online,
        "people_detected": people_detected,
        "active_alerts": active_alerts,
    }


def _sha256_file(path: Path) -> str | None:
    try:
        data = path.read_bytes()
    except Exception:
        return None
    return hashlib.sha256(data).hexdigest()


@router.get("/debug/runtime")
def get_runtime_debug():
    """Lightweight runtime introspection for local debugging.

    Helps confirm which Python executable/environment and which code version is
    running behind the API (useful when multiple processes fight over the port).
    """
    # Keep env reporting narrowly scoped to relevant tuning knobs.
    env_keys = [
        "INTENTWATCH_WEAPON_CONF",
        "INTENTWATCH_WEAPON_KNIFE_CONF",
        "INTENTWATCH_WEAPON_PERSIST_FRAMES",
        "INTENTWATCH_WEAPON_MAX_AREA_RATIO",
        "INTENTWATCH_WEAPON_IMGSZ",
        "INTENTWATCH_WEAPON_INFER_EVERY_N_FRAMES",
        "INTENTWATCH_WEAPON_REARM_SECONDS",
        "INTENTWATCH_WEAPON_CLEAR_SECONDS",
        "INTENTWATCH_WEAPON_ENABLE_FALLBACK",
        "INTENTWATCH_WEAPON_FALLBACK_CONF",
        "INTENTWATCH_WEAPON_FALLBACK_PERSIST_FRAMES",
        "INTENTWATCH_WEAPON_VERIFY_ENABLED",
        "INTENTWATCH_WEAPON_VERIFY_MODEL_PATH",
        "INTENTWATCH_WEAPON_VERIFY_CONF",
        "INTENTWATCH_WEAPON_VERIFY_IMGSZ",
        "INTENTWATCH_INFER_HALF",
        "INTENTWATCH_MAX_FRAME_HEIGHT",
        "INTENTWATCH_JPEG_QUALITY",
    ]
    env = {k: os.getenv(k) for k in env_keys if os.getenv(k) is not None}

    # Best-effort code fingerprints.
    this_file = Path(__file__).resolve()
    stream_manager_file = (this_file.parents[1] / "stream_manager.py").resolve()
    video_routes_file = (this_file.parent / "video.py").resolve()

    # Model candidates (do not load models here).
    try:
        weapon_candidates = [str(p) for p in video._weapon_model_candidates()]
        weapon_existing = [str(p) for p in video._weapon_model_candidates() if p.exists()]
    except Exception:
        weapon_candidates = []
        weapon_existing = []

    try:
        verify_candidates = [str(p) for p in video._weapon_verify_model_candidates()]
        verify_existing = [str(p) for p in video._weapon_verify_model_candidates() if p.exists()]
    except Exception:
        verify_candidates = []
        verify_existing = []

    try:
        fallback_candidates = [str(p) for p in video._weapon_fallback_model_candidates()]
        fallback_existing = [str(p) for p in video._weapon_fallback_model_candidates() if p.exists()]
    except Exception:
        fallback_candidates = []
        fallback_existing = []

    try:
        effective = video.manager.get_effective_tuning()
    except Exception:
        effective = {}

    return {
        "pid": os.getpid(),
        "python": {
            "executable": sys.executable,
            "version": sys.version,
            "prefix": getattr(sys, "prefix", None),
            "base_prefix": getattr(sys, "base_prefix", None),
        },
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
        },
        "cwd": os.getcwd(),
        "env": env,
        "effective": effective,
        "code": {
            "metrics_py": str(this_file),
            "metrics_sha256": _sha256_file(this_file),
            "stream_manager_py": str(stream_manager_file),
            "stream_manager_sha256": _sha256_file(stream_manager_file),
            "video_routes_py": str(video_routes_file),
            "video_routes_sha256": _sha256_file(video_routes_file),
        },
        "models": {
            "weapon_candidates": weapon_candidates,
            "weapon_existing": weapon_existing,
            "verify_candidates": verify_candidates,
            "verify_existing": verify_existing,
            "fallback_candidates": fallback_candidates,
            "fallback_existing": fallback_existing,
        },
    }

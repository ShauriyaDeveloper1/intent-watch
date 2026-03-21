from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse
from pathlib import Path
import os
import re
import json
import time
import threading
import tempfile

router = APIRouter()

BACKEND_DIR = Path(__file__).resolve().parents[2]  # .../backend
HISTORY_DIR = BACKEND_DIR / "data" / "history"
HISTORY_DIR.mkdir(parents=True, exist_ok=True)

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _env_bool(name: str, default: bool = False) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return str(v).strip().lower() in {"1", "true", "yes", "y", "on"}


def _safe_stream_id(stream_id: str) -> str:
    s = str(stream_id or "").strip()
    if not s or "/" in s or "\\" in s or ".." in s:
        raise HTTPException(status_code=400, detail="Invalid stream_id")
    return s


def _safe_date(date: str) -> str:
    d = str(date or "").strip()
    if not _DATE_RE.match(d):
        raise HTTPException(status_code=400, detail="Invalid date (expected YYYY-MM-DD)")
    return d


def _safe_filename(name: str) -> str:
    n = os.path.basename(str(name or "").strip())
    if not n or n in {".", ".."}:
        raise HTTPException(status_code=400, detail="Invalid filename")
    if any(sep in n for sep in ["/", "\\"]):
        raise HTTPException(status_code=400, detail="Invalid filename")
    return n


def _safe_clip_path(stream_id: str, date: str, filename: str) -> Path:
    sid = _safe_stream_id(stream_id)
    d = _safe_date(date)
    fn = _safe_filename(filename)

    p = (HISTORY_DIR / sid / d / fn).resolve()
    if HISTORY_DIR.resolve() not in p.parents:
        raise HTTPException(status_code=400, detail="Invalid path")
    return p


def cleanup_old_history_files(*, retention_days: int) -> dict:
    try:
        days = int(retention_days)
    except Exception:
        days = 180
    if days <= 0:
        return {"retention_days": days, "deleted": 0, "errors": 0}

    cutoff = time.time() - (float(days) * 86400.0)

    deleted = 0
    errors = 0

    if not HISTORY_DIR.exists():
        return {"retention_days": days, "deleted": 0, "errors": 0}

    media_files: list[Path] = []
    media_files.extend(list(HISTORY_DIR.rglob("*.mp4")))
    media_files.extend(list(HISTORY_DIR.rglob("*.webm")))
    for p in media_files:
        try:
            rp = p.resolve()
            if HISTORY_DIR.resolve() not in rp.parents:
                continue
            if not rp.is_file():
                continue
            try:
                mtime = float(rp.stat().st_mtime)
            except Exception:
                continue
            if mtime >= cutoff:
                continue

            meta = rp.with_suffix(rp.suffix + ".json")
            try:
                rp.unlink(missing_ok=True)
                deleted += 1
            except Exception:
                errors += 1

            try:
                meta.unlink(missing_ok=True)
            except Exception:
                pass
        except Exception:
            errors += 1

    # Clean up orphaned sidecars
    json_files: list[Path] = []
    json_files.extend(list(HISTORY_DIR.rglob("*.mp4.json")))
    json_files.extend(list(HISTORY_DIR.rglob("*.webm.json")))
    for jp in json_files:
        try:
            rp = jp.resolve()
            if HISTORY_DIR.resolve() not in rp.parents:
                continue
            base = Path(str(rp)[: -len(".json")])
            if base.exists():
                continue
            rp.unlink(missing_ok=True)
        except Exception:
            pass

    # Remove empty day/stream folders
    try:
        for day_dir in sorted([p for p in HISTORY_DIR.rglob("*") if p.is_dir()], reverse=True):
            try:
                if any(day_dir.iterdir()):
                    continue
                day_dir.rmdir()
            except Exception:
                continue
    except Exception:
        pass

    return {"retention_days": days, "deleted": deleted, "errors": errors}


def start_history_retention_worker() -> None:
    enabled = _env_bool("INTENTWATCH_HISTORY_RETENTION_ENABLED", True)
    if not enabled:
        return

    try:
        retention_days = int(os.getenv("INTENTWATCH_HISTORY_RETENTION_DAYS") or "180")
    except Exception:
        retention_days = 180

    try:
        interval_hours = int(os.getenv("INTENTWATCH_HISTORY_CLEANUP_INTERVAL_HOURS") or "24")
    except Exception:
        interval_hours = 24

    if interval_hours <= 0:
        interval_hours = 24

    def _loop() -> None:
        while True:
            try:
                res = cleanup_old_history_files(retention_days=retention_days)
                if int(res.get("deleted") or 0) > 0:
                    print(
                        f"✓ History retention cleanup deleted {res['deleted']} clip(s) "
                        f"(retention_days={res['retention_days']}, errors={res['errors']})"
                    )
            except Exception as e:
                try:
                    print(f"✗ History retention cleanup failed: {e}")
                except Exception:
                    pass
            time.sleep(float(interval_hours) * 3600.0)

    # Run once immediately, then on the interval.
    try:
        cleanup_old_history_files(retention_days=retention_days)
    except Exception:
        pass

    threading.Thread(target=_loop, name="history-retention", daemon=True).start()


@router.get("/dates")
def list_dates(stream_id: str = "primary"):
    sid = _safe_stream_id(stream_id)
    base = HISTORY_DIR / sid
    if not base.exists():
        return {"stream_id": sid, "dates": []}

    dates: list[str] = []
    for p in base.iterdir():
        if p.is_dir() and _DATE_RE.match(p.name):
            dates.append(p.name)
    dates.sort(reverse=True)
    return {"stream_id": sid, "dates": dates}


@router.get("/streams")
def list_streams():
    """List stream_ids that have local history clips."""
    if not HISTORY_DIR.exists():
        return {"streams": []}

    streams: list[str] = []
    try:
        for p in HISTORY_DIR.iterdir():
            if not p.is_dir():
                continue
            # Reuse the same safety checks as inputs
            try:
                sid = _safe_stream_id(p.name)
            except HTTPException:
                continue
            streams.append(sid)
    except Exception:
        streams = []

    streams.sort()
    # Prefer primary first when present
    if "primary" in streams:
        streams = ["primary"] + [s for s in streams if s != "primary"]

    return {"streams": streams}


@router.get("/supabase/status")
def supabase_status():
    """Report whether Supabase is configured for this backend process.

    This endpoint never returns secrets; it only reports boolean presence.
    """
    bucket = (os.getenv("INTENTWATCH_HISTORY_BUCKET") or "footages").strip() or "footages"
    upload_enabled = _env_bool("INTENTWATCH_HISTORY_UPLOAD_SUPABASE", False)
    has_url = bool((os.getenv("SUPABASE_URL") or "").strip())
    has_key = bool(
        (os.getenv("SUPABASE_SERVICE_ROLE_KEY") or "").strip()
        or (os.getenv("SUPABASE_KEY") or "").strip()
        or (os.getenv("SUPABASE_ANON_KEY") or "").strip()
    )

    configured = False
    try:
        from api.supabase_client import is_configured

        configured = bool(is_configured())
    except Exception:
        configured = False

    return {
        "upload_enabled": upload_enabled,
        "bucket": bucket,
        "has_url": has_url,
        "has_key": has_key,
        "configured": configured,
    }


@router.get("/clips")
def list_clips(stream_id: str = "primary", date: str | None = None):
    sid = _safe_stream_id(stream_id)
    if not date:
        raise HTTPException(status_code=400, detail="Missing date")
    d = _safe_date(date)

    day_dir = HISTORY_DIR / sid / d
    if not day_dir.exists():
        return {"stream_id": sid, "date": d, "clips": []}

    clips = []
    media_paths: list[Path] = []
    media_paths.extend(list(day_dir.glob("*.mp4")))
    media_paths.extend(list(day_dir.glob("*.webm")))
    for p in sorted(media_paths, key=lambda x: x.stat().st_mtime, reverse=True):
        try:
            size_bytes = int(p.stat().st_size)
        except Exception:
            continue

        # Skip tiny/corrupt stub files (e.g., if a writer was created but never wrote frames).
        if size_bytes < 1024:
            continue

        meta_path = p.with_suffix(p.suffix + ".json")
        meta = None
        if meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
            except Exception:
                meta = None

        mime = "video/webm" if p.suffix.lower() == ".webm" else "video/mp4"

        alt_url = None
        alt_mime = None
        if p.suffix.lower() == ".mp4":
            # Allow frontend to fall back to WebM conversion if MP4 playback fails in browser.
            alt_url = f"/history/clip/{sid}/{d}/{p.name}?format=webm"
            alt_mime = "video/webm"

        clips.append(
            {
                "filename": p.name,
                "size_bytes": size_bytes,
                "mtime": int(p.stat().st_mtime),
                "public_url": (meta or {}).get("public_url"),
                "url": f"/history/clip/{sid}/{d}/{p.name}",
                "mime": mime,
                "alt_url": alt_url,
                "alt_mime": alt_mime,
            }
        )

    return {"stream_id": sid, "date": d, "clips": clips}


def _media_type_for_path(p: Path) -> str:
    return "video/webm" if p.suffix.lower() == ".webm" else "video/mp4"


def _transcode_mp4_to_webm(src: Path, dst: Path) -> None:
    # Best-effort conversion using OpenCV/FFmpeg bindings.
    # Writes to a temp file then renames atomically.
    import cv2

    cap = cv2.VideoCapture(str(src))
    if not cap.isOpened():
        raise RuntimeError("Failed to open source clip for transcoding")

    fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
    if not (1.0 < fps < 121.0):
        fps = 15.0
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    if w <= 0 or h <= 0:
        # Fallback: grab one frame to infer size
        ok, frame = cap.read()
        if not ok or frame is None:
            cap.release()
            raise RuntimeError("Failed to read frames for transcoding")
        h, w = frame.shape[:2]
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

    # Create temp file on the same drive as destination (Windows can't os.replace across drives).
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp_fd = None
    tmp_path = None
    try:
        tmp_fd, tmp_path = tempfile.mkstemp(prefix=f"iw-transcode-{dst.stem}-", suffix=".webm", dir=str(dst.parent))
        os.close(tmp_fd)
        tmp = Path(tmp_path)
    except Exception:
        # Fallback: best-effort unique name in destination folder.
        tmp = dst.parent / f"iw-transcode-{dst.stem}-{int(time.time())}.webm"
    try:
        cc = cv2.VideoWriter_fourcc(*"VP80")
        writer = cv2.VideoWriter(str(tmp), cc, fps, (w, h))
        if not writer.isOpened():
            writer.release()
            cap.release()
            raise RuntimeError("Failed to initialize WebM writer")

        while True:
            ok, frame = cap.read()
            if not ok or frame is None:
                break
            writer.write(frame)

        writer.release()
        cap.release()

        if not tmp.exists() or tmp.stat().st_size < 1024:
            raise RuntimeError("Transcode produced an empty WebM")

        os.replace(str(tmp), str(dst))
    finally:
        try:
            if tmp.exists():
                tmp.unlink(missing_ok=True)
        except Exception:
            pass


@router.get("/clip/{stream_id}/{date}/{filename}")
def get_clip(stream_id: str, date: str, filename: str, request: Request, format: str | None = None):
    p = _safe_clip_path(stream_id, date, filename)

    if not p.exists() or not p.is_file():
        raise HTTPException(status_code=404, detail="Clip not found")

    # Optional on-demand conversion for browser playback.
    # If the frontend requests ?format=webm for an MP4, convert once and cache alongside the original.
    if format and str(format).strip().lower() == "webm":
        if p.suffix.lower() == ".webm":
            pass
        elif p.suffix.lower() == ".mp4":
            webm_path = p.with_suffix(".webm")
            try:
                if (not webm_path.exists()) or (webm_path.stat().st_mtime < p.stat().st_mtime):
                    _transcode_mp4_to_webm(p, webm_path)
                p = webm_path
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to transcode clip: {e}")

    file_size = int(p.stat().st_size)
    range_header = request.headers.get("range") or request.headers.get("Range")

    # Support byte-range requests for HTML5 video playback.
    # Example: Range: bytes=0-1023
    if range_header:
        m = re.match(r"^bytes=(\d+)-(\d*)$", range_header.strip())
        if not m:
            raise HTTPException(status_code=416, detail="Invalid Range header")

        start = int(m.group(1))
        end_s = m.group(2)
        end = int(end_s) if end_s else (file_size - 1)

        if start >= file_size:
            raise HTTPException(status_code=416, detail="Range start out of bounds")
        end = min(end, file_size - 1)
        if end < start:
            raise HTTPException(status_code=416, detail="Invalid Range")

        chunk_size = 1024 * 1024
        length = (end - start) + 1

        def _iterfile():
            with open(p, "rb") as f:
                f.seek(start)
                remaining = length
                while remaining > 0:
                    data = f.read(min(chunk_size, remaining))
                    if not data:
                        break
                    remaining -= len(data)
                    yield data

        headers = {
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(length),
        }
        return StreamingResponse(_iterfile(), status_code=206, media_type=_media_type_for_path(p), headers=headers)

    # No range: serve full file. Still advertise Accept-Ranges.
    return FileResponse(
        str(p),
        media_type=_media_type_for_path(p),
        filename=os.path.basename(str(p)),
        headers={"Accept-Ranges": "bytes"},
    )


@router.delete("/clip/{stream_id}/{date}/{filename}")
def delete_clip(stream_id: str, date: str, filename: str):
    p = _safe_clip_path(stream_id, date, filename)
    if not p.exists() or not p.is_file():
        raise HTTPException(status_code=404, detail="Clip not found")

    deleted_files: list[str] = []
    try:
        p.unlink(missing_ok=True)
        deleted_files.append(p.name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete clip: {e}")

    # If deleting an MP4, also delete a cached WebM transcode (same stem).
    try:
        if p.suffix.lower() == ".mp4":
            w = p.with_suffix(".webm")
            if w.exists() and w.is_file():
                w.unlink(missing_ok=True)
                deleted_files.append(w.name)
            wmeta = w.with_suffix(w.suffix + ".json")
            if wmeta.exists() and wmeta.is_file():
                wmeta.unlink(missing_ok=True)
                deleted_files.append(wmeta.name)
    except Exception:
        pass

    meta = p.with_suffix(p.suffix + ".json")
    try:
        if meta.exists() and meta.is_file():
            meta.unlink(missing_ok=True)
            deleted_files.append(meta.name)
    except Exception:
        pass

    try:
        day_dir = p.parent
        if day_dir.exists() and day_dir.is_dir() and not any(day_dir.iterdir()):
            day_dir.rmdir()
        stream_dir = day_dir.parent
        if stream_dir.exists() and stream_dir.is_dir() and not any(stream_dir.iterdir()):
            stream_dir.rmdir()
    except Exception:
        pass

    return {"message": "Clip deleted", "deleted": deleted_files}

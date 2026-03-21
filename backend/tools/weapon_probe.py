from __future__ import annotations

import os
from pathlib import Path

import cv2
from ultralytics import YOLO


def _env(name: str) -> str:
    v = os.getenv(name)
    if not v:
        raise SystemExit(f"Missing env var {name}")
    return v


def main() -> None:
    video = Path(_env("PROBE_VIDEO")).resolve()
    model = Path(_env("PROBE_WEAPON_MODEL")).resolve()

    if not video.exists():
        raise SystemExit(f"Video not found: {video}")
    if not model.exists():
        raise SystemExit(f"Model not found: {model}")

    imgsz = int(os.getenv("PROBE_IMGSZ", "960"))
    conf = float(os.getenv("PROBE_CONF", "0.05"))
    max_samples = int(os.getenv("PROBE_SAMPLES", "30"))

    m = YOLO(str(model))
    cap = cv2.VideoCapture(str(video))
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)

    step = max(1, (total // max_samples) if total > 0 else 15)
    idxs = (list(range(0, total, step))[:max_samples] if total > 0 else list(range(0, 450, step))[:max_samples])

    best: dict[str, float] = {}
    for fi in idxs:
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(fi))
        ok, frame = cap.read()
        if not ok or frame is None:
            continue

        results = m(frame, conf=conf, imgsz=imgsz, verbose=False)
        for r in results:
            for b in r.boxes:
                cls = int(b.cls[0])
                name = str(m.names.get(cls, cls)).strip().lower()
                try:
                    score = float(b.conf[0])
                except Exception:
                    score = 0.0
                if (name not in best) or score > best[name]:
                    best[name] = score

    cap.release()

    keys = sorted(best.items(), key=lambda kv: kv[1], reverse=True)
    print("video", str(video))
    print("model", str(model))
    print("total_frames", total, "sampled", len(idxs), "step", step)
    print("top_labels")
    for k, v in keys[:10]:
        print(k, round(v, 3))
    print("pistol_best", round(best.get("pistol", 0.0), 3))
    print("knife_best", round(best.get("knife", 0.0), 3))


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
import math
from pathlib import Path


def iter_label_lines(labels_dir: Path):
    for lf in labels_dir.rglob("*.txt"):
        try:
            lines = lf.read_text(encoding="utf-8", errors="ignore").splitlines()
        except Exception:
            continue
        for line_no, raw in enumerate(lines, start=1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            yield lf, line_no, line


def validate_labels_dir(labels_dir: Path, nc: int) -> tuple[int, int, list[tuple[str, int, str, str]]]:
    """Return (total_lines, bad_lines, examples[])."""
    total = 0
    bad = 0
    examples: list[tuple[str, int, str, str]] = []

    for lf, line_no, line in iter_label_lines(labels_dir):
        total += 1
        parts = line.split()
        if len(parts) != 5:
            bad += 1
            if len(examples) < 5:
                examples.append((str(lf), line_no, line, "expected 5 columns"))
            continue

        try:
            cls = int(float(parts[0]))
            x, y, w, h = map(float, parts[1:])
        except Exception:
            bad += 1
            if len(examples) < 5:
                examples.append((str(lf), line_no, line, "failed to parse"))
            continue

        if cls < 0 or cls >= nc:
            bad += 1
            if len(examples) < 5:
                examples.append((str(lf), line_no, line, f"class_id {cls} out of range 0..{nc-1}"))
            continue

        nums = [x, y, w, h]
        if any(math.isnan(v) or math.isinf(v) for v in nums):
            bad += 1
            if len(examples) < 5:
                examples.append((str(lf), line_no, line, "NaN/Inf in coords"))
            continue

        if not (0.0 <= x <= 1.0 and 0.0 <= y <= 1.0 and 0.0 < w <= 1.0 and 0.0 < h <= 1.0):
            bad += 1
            if len(examples) < 5:
                examples.append((str(lf), line_no, line, f"coords out of range: x,y,w,h={x,y,w,h}"))
            continue

    return total, bad, examples


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate YOLO label files for common issues")
    ap.add_argument("--nc", type=int, required=True, help="Number of classes")
    ap.add_argument(
        "labels_dirs",
        nargs="+",
        type=Path,
        help="One or more labels directories (folders containing .txt files)",
    )
    args = ap.parse_args()

    any_bad = False
    for labels_dir in args.labels_dirs:
        labels_dir = labels_dir.expanduser().resolve()
        if not labels_dir.exists():
            print(f"MISSING: {labels_dir}")
            any_bad = True
            continue

        total, bad, examples = validate_labels_dir(labels_dir, nc=int(args.nc))
        print(f"{labels_dir}: label_lines={total} bad_lines={bad}")
        for ex in examples:
            print("  example:", ex)
        if bad:
            any_bad = True

    return 1 if any_bad else 0


if __name__ == "__main__":
    raise SystemExit(main())

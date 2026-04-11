from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

import yaml


IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def _listify(x):
    if x is None:
        return []
    if isinstance(x, (list, tuple)):
        return list(x)
    return [x]


def _resolve_dir(yaml_path: Path, raw: str) -> Path:
    p = Path(raw)
    if p.is_absolute():
        return p
    # Ultralytics resolves relative to the YAML directory.
    return (yaml_path.parent / p).resolve()


def _count_images(img_dir: Path) -> int:
    if not img_dir.exists():
        return 0
    total = 0
    for ext in IMAGE_EXTS:
        total += sum(1 for _ in img_dir.rglob(f"*{ext}"))
    return total


def _iter_label_files(img_dir: Path) -> list[Path]:
    # Standard YOLO layout: .../images and .../labels
    if img_dir.name != "images":
        label_dir = img_dir.parent / "labels"
    else:
        label_dir = img_dir.parent.parent / "labels" / img_dir.name
        # Fallback to sibling labels
        if not label_dir.exists():
            label_dir = img_dir.parent / "labels"
    if not label_dir.exists():
        return []
    return list(label_dir.rglob("*.txt"))


def main() -> int:
    ap = argparse.ArgumentParser(description="Inspect a YOLO dataset YAML and print basic stats")
    ap.add_argument("--data", required=True, help="Path to data.yaml")
    ap.add_argument("--max-label-files", type=int, default=0, help="Limit label-file scan (0=all)")
    args = ap.parse_args()

    yaml_path = Path(args.data).expanduser().resolve()
    if not yaml_path.exists():
        raise SystemExit(f"data yaml not found: {yaml_path}")

    obj = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    names = obj.get("names")
    nc = obj.get("nc")

    print(f"Dataset YAML: {yaml_path}")
    print(f"nc: {nc}")
    print(f"names: {names}")

    split_dirs = {}
    for split in ("train", "val", "test"):
        raw_dirs = _listify(obj.get(split))
        split_dirs[split] = [str(d) for d in raw_dirs]

    print("\nSplits:")
    for split, raw_dirs in split_dirs.items():
        print(f"- {split}: {raw_dirs}")

    print("\nResolved paths + image counts:")
    totals = {}
    for split, raw_dirs in split_dirs.items():
        total = 0
        for raw in raw_dirs:
            d = _resolve_dir(yaml_path, raw)
            n = _count_images(d)
            total += n
            print(f"  {split}: {raw} -> {d}  images={n}  exists={d.exists()}")
        totals[split] = total

    print("\nTotals:")
    for split in ("train", "val", "test"):
        print(f"- {split} images: {totals.get(split, 0)}")

    # Basic class distribution from labels (best-effort)
    print("\nLabel distribution (best-effort):")
    class_counts: Counter[int] = Counter()
    label_files_scanned = 0
    for split, raw_dirs in split_dirs.items():
        for raw in raw_dirs:
            img_dir = _resolve_dir(yaml_path, raw)
            label_files = _iter_label_files(img_dir)
            if not label_files:
                print(f"  {split}: no labels found near {img_dir}")
                continue
            for lf in label_files:
                try:
                    for line in lf.read_text(encoding="utf-8", errors="ignore").splitlines():
                        parts = line.strip().split()
                        if not parts:
                            continue
                        cls = int(float(parts[0]))
                        class_counts[cls] += 1
                except Exception:
                    continue
                label_files_scanned += 1
                if args.max_label_files and label_files_scanned >= args.max_label_files:
                    break
            if args.max_label_files and label_files_scanned >= args.max_label_files:
                break
        if args.max_label_files and label_files_scanned >= args.max_label_files:
            break

    if not class_counts:
        print("  (no labels scanned)")
    else:
        for cls, cnt in class_counts.most_common():
            name = None
            try:
                if isinstance(names, list) and 0 <= cls < len(names):
                    name = str(names[cls])
                elif isinstance(names, dict) and str(cls) in names:
                    name = str(names[str(cls)])
            except Exception:
                name = None
            label = f"{cls}" + (f" ({name})" if name else "")
            print(f"  - {label}: {cnt}")
        print(f"  label files scanned: {label_files_scanned}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

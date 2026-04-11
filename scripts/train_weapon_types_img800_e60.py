from __future__ import annotations

import argparse
import math
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser(description="Train weapon-type YOLO model")
    ap.add_argument(
        "--data",
        default=str(Path("datasets") / "data_combined_archive_archive1.yaml"),
        help="Path to YOLO data.yaml",
    )
    ap.add_argument("--model", default="yolov8s.pt", help="Base model or checkpoint")
    ap.add_argument("--epochs", type=int, default=60)
    ap.add_argument("--imgsz", type=int, default=800)
    ap.add_argument("--device", default="0", help="CUDA device index (e.g., 0) or 'cpu'")
    ap.add_argument("--project", default=str(Path("runs_weapon")), help="Output root folder")
    ap.add_argument("--name", default="weapon_types_img800_e60", help="Run name")
    ap.add_argument("--batch", type=int, default=-1, help="Batch size (-1=auto)")
    ap.add_argument(
        "--resume-from",
        default="",
        help="Resume from a checkpoint path (e.g. runs_weapon/<run>/weights/last.pt). Keeps optimizer state.",
    )
    ap.add_argument(
        "--no-amp",
        action="store_true",
        help="Disable Automatic Mixed Precision (can help if you see NaN losses)",
    )
    ap.add_argument(
        "--map-patience",
        type=int,
        default=0,
        help="Early-stop if mAP50-95 does not improve for N consecutive epochs (0=disabled)",
    )
    ap.add_argument(
        "--map-warmup-epochs",
        type=int,
        default=0,
        help="Ignore mAP early-stop for the first N epochs (useful because mAP can stay flat early)",
    )
    args = ap.parse_args()

    resume_from = str(args.resume_from).strip()
    data_path: Path | None = None
    if not resume_from:
        data_path = Path(args.data).expanduser().resolve()
        if not data_path.exists():
            raise SystemExit(f"data.yaml not found: {data_path}")

    from ultralytics import YOLO
    if resume_from:
        ckpt_path = Path(resume_from).expanduser().resolve()
        if not ckpt_path.exists():
            raise SystemExit(f"resume checkpoint not found: {ckpt_path}")
        model = YOLO(str(ckpt_path))
    else:
        model = YOLO(str(args.model))

    # --- Per-epoch accuracy (mAP) reporting ---
    last_map5095: float | None = None
    best_map5095: float | None = None
    best_epoch: int | None = None
    no_improve_streak = 0

    def _get_metric(metrics: dict, keys: list[str]) -> float | None:
        for k in keys:
            if k in metrics:
                try:
                    v = float(metrics[k])
                except Exception:
                    continue
                if math.isnan(v) or math.isinf(v):
                    return None
                return v
        return None

    def on_fit_epoch_end(trainer):
        nonlocal last_map5095, best_map5095, best_epoch, no_improve_streak

        metrics = getattr(trainer, "metrics", {}) or {}
        map5095 = _get_metric(metrics, ["metrics/mAP50-95(B)", "metrics/mAP50-95", "mAP50-95"])
        map50 = _get_metric(metrics, ["metrics/mAP50(B)", "metrics/mAP50", "mAP50"])

        # Always print something epoch-scoped so it's easy to track in logs.
        epoch_num = int(getattr(trainer, "epoch", -1)) + 1

        improved_prev = None
        improved_best = None
        if map5095 is not None and last_map5095 is not None:
            improved_prev = map5095 > last_map5095

        if map5095 is not None:
            if best_map5095 is None:
                best_map5095 = map5095
                best_epoch = epoch_num
                improved_best = True
            elif map5095 > best_map5095:
                best_map5095 = map5095
                best_epoch = epoch_num
                improved_best = True
            else:
                improved_best = False

        status = ""
        if improved_prev is True:
            status = "(improved vs prev)"
        elif improved_prev is False:
            status = "(no improvement vs prev)"

        map5095_str = f"{map5095:.4f}" if map5095 is not None else "n/a"
        map50_str = f"{map50:.4f}" if map50 is not None else "n/a"
        best_str = f"{best_map5095:.4f}@{best_epoch}" if best_map5095 is not None and best_epoch else "n/a"
        print(
            f"[epoch {epoch_num}] mAP50-95={map5095_str} mAP50={map50_str} best(mAP50-95)={best_str} {status}",
            flush=True,
        )

        # Optional early-stopping based on mAP trend.
        if int(args.map_patience) > 0 and map5095 is not None:
            if epoch_num <= int(args.map_warmup_epochs):
                no_improve_streak = 0
            else:
                if improved_best is True:
                    no_improve_streak = 0
                elif improved_best is False:
                    no_improve_streak += 1

                if no_improve_streak >= int(args.map_patience):
                    print(
                        f"[early-stop] mAP50-95 did not improve for {no_improve_streak} epochs (patience={args.map_patience}).",
                        flush=True,
                    )
                    # Ultralytics trainer checks this flag after on_fit_epoch_end.
                    trainer.stop = True

    model.add_callback("on_fit_epoch_end", on_fit_epoch_end)

    try:
        train_kwargs = {
            "imgsz": int(args.imgsz),
            "batch": int(args.batch),
            "amp": not bool(args.no_amp),
        }

        if resume_from:
            # True resume (optimizer + scheduler state) from checkpoint.
            train_kwargs["resume"] = str(Path(resume_from).expanduser().resolve())
            train_kwargs["device"] = str(args.device)
        else:
            # Fresh run.
            train_kwargs.update(
                {
                    "data": str(data_path),
                    "epochs": int(args.epochs),
                    "device": str(args.device),
                    "project": str(args.project),
                    "name": str(args.name),
                }
            )

        results = model.train(**train_kwargs)
    except KeyboardInterrupt:
        # Ultralytics saves periodic checkpoints; show user a good next step.
        if resume_from:
            print(f"\nInterrupted. Resume again with --resume-from {resume_from}")
        else:
            last_guess = Path(args.project) / args.name / "weights" / "last.pt"
            print(f"\nInterrupted. To resume: --resume-from {last_guess}")
        return 1

    # Ultralytics returns a Results object; best.pt path is typically under:
    # <project>/<name>/weights/best.pt
    print("\nTraining complete.")
    try:
        save_dir = getattr(results, "save_dir", None)
        if save_dir:
            print("Save dir:", save_dir)
    except Exception:
        pass

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

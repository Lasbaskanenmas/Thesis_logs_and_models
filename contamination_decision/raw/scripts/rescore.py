#!/usr/bin/env python
# coding: utf-8
"""
Task 2: rescore every completed matrix cell on the 18,033 uncontaminated tiles.

Method (exact, not approximate). The pooled out-of-fold confusion matrix is a SUM over tiles:
    CM_all = sum_over_all_tiles CM_tile
so the clean matrix is obtained by subtraction:
    CM_clean = CM_all - sum_over_contaminated_tiles CM_tile
CM_all is read from each cell's already-persisted pooled_oof_metrics.json
("global_confusion_matrix"); only the 1,281 contaminated tiles are re-read from disk. This is
arithmetically identical to rescoring all 18,033 tiles, at 1/15th of the I/O.

Guards:
  * every entry of CM_clean must be >= 0  (fails loud otherwise)
  * metrics recomputed from the STORED CM_all must reproduce the published macro_iou exactly
  * --verify_cell CELL additionally recomputes CM_all for one cell from disk, tile by tile, and
    compares it element-wise with the stored matrix. That is the check that the persisted
    matrices still correspond to the prediction rasters on disk.

Reuses the frozen scorer: analyse/per_category_metrics.py (metrics_from_confusion,
pooled_confusion_matrix) so the metric definitions are byte-identical to the ones that produced
the published figures.

Read-only outside OUT_DIR.
"""
import argparse
import csv
import json
import os
import re
import sys
import time

import numpy as np
from PIL import Image

ROOT = r"C:\thesis"
REPO = os.path.join(ROOT, "ML_sdfi_fastai2")
ANALYSE = os.path.join(REPO, r"src\ML_sdfi_fastai2\analyse")
sys.path.insert(0, ANALYSE)
import per_category_metrics as pcm  # noqa: E402

CMD = os.path.join(REPO, "run_spatial_matrix.cmd")
LABELS = os.path.join(ROOT, r"multi_channel_dataset_creation\example_dataset\labels\splitted_labels")
CODES = os.path.join(ROOT, r"multi_channel_dataset_creation\example_dataset\labels\codes.txt")
FOLD_CSV = os.path.join(ROOT, r"logs_and_models\route_class_audit\fold_assignment.csv")
ALL_TXT = os.path.join(ROOT, r"multi_channel_dataset_creation\example_dataset\data\all.txt")
MATRIX = os.path.join(ROOT, r"logs_and_models\spatial_matrix")
OUT_DIR = os.path.join(ROOT, r"logs_and_models\contamination_decision")
RAW_DIR = os.path.join(OUT_DIR, "raw")
CONTAM = os.path.join(RAW_DIR, "contaminated_tiles.txt")

ROUTE_RE = re.compile(r"^O(\d{4})_(\d{2})_(\d{2})_.+_(\d+)_(\d+)\.tif$")
PREDICTED = ["asfalt", "fliser", "grus", "ubefestet", "green_roof",
             "drivhus", "betonflade", "brosten", "solceller"]
NFOLDS = 3


def log(msg=""):
    print(msg, flush=True)


def resolve(relpath):
    """Resolve a path written relative to the repo root inside run_spatial_matrix.cmd."""
    return os.path.normpath(os.path.join(REPO, relpath.replace("/", os.sep)))


def parse_cells_from_cmd():
    """Authoritative cell -> (pred_fold0, pred_fold1, pred_fold2) map, taken from the runner."""
    cells = {}
    pat = re.compile(
        r"--pred_fold0\s+(\S+)\s+--pred_fold1\s+(\S+)\s+--pred_fold2\s+(\S+)\s+--out\s+(\S+)")
    for line in open(CMD, encoding="utf8", errors="replace"):
        if "pooled_oof_metrics.py" not in line:
            continue
        m = pat.search(line)
        if not m:
            continue
        p0, p1, p2, out = m.groups()
        cell = os.path.basename(out.rstrip("/\\"))
        if cell.startswith("oof_"):
            cell = cell[4:]
        cells[cell] = {"pred": [resolve(p0), resolve(p1), resolve(p2)], "out": resolve(out)}
    return cells


def parse_route(fname):
    m = ROUTE_RE.match(fname.strip())
    return None if not m else f"{m.group(2)}-{m.group(3)}"


def load_folds():
    route_to_fold = {}
    with open(FOLD_CSV, newline="") as f:
        for row in csv.DictReader(f):
            route_to_fold[row["route"]] = int(row["fold"])
    folds = [[] for _ in range(NFOLDS)]
    for line in open(ALL_TXT, encoding="utf8", errors="replace"):
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        folds[route_to_fold[parse_route(s)]].append(s)
    return folds


def cm_for(tiles, pred_folder, label_cache, n_classes):
    """Pixel-summed confusion matrix over `tiles`, labels served from the in-memory cache."""
    cm = np.zeros(n_classes * n_classes, dtype=np.int64)
    for t in tiles:
        pred = np.asarray(Image.open(os.path.join(pred_folder, t)), dtype=np.int64)
        label = label_cache[t]
        if label.shape != pred.shape:
            sys.exit(f"shape mismatch {t}: {label.shape} vs {pred.shape}")
        if pred.max() >= n_classes:
            sys.exit(f"pred class index out of range in {t}: {pred.max()}")
        cm += np.bincount(label.ravel() * n_classes + pred.ravel(),
                          minlength=n_classes * n_classes)
    return cm.reshape(n_classes, n_classes)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify_cell", default="segformer_b1_rgb",
                    help="cell whose stored CM is re-derived from disk in full ('' to skip)")
    args = ap.parse_args()

    os.makedirs(RAW_DIR, exist_ok=True)
    codes = pcm.load_codes(CODES)
    n_classes = len(codes)
    folds = load_folds()
    contaminated = set(l.strip() for l in open(CONTAM) if l.strip())
    log(f"codes: {n_classes}  folds: {[len(f) for f in folds]}  contaminated: {len(contaminated):,}")

    contam_by_fold = [[t for t in folds[i] if t in contaminated] for i in range(NFOLDS)]
    log(f"contaminated per fold: {[len(x) for x in contam_by_fold]} "
        f"(total {sum(len(x) for x in contam_by_fold):,})")
    assert sum(len(x) for x in contam_by_fold) == len(contaminated)

    # ---- cache the 1,281 contaminated label rasters once (~1.3 GB as uint8) ----
    t0 = time.time()
    label_cache = {}
    for i in range(NFOLDS):
        for t in contam_by_fold[i]:
            p = os.path.join(LABELS, t)
            label_cache[t] = np.asarray(Image.open(p), dtype=np.int64)
    log(f"cached {len(label_cache):,} label rasters in {time.time()-t0:.1f}s")

    cells = parse_cells_from_cmd()
    log(f"cells parsed from run_spatial_matrix.cmd: {len(cells)}")

    # also pick up any oof folder with a metrics json that the cmd did not describe
    for model in sorted(os.listdir(MATRIX)):
        mdir = os.path.join(MATRIX, model)
        if not os.path.isdir(mdir):
            continue
        for d in sorted(os.listdir(mdir)):
            if not d.startswith("oof_"):
                continue
            if not os.path.isfile(os.path.join(mdir, d, "pooled_oof_metrics.json")):
                continue
            cell = d[4:]
            if cell not in cells:
                log(f"  NOTE: {cell} has a metrics json but no invocation in the cmd -> inferring")
                base = cell[:-4] if cell.endswith("_unw") else cell
                suf = "_unw" if cell.endswith("_unw") else ""
                cells[cell] = {
                    "pred": [os.path.join(mdir, f"{base}_fold{i}{suf}", "models", "example_dataset")
                             for i in range(NFOLDS)],
                    "out": os.path.join(mdir, d), "inferred": True}

    results, skipped, incons = [], [], []
    for cell in sorted(cells):
        info = cells[cell]
        jpath = os.path.join(info["out"], "pooled_oof_metrics.json")
        if not os.path.isfile(jpath):
            skipped.append((cell, "no pooled_oof_metrics.json"))
            continue
        missing = [p for p in info["pred"] if not os.path.isdir(p)
                   or not any(f.endswith(".tif") for f in os.listdir(p))]
        if missing:
            skipped.append((cell, f"prediction folder empty/missing: {missing}"))
            continue

        stored = json.load(open(jpath, encoding="utf8"))
        cm_all = np.array(stored["global_confusion_matrix"], dtype=np.int64)

        # guard 1: the stored matrix must reproduce the published headline exactly
        m_all = pcm.metrics_from_confusion(cm_all, codes, split_tag="pooled_oof_all")
        pub = stored["headline_pooled_oof"]["macro_iou"]
        if abs(m_all["macro_iou"] - pub) > 1e-12:
            incons.append(f"{cell}: recomputed macro_iou {m_all['macro_iou']!r} != stored {pub!r}")

        t1 = time.time()
        cm_contam = np.zeros((n_classes, n_classes), dtype=np.int64)
        for i in range(NFOLDS):
            cm_contam += cm_for(contam_by_fold[i], info["pred"][i], label_cache, n_classes)
        cm_clean = cm_all - cm_contam

        # guard 2: subtraction must not go negative anywhere
        if (cm_clean < 0).any():
            neg = int((cm_clean < 0).sum())
            incons.append(f"{cell}: CM_clean has {neg} negative entries -> stored CM does NOT "
                          f"match the predictions now on disk. Cell EXCLUDED.")
            skipped.append((cell, "negative entries after subtraction"))
            log(f"  {cell}: FAILED negative-entry guard, skipped")
            continue

        m_clean = pcm.metrics_from_confusion(cm_clean, codes, split_tag="pooled_oof_clean")
        m_contam = pcm.metrics_from_confusion(cm_contam, codes, split_tag="contaminated_only")

        row = {"cell": cell,
               "macro_iou_all": m_all["macro_iou"], "macro_iou_clean": m_clean["macro_iou"],
               "d_macro_iou": m_clean["macro_iou"] - m_all["macro_iou"],
               "macro_f1_all": m_all["macro_f1"], "macro_f1_clean": m_clean["macro_f1"],
               "d_macro_f1": m_clean["macro_f1"] - m_all["macro_f1"],
               "acc_all": m_all["overall_accuracy"], "acc_clean": m_clean["overall_accuracy"],
               "d_acc": m_clean["overall_accuracy"] - m_all["overall_accuracy"],
               "px_all": m_all["evaluated_pixels"], "px_clean": m_clean["evaluated_pixels"],
               "n_macro_all": m_all["n_macro_classes_evaluated"],
               "n_macro_clean": m_clean["n_macro_classes_evaluated"],
               "excluded_clean": ",".join(m_clean["excluded_absent"]),
               "published_macro_iou": pub,
               "inferred_paths": bool(info.get("inferred"))}
        for c in PREDICTED:
            a = m_all["per_class"][c]["iou"]
            b = m_clean["per_class"][c]["iou"]
            row[f"iou_all_{c}"] = a
            row[f"iou_clean_{c}"] = b
            row[f"d_{c}"] = (None if (a is None or b is None) else b - a)
        results.append(row)

        with open(os.path.join(RAW_DIR, f"rescore_{cell}.json"), "w", encoding="utf8") as f:
            json.dump({"cell": cell, "pred_folders": info["pred"],
                       "all_tiles": m_all, "clean_tiles": m_clean,
                       "contaminated_only": m_contam,
                       "cm_contaminated": cm_contam.tolist(),
                       "cm_clean": cm_clean.tolist()}, f, indent=2)
        log(f"  {cell:<36} mIoU {m_all['macro_iou']:.4f} -> {m_clean['macro_iou']:.4f} "
            f"(d={row['d_macro_iou']:+.4f})  {time.time()-t1:.0f}s")

    # ---------------- full-recompute verification for one cell ----------------
    verify = {}
    if args.verify_cell and args.verify_cell in cells:
        cell = args.verify_cell
        log(f"\nVERIFY: recomputing the FULL pooled CM for {cell} from disk "
            f"({sum(len(f) for f in folds):,} tiles)...")
        t1 = time.time()
        cm_re = np.zeros((n_classes, n_classes), dtype=np.int64)
        for i in range(NFOLDS):
            cm_re += pcm.pooled_confusion_matrix(folds[i], cells[cell]["pred"][i], LABELS,
                                                 n_classes=n_classes)
            log(f"    fold {i} done ({time.time()-t1:.0f}s)")
        stored = json.load(open(os.path.join(cells[cell]["out"], "pooled_oof_metrics.json")))
        cm_st = np.array(stored["global_confusion_matrix"], dtype=np.int64)
        identical = bool(np.array_equal(cm_re, cm_st))
        verify = {"cell": cell, "identical_to_stored": identical,
                  "max_abs_diff": int(np.abs(cm_re - cm_st).max()),
                  "seconds": time.time() - t1}
        log(f"  stored CM identical to freshly recomputed CM: {identical} "
            f"(max abs diff {verify['max_abs_diff']})")
        if not identical:
            incons.append(f"{cell}: freshly recomputed CM differs from stored "
                          f"(max abs diff {verify['max_abs_diff']})")

    # ---------------- persist ----------------
    results.sort(key=lambda r: r["d_macro_iou"])
    fields = list(results[0].keys()) if results else []
    with open(os.path.join(OUT_DIR, "task2_rescore_table.csv"), "w", newline="",
              encoding="utf8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in results:
            w.writerow(r)
    with open(os.path.join(RAW_DIR, "task2_summary.json"), "w", encoding="utf8") as f:
        json.dump({"n_cells_scored": len(results), "skipped": skipped,
                   "inconsistencies": incons, "verification": verify,
                   "n_contaminated": len(contaminated),
                   "contaminated_per_fold": [len(x) for x in contam_by_fold],
                   "results": results}, f, indent=2)

    log(f"\nscored {len(results)} cells; skipped {len(skipped)}")
    for c, why in skipped:
        log(f"  SKIPPED {c}: {why}")
    for s in incons:
        log(f"  INCONSISTENCY {s}")
    log(f"\nwrote {OUT_DIR}\\task2_rescore_table.csv")


if __name__ == "__main__":
    main()

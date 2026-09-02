#!/usr/bin/env python
# coding: utf-8
"""
Supplementary to Task 2: does the Task-2 delta measure LEAKAGE, or only a change in which ground
gets scored?

Dropping the 1,281 contaminated tiles changes the class mix of the evaluation set (solceller loses
43 % of its tiles, brosten 1.7 %). So a fall in Macro-IoU is not by itself evidence of leakage.

This isolates the leakage channel with a within-tile control. For every contaminated tile:

    shared window   = union of the rectangles it shares with cross-fold partner tiles
    unshared window = the rest of the SAME tile

Same tile, same image, same model, same fold. The only thing that differs is whether the model that
predicted this tile had already seen that ground's ground-truth polygons while training on another
fold. Composition is controlled by construction: any systematic gap between the two windows is the
leakage signal.

Tile geometry comes from tile_inventory.csv (easting = west edge, northing = north edge, 1000 px
at 0.1 m = 100 m square). The geometry is validated against the independently computed overlap_m2
column of cross_route_tile_overlaps.csv before any metric is reported.

Read-only outside OUT_DIR.
"""
import csv
import json
import os
import re
import sys
import time
from collections import defaultdict

import numpy as np
from PIL import Image

ROOT = r"C:\thesis"
REPO = os.path.join(ROOT, "ML_sdfi_fastai2")
sys.path.insert(0, os.path.join(REPO, r"src\ML_sdfi_fastai2\analyse"))
import per_category_metrics as pcm  # noqa: E402

OVERLAPS = os.path.join(ROOT, r"logs_and_models\filename_provenance\cross_route_tile_overlaps.csv")
TILE_INV = os.path.join(ROOT, r"exploratory_data_analysis\results\tables\tile_inventory.csv")
LABELS = os.path.join(ROOT, r"multi_channel_dataset_creation\example_dataset\labels\splitted_labels")
CODES = os.path.join(ROOT, r"multi_channel_dataset_creation\example_dataset\labels\codes.txt")
FOLD_CSV = os.path.join(ROOT, r"logs_and_models\route_class_audit\fold_assignment.csv")
ALL_TXT = os.path.join(ROOT, r"multi_channel_dataset_creation\example_dataset\data\all.txt")
MATRIX = os.path.join(ROOT, r"logs_and_models\spatial_matrix")
OUT_DIR = os.path.join(ROOT, r"logs_and_models\contamination_decision")
RAW_DIR = os.path.join(OUT_DIR, "raw")

PX, RES, SIDE = 1000, 0.1, 100.0
NFOLDS = 3
ROUTE_RE = re.compile(r"^O(\d{4})_(\d{2})_(\d{2})_.+_(\d+)_(\d+)\.tif$")
PREDICTED = ["asfalt", "fliser", "grus", "ubefestet", "green_roof",
             "drivhus", "betonflade", "brosten", "solceller"]

log_lines = []


def log(m=""):
    print(m, flush=True)
    log_lines.append(str(m))


def parse_route(f):
    m = ROUTE_RE.match(f.strip())
    return None if not m else f"{m.group(2)}-{m.group(3)}"


# ---------------------------------------------------------------- geometry
geom = {}
for row in csv.DictReader(open(TILE_INV, newline="")):
    geom[row["filename"]] = (float(row["easting"]), float(row["northing"]))

route_to_fold = {r["route"]: int(r["fold"]) for r in csv.DictReader(open(FOLD_CSV, newline=""))}
folds = [[] for _ in range(NFOLDS)]
for line in open(ALL_TXT, encoding="utf8", errors="replace"):
    s = line.strip()
    if not s or s.startswith("#"):
        continue
    folds[route_to_fold[parse_route(s)]].append(s)

rows = [r for r in csv.DictReader(open(OVERLAPS, newline="")) if r["fold_a"] != r["fold_b"]]
log(f"cross-fold pairs: {len(rows):,}")

# shared windows per tile, and a geometry check against the CSV's own overlap_m2
windows = defaultdict(list)
checked = bad = 0
for r in rows:
    for me, other in (("a", "b"), ("b", "a")):
        t, o = r[f"tile_{me}"], r[f"tile_{other}"]
        if t not in geom or o not in geom:
            continue
        ex, ny = geom[t]
        ox, oy = geom[o]
        x0, x1 = max(ex, ox), min(ex + SIDE, ox + SIDE)
        y0, y1 = max(ny - SIDE, oy - SIDE), min(ny, oy)
        if x1 <= x0 or y1 <= y0:
            continue
        if me == "a":
            checked += 1
            if abs((x1 - x0) * (y1 - y0) - float(r["overlap_m2"])) > 1.5:
                bad += 1
        c0 = int(round((x0 - ex) / RES))
        c1 = int(round((x1 - ex) / RES))
        r0 = int(round((ny - y1) / RES))
        r1 = int(round((ny - y0) / RES))
        windows[t].append((max(0, r0), min(PX, r1), max(0, c0), min(PX, c1)))

log(f"geometry check vs overlap_m2: {checked:,} rectangles compared, {bad} disagree by >1.5 m²")
if bad > checked * 0.01:
    sys.exit("tile geometry from tile_inventory.csv does not reproduce the published overlap areas")
log(f"tiles with at least one shared window: {len(windows):,}")

masks, shared_px, total_px = {}, 0, 0
for t, ws in windows.items():
    m = np.zeros((PX, PX), dtype=bool)
    for r0, r1, c0, c1 in ws:
        m[r0:r1, c0:c1] = True
    masks[t] = m
    shared_px += int(m.sum())
    total_px += PX * PX
log(f"shared pixels: {shared_px:,} of {total_px:,} contaminated-tile pixels "
    f"({100*shared_px/total_px:.2f} %)")

contam_by_fold = [[t for t in folds[i] if t in masks] for i in range(NFOLDS)]
log(f"contaminated tiles per fold: {[len(x) for x in contam_by_fold]}")

codes = pcm.load_codes(CODES)
NC = len(codes)
t0 = time.time()
lab = {t: np.asarray(Image.open(os.path.join(LABELS, t)), dtype=np.int64)
       for i in range(NFOLDS) for t in contam_by_fold[i]}
log(f"cached {len(lab):,} labels in {time.time()-t0:.1f}s")

# ---------------------------------------------------------------- cells
cells = {}
pat = re.compile(r"--pred_fold0\s+(\S+)\s+--pred_fold1\s+(\S+)\s+--pred_fold2\s+(\S+)\s+--out\s+(\S+)")
for line in open(os.path.join(REPO, "run_spatial_matrix.cmd"), encoding="utf8", errors="replace"):
    if "pooled_oof_metrics.py" not in line:
        continue
    m = pat.search(line)
    if m:
        p = [os.path.normpath(os.path.join(REPO, x.replace("/", os.sep))) for x in m.groups()[:3]]
        cells[os.path.basename(m.group(4).rstrip("/\\"))[4:]] = p
log(f"cells: {len(cells)}")

results = []
for cell in sorted(cells):
    pred = cells[cell]
    if not all(os.path.isdir(p) for p in pred):
        continue
    t1 = time.time()
    cm_s = np.zeros(NC * NC, dtype=np.int64)
    cm_u = np.zeros(NC * NC, dtype=np.int64)
    for i in range(NFOLDS):
        for t in contam_by_fold[i]:
            pr = np.asarray(Image.open(os.path.join(pred[i], t)), dtype=np.int64)
            lb, mk = lab[t], masks[t]
            cm_s += np.bincount(lb[mk] * NC + pr[mk], minlength=NC * NC)
            cm_u += np.bincount(lb[~mk] * NC + pr[~mk], minlength=NC * NC)
    ms = pcm.metrics_from_confusion(cm_s.reshape(NC, NC), codes, split_tag="shared_window")
    mu = pcm.metrics_from_confusion(cm_u.reshape(NC, NC), codes, split_tag="unshared_window")
    row = {"cell": cell,
           "acc_shared": ms["overall_accuracy"], "acc_unshared": mu["overall_accuracy"],
           "d_acc": ms["overall_accuracy"] - mu["overall_accuracy"],
           "miou_shared": ms["macro_iou"], "miou_unshared": mu["macro_iou"],
           "d_miou": ms["macro_iou"] - mu["macro_iou"],
           "px_shared": ms["evaluated_pixels"], "px_unshared": mu["evaluated_pixels"],
           "n_macro_shared": ms["n_macro_classes_evaluated"],
           "n_macro_unshared": mu["n_macro_classes_evaluated"]}
    for c in PREDICTED:
        a, b = ms["per_class"][c]["iou"], mu["per_class"][c]["iou"]
        row[f"iou_shared_{c}"], row[f"iou_unshared_{c}"] = a, b
        row[f"d_{c}"] = None if (a is None or b is None) else a - b
    results.append(row)
    log(f"  {cell:<36} acc {mu['overall_accuracy']:.4f}->{ms['overall_accuracy']:.4f} "
        f"(d={row['d_acc']:+.4f})  mIoU {mu['macro_iou']:.4f}->{ms['macro_iou']:.4f} "
        f"(d={row['d_miou']:+.4f})  {time.time()-t1:.0f}s")

os.makedirs(RAW_DIR, exist_ok=True)
with open(os.path.join(OUT_DIR, "task2b_shared_window_leakage.csv"), "w", newline="",
          encoding="utf8") as f:
    w = csv.DictWriter(f, fieldnames=list(results[0].keys()))
    w.writeheader()
    for r in results:
        w.writerow(r)

d_acc = np.array([r["d_acc"] for r in results])
d_miou = np.array([r["d_miou"] for r in results])
log(f"\n=== shared vs unshared window, across {len(results)} cells ===")
log(f"  accuracy gap  : mean {d_acc.mean():+.4f}  median {np.median(d_acc):+.4f}  "
    f"min {d_acc.min():+.4f}  max {d_acc.max():+.4f}  positive in {int((d_acc>0).sum())}/{len(d_acc)}")
log(f"  Macro-IoU gap : mean {d_miou.mean():+.4f}  median {np.median(d_miou):+.4f}  "
    f"min {d_miou.min():+.4f}  max {d_miou.max():+.4f}  "
    f"positive in {int((d_miou>0).sum())}/{len(d_miou)}")
log("  A POSITIVE gap means the model scores BETTER on ground whose labels it already saw in "
    "training = the leakage signature. A gap near zero means the Task-2 delta is composition, "
    "not leakage.")

with open(os.path.join(RAW_DIR, "task2b_shared_window.json"), "w", encoding="utf8") as f:
    json.dump({"shared_px": shared_px, "contaminated_tile_px": total_px,
               "geometry_rectangles_checked": checked, "geometry_disagreements": bad,
               "results": results,
               "summary": {"d_acc_mean": float(d_acc.mean()),
                           "d_acc_median": float(np.median(d_acc)),
                           "d_miou_mean": float(d_miou.mean()),
                           "d_miou_median": float(np.median(d_miou)),
                           "n_cells_positive_acc": int((d_acc > 0).sum()),
                           "n_cells": len(results)}}, f, indent=2)
with open(os.path.join(RAW_DIR, "task2b_log.txt"), "w", encoding="utf8") as f:
    f.write("\n".join(log_lines) + "\n")
log(f"\nwrote {OUT_DIR}\\task2b_shared_window_leakage.csv")

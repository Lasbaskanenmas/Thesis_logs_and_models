#!/usr/bin/env python
# coding: utf-8
"""
Route-matched control for the Task-2 delta.

The Task-2 delta (all tiles -> clean tiles) mixes two things: genuine leakage optimism, and the
fact that dropping 1,281 tiles changes WHICH ground is scored (solceller loses 43 % of its tiles).
The within-tile shared/unshared split is one control but is badly unbalanced (92.6 % vs 7.4 %, and
the unshared part is tile margins).

This is the better-matched control. Four routes contain BOTH contaminated and uncontaminated tiles:

    82-20 (fold 2): 522 contaminated / 86 clean
    85-45 (fold 2): 173 / 228
    84-41 (fold 2):  61 / 282
    84-40 (fold 0):  62 / 5,207

Within one route the terrain, the sensor, the flight and the held-out model are all the same. The
only systematic difference between the two groups is whether that ground's labels were also present,
under a different route number, in the model's training folds. A large positive gap on the
contaminated group is the leakage signature; a gap near zero says the Task-2 delta is composition.

Read-only outside OUT_DIR.
"""
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
sys.path.insert(0, os.path.join(REPO, r"src\ML_sdfi_fastai2\analyse"))
import per_category_metrics as pcm  # noqa: E402

LABELS = os.path.join(ROOT, r"multi_channel_dataset_creation\example_dataset\labels\splitted_labels")
CODES = os.path.join(ROOT, r"multi_channel_dataset_creation\example_dataset\labels\codes.txt")
FOLD_CSV = os.path.join(ROOT, r"logs_and_models\route_class_audit\fold_assignment.csv")
ALL_TXT = os.path.join(ROOT, r"multi_channel_dataset_creation\example_dataset\data\all.txt")
OUT_DIR = os.path.join(ROOT, r"logs_and_models\contamination_decision")
RAW_DIR = os.path.join(OUT_DIR, "raw")
CONTAM = os.path.join(RAW_DIR, "contaminated_tiles.txt")

ROUTE_RE = re.compile(r"^O(\d{4})_(\d{2})_(\d{2})_.+_(\d+)_(\d+)\.tif$")
PREDICTED = ["asfalt", "fliser", "grus", "ubefestet", "green_roof",
             "drivhus", "betonflade", "brosten", "solceller"]
NFOLDS = 3
lines = []


def log(m=""):
    print(m, flush=True)
    lines.append(str(m))


route_to_fold = {r["route"]: int(r["fold"]) for r in csv.DictReader(open(FOLD_CSV, newline=""))}
contam = set(l.strip() for l in open(CONTAM) if l.strip())
by_route = {}
for line in open(ALL_TXT, encoding="utf8", errors="replace"):
    s = line.strip()
    if not s or s.startswith("#"):
        continue
    m = ROUTE_RE.match(s)
    by_route.setdefault(f"{m.group(2)}-{m.group(3)}", []).append(s)

targets = {r: (sorted(t for t in ts if t in contam), sorted(t for t in ts if t not in contam))
           for r, ts in by_route.items()}
targets = {r: v for r, v in targets.items() if v[0] and v[1]}

# 84-40 contributes 5,207 clean tiles against only 62 contaminated ones; reading all of them for
# all 24 cells would dominate the runtime without sharpening the comparison. Cap the clean side at
# CAP tiles using a fixed-seed sample so the run is reproducible, and record what was capped.
CAP = 600
rng = np.random.default_rng(20260827)
capped = {}
for r, (c, u) in list(targets.items()):
    if len(u) > CAP:
        idx = rng.choice(len(u), size=CAP, replace=False)
        capped[r] = {"clean_total": len(u), "clean_sampled": CAP}
        targets[r] = (c, sorted(u[i] for i in idx))

log("routes with both contaminated and clean tiles:")
for r, (c, u) in sorted(targets.items()):
    note = (f"  [clean side subsampled from {capped[r]['clean_total']:,}, seed 20260827]"
            if r in capped else "")
    log(f"  {r} (fold {route_to_fold[r]}): {len(c):,} contaminated / {len(u):,} clean{note}")

codes = pcm.load_codes(CODES)
NC = len(codes)

cells = {}
pat = re.compile(r"--pred_fold0\s+(\S+)\s+--pred_fold1\s+(\S+)\s+--pred_fold2\s+(\S+)\s+--out\s+(\S+)")
for line in open(os.path.join(REPO, "run_spatial_matrix.cmd"), encoding="utf8", errors="replace"):
    if "pooled_oof_metrics.py" not in line:
        continue
    m = pat.search(line)
    if m:
        cells[os.path.basename(m.group(4).rstrip("/\\"))[4:]] = [
            os.path.normpath(os.path.join(REPO, x.replace("/", os.sep))) for x in m.groups()[:3]]
log(f"\ncells: {len(cells)}")

# cache labels for every tile of the four routes
t0 = time.time()
need = sorted({t for r in targets for grp in targets[r] for t in grp})
lab = {t: np.asarray(Image.open(os.path.join(LABELS, t)), dtype=np.int64) for t in need}
log(f"cached {len(lab):,} labels in {time.time()-t0:.1f}s")


def cm(tiles, folder):
    acc = np.zeros(NC * NC, dtype=np.int64)
    for t in tiles:
        pr = np.asarray(Image.open(os.path.join(folder, t)), dtype=np.int64)
        acc += np.bincount(lab[t].ravel() * NC + pr.ravel(), minlength=NC * NC)
    return acc.reshape(NC, NC)


rows = []
for cell in sorted(cells):
    pred = cells[cell]
    if not all(os.path.isdir(p) for p in pred):
        continue
    t1 = time.time()
    for r, (ct, ut) in sorted(targets.items()):
        f = route_to_fold[r]
        mc = pcm.metrics_from_confusion(cm(ct, pred[f]), codes, split_tag="contaminated")
        mu = pcm.metrics_from_confusion(cm(ut, pred[f]), codes, split_tag="clean")
        row = {"cell": cell, "route": r, "fold": f,
               "n_contam": len(ct), "n_clean": len(ut),
               "acc_contam": mc["overall_accuracy"], "acc_clean": mu["overall_accuracy"],
               "d_acc": mc["overall_accuracy"] - mu["overall_accuracy"],
               "miou_contam": mc["macro_iou"], "miou_clean": mu["macro_iou"],
               "d_miou": mc["macro_iou"] - mu["macro_iou"],
               "n_macro_contam": mc["n_macro_classes_evaluated"],
               "n_macro_clean": mu["n_macro_classes_evaluated"]}
        for c in PREDICTED:
            a, b = mc["per_class"][c]["iou"], mu["per_class"][c]["iou"]
            row[f"iou_contam_{c}"], row[f"iou_clean_{c}"] = a, b
            row[f"d_{c}"] = None if (a is None or b is None) else a - b
        rows.append(row)
    log(f"  {cell:<34} {time.time()-t1:.0f}s")

with open(os.path.join(OUT_DIR, "task2c_route_matched.csv"), "w", newline="", encoding="utf8") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader()
    for r in rows:
        w.writerow(r)

log("\n=== route-matched: contaminated minus clean, within the same route ===")
log(f"{'route':<8}{'fold':>5}{'n_con':>7}{'n_cln':>7}{'acc_con':>9}{'acc_cln':>9}{'d_acc':>9}"
    f"{'mIoU_con':>10}{'mIoU_cln':>10}{'d_mIoU':>9}{'cells+':>8}")
summ = {}
for r in sorted(targets):
    rs = [x for x in rows if x["route"] == r]
    da = np.array([x["d_acc"] for x in rs])
    dm = np.array([x["d_miou"] for x in rs if x["d_miou"] is not None])
    log(f"{r:<8}{rs[0]['fold']:>5}{rs[0]['n_contam']:>7,}{rs[0]['n_clean']:>7,}"
        f"{np.mean([x['acc_contam'] for x in rs]):>9.4f}"
        f"{np.mean([x['acc_clean'] for x in rs]):>9.4f}{da.mean():>+9.4f}"
        f"{np.mean([x['miou_contam'] for x in rs]):>10.4f}"
        f"{np.mean([x['miou_clean'] for x in rs]):>10.4f}{dm.mean():>+9.4f}"
        f"{int((da > 0).sum())}/{len(da):>3}")
    summ[r] = {"d_acc_mean": float(da.mean()), "d_miou_mean": float(dm.mean()),
               "n_cells_acc_positive": int((da > 0).sum()), "n_cells": len(da),
               "n_contam": rs[0]["n_contam"], "n_clean": rs[0]["n_clean"],
               "fold": rs[0]["fold"]}

log("\nper-class IoU gap (contaminated - clean), mean over cells, by route:")
log(f"{'route':<8}" + "".join(f"{c[:9]:>11}" for c in PREDICTED))
for r in sorted(targets):
    rs = [x for x in rows if x["route"] == r]
    cells_ = []
    for c in PREDICTED:
        vs = [x[f"d_{c}"] for x in rs if x[f"d_{c}"] is not None]
        cells_.append(f"{np.mean(vs):>+11.4f}" if vs else f"{'n/a':>11}")
    log(f"{r:<8}" + "".join(cells_))

with open(os.path.join(RAW_DIR, "task2c_route_matched.json"), "w", encoding="utf8") as f:
    json.dump({"summary": summ, "rows": rows, "clean_side_subsampled": capped,
               "subsample_seed": 20260827}, f, indent=2)
with open(os.path.join(RAW_DIR, "task2c_log.txt"), "w", encoding="utf8") as f:
    f.write("\n".join(lines) + "\n")
log(f"\nwrote {OUT_DIR}\\task2c_route_matched.csv")

#!/usr/bin/env python
# coding: utf-8
"""
Tasks 4 and 5 of the fold-contamination decision-support work order (2026-08-27).

Task 4  - what remedy (b) would imply: merge {82-20,82-21} and {85-45,85-48} into single blocking
          units (16 routes -> 14 units), report unit sizes, and establish by EXHAUSTIVE search
          whether a balanced feasible 3-fold split still exists under the same constraints
          build_spatial_folds.py enforced. Plus the GPU cost of rerunning the matrix, from the
          per-run wandb summaries actually on disk.
Task 5  - residual cross-fold ground sharing after the merge, recomputed from
          cross_route_tile_overlaps.csv under the new unit -> fold assignment.

Nothing is rebuilt or written outside OUT_DIR: fold_assignment.csv and all.txt are read only.
"""
import csv
import itertools
import json
import os
import re
from collections import Counter, defaultdict

ROOT = r"C:\thesis"
AUDIT = os.path.join(ROOT, r"logs_and_models\route_class_audit")
CLASS_ROUTES = os.path.join(AUDIT, "class_routes.json")
ROUTE_CSV = os.path.join(AUDIT, "route_class_audit.csv")
FOLD_CSV = os.path.join(AUDIT, "fold_assignment.csv")
ALL_TXT = os.path.join(ROOT, r"multi_channel_dataset_creation\example_dataset\data\all.txt")
OVERLAPS = os.path.join(ROOT, r"logs_and_models\filename_provenance\cross_route_tile_overlaps.csv")
MATRIX = os.path.join(ROOT, r"logs_and_models\spatial_matrix")
OUT_DIR = os.path.join(ROOT, r"logs_and_models\contamination_decision")
RAW_DIR = os.path.join(OUT_DIR, "raw")

PREDICTED = ["asfalt", "fliser", "grus", "ubefestet", "green_roof",
             "drivhus", "betonflade", "brosten", "solceller"]
RARE = ["green_roof", "drivhus", "betonflade", "brosten", "solceller"]
NFOLDS = 3
ROUTE_RE = re.compile(r"^O(\d{4})_(\d{2})_(\d{2})_.+_(\d+)_(\d+)\.tif$")

MERGES = [("82-20", "82-21"), ("85-45", "85-48")]

os.makedirs(RAW_DIR, exist_ok=True)
out_lines = []


def log(m=""):
    print(m, flush=True)
    out_lines.append(str(m))


# ------------------------------------------------------------------ inputs
route_tiles = Counter()
for line in open(ALL_TXT, encoding="utf8", errors="replace"):
    s = line.strip()
    if not s or s.startswith("#"):
        continue
    m = ROUTE_RE.match(s)
    route_tiles[f"{m.group(2)}-{m.group(3)}"] += 1

class_routes = {c: list(json.load(open(CLASS_ROUTES))["class_routes"][c]["any_pixel"])
                for c in PREDICTED}
route_tc, route_px, year_span = {}, {}, {}
for row in csv.DictReader(open(ROUTE_CSV, newline="")):
    route_tc[row["route"]] = {c: int(row[f"tiles_{c}"]) for c in PREDICTED}
    route_px[row["route"]] = {c: int(row[f"px_{c}"]) for c in PREDICTED}
    year_span[row["route"]] = row["year_span"]

frozen = {}
for row in csv.DictReader(open(FOLD_CSV, newline="")):
    frozen[row["route"]] = int(row["fold"])

routes = sorted(route_tiles)
TOTAL = sum(route_tiles.values())
log(f"routes: {len(routes)}   total tiles: {TOTAL:,}")


# ------------------------------------------------------------------ unit machinery
def build_units(merges):
    """route -> unit-name map and unit -> [routes], from a list of route groups to merge."""
    parent = {r: r for r in routes}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for grp in merges:
        base = find(grp[0])
        for r in grp[1:]:
            parent[find(r)] = base
    members = defaultdict(list)
    for r in routes:
        members[find(r)].append(r)
    unit_name = {root: "+".join(sorted(ms)) for root, ms in members.items()}
    r2u = {r: unit_name[find(r)] for r in routes}
    u2r = defaultdict(list)
    for r, u in r2u.items():
        u2r[u].append(r)
    return r2u, {u: sorted(rs) for u, rs in u2r.items()}


def unit_stats(u2r):
    tiles = {u: sum(route_tiles[r] for r in rs) for u, rs in u2r.items()}
    cr = {c: sorted({u for u, rs in u2r.items() if any(r in class_routes[c] for r in rs)})
          for c in PREDICTED}
    tc = {u: {c: sum(route_tc[r][c] for r in rs) for c in PREDICTED} for u, rs in u2r.items()}
    px = {u: {c: sum(route_px[r][c] for r in rs) for c in PREDICTED} for u, rs in u2r.items()}
    return tiles, cr, tc, px


def check(assign, cr, gr_units, whales):
    fails = []
    if len({assign[u] for u in gr_units}) < 2:
        fails.append(f"(a) green_roof units {gr_units} all in one fold")
    if assign[whales[0]] == assign[whales[1]]:
        fails.append(f"(b) whales {whales} share a fold")
    for c, us in cr.items():
        if len({assign[u] for u in us}) < 2:
            fails.append(f"(c) class {c} spans one fold only")
    return (not fails), fails


def leximin(assign, cr, tc, totals):
    ft = [0.0] * NFOLDS
    for c in RARE:
        for u in cr[c]:
            ft[assign[u]] += tc[u][c] / totals[c]
    return tuple(sorted(ft))


# ------------------------------------------------------------------ residual overlap
pairs = list(csv.DictReader(open(OVERLAPS, newline="")))

# The residual depends only on WHICH ROUTE PAIRS straddle a fold boundary, so pre-aggregate the
# 8,120 tile pairs by route pair once. There are only a handful of overlapping route pairs, which
# turns the per-assignment residual into a few dictionary lookups instead of an 8,120-row scan.
_by_rp = defaultdict(lambda: {"pairs": 0, "area": 0.0, "tiles": set()})
for p in pairs:
    k = (p["route_a"], p["route_b"])
    d = _by_rp[k]
    d["pairs"] += 1
    d["area"] += float(p["overlap_m2"])
    d["tiles"].add(p["tile_a"])
    d["tiles"].add(p["tile_b"])
_RP = [(k, v["pairs"], v["area"], frozenset(v["tiles"])) for k, v in _by_rp.items()]


_RESID_CACHE = {}


def residual(assign, r2u):
    """Cross-FOLD tile pairs / tiles / shared area under a route->unit->fold assignment.

    Two assignments that make the same set of route pairs straddle a fold boundary have the same
    residual, so the answer is memoised on that straddle pattern (a handful of distinct keys).
    """
    key = tuple(assign[r2u[ra]] != assign[r2u[rb]] for (ra, rb), _, _, _ in _RP)
    hit = _RESID_CACHE.get(key)
    if hit is not None:
        return hit
    n, area = 0, 0.0
    tiles = set()
    by_pair = Counter()
    for straddles, ((ra, rb), np_, ar, ts) in zip(key, _RP):
        if straddles:
            n += np_
            area += ar
            tiles |= ts
            by_pair[tuple(sorted((ra, rb)))] += np_
    out = {"pairs": n, "tiles": len(tiles), "pct_tiles": 100 * len(tiles) / TOTAL,
           "naive_area_m2": area,
           "by_route_pair": {f"{a} x {b}": v for (a, b), v in by_pair.items()}}
    _RESID_CACHE[key] = out
    return out


def search(u2r, label, extra_note=""):
    """Exhaustive feasible 3-fold search over the units, same objective as build_spatial_folds.py."""
    tiles, cr, tc, px = unit_stats(u2r)
    units = sorted(u2r)
    gr_units = cr["green_roof"]
    whales = sorted(units, key=lambda u: tiles[u], reverse=True)[:2]
    totals = {c: sum(tc[u][c] for u in units) for c in RARE}

    log(f"\n=== {label}: {len(units)} blocking units ===")
    for u in sorted(units, key=lambda x: -tiles[x]):
        merged = " (MERGED)" if len(u2r[u]) > 1 else ""
        ys = "+".join(sorted({y for r in u2r[u] for y in year_span[r].split("+")}))
        log(f"  {u:<16} {tiles[u]:>6,} tiles  {ys}{merged}")
    log(f"  green_roof units (hard span): {gr_units}")
    log(f"  whales (must split):          {whales}")
    if extra_note:
        log(f"  {extra_note}")

    free = [u for u in units if u not in whales]
    base = {whales[0]: 0, whales[1]: 1}
    best, n_pass, best_resid = None, 0, None
    r2u = {r: u for u, rs in u2r.items() for r in rs}
    for combo in itertools.product(range(NFOLDS), repeat=len(free)):
        assign = dict(base)
        assign.update(zip(free, combo))
        ok, _ = check(assign, cr, gr_units, whales)
        if not ok:
            continue
        n_pass += 1
        ft = [0, 0, 0]
        for u, f in assign.items():
            ft[f] += tiles[u]
        imb = max(ft) - min(ft)
        lex = leximin(assign, cr, tc, totals)
        s = "".join(str(assign[u]) for u in units)
        cand = {"imbalance": imb, "lex": lex, "s": s, "assign": dict(assign), "fold_tiles": ft}
        if best is None or imb < best["imbalance"] or (
                imb == best["imbalance"] and (lex > best["lex"] or
                                              (lex == best["lex"] and s < best["s"]))):
            best = cand
        rz = residual(assign, r2u)
        if best_resid is None or (rz["pairs"], imb) < (best_resid["r"]["pairs"],
                                                       best_resid["imbalance"]):
            best_resid = {"r": rz, "imbalance": imb, "assign": dict(assign), "fold_tiles": ft}

    if best is None:
        log("  NO FEASIBLE ASSIGNMENT EXISTS under the constraints.")
        return {"units": len(units), "feasible": 0, "unit_tiles": tiles}

    log(f"\n  feasible assignments passing the checker: {n_pass:,}")
    ft = best["fold_tiles"]
    log(f"  SELECTED (min imbalance, then leximin, then canonical): fold sizes "
        f"{ft[0]:,} / {ft[1]:,} / {ft[2]:,}   imbalance {best['imbalance']:,} tiles "
        f"({100*best['imbalance']/TOTAL:.2f} % of the pool)")
    for f in range(NFOLDS):
        us = sorted([u for u in units if best["assign"][u] == f], key=lambda x: -tiles[x])
        log(f"    fold {f}: {ft[f]:>6,} tiles | {us}")
    ok, fails = check(best["assign"], cr, gr_units, whales)
    log(f"  checker on selected: {'PASS' if ok else 'FAIL ' + str(fails)}")
    for c in PREDICTED:
        fs = sorted({best["assign"][u] for u in cr[c]})
        log(f"    (c) {c:<11} spans folds {fs} ({len(fs)}/3)")

    rsel = residual(best["assign"], r2u)
    log(f"\n  TASK 5 residual cross-fold sharing under the SELECTED assignment:")
    log(f"    cross-fold tile pairs : {rsel['pairs']:,}")
    log(f"    tiles involved        : {rsel['tiles']:,}  ({rsel['pct_tiles']:.2f} % of {TOTAL:,})")
    log(f"    naive summed overlap  : {rsel['naive_area_m2']/1e6:.4f} km²")
    if rsel["by_route_pair"]:
        log("    residual by route pair:")
        for k, v in sorted(rsel["by_route_pair"].items(), key=lambda x: -x[1]):
            log(f"      {k}: {v:,} pairs")
    log(f"  minimum achievable residual over all {n_pass:,} feasible assignments: "
        f"{best_resid['r']['pairs']:,} pairs / {best_resid['r']['tiles']:,} tiles "
        f"({best_resid['r']['pct_tiles']:.2f} %), at imbalance {best_resid['imbalance']:,}")

    return {"units": len(units), "feasible": n_pass, "unit_tiles": tiles,
            "selected": {"assign": best["assign"], "fold_tiles": ft,
                         "imbalance": best["imbalance"]},
            "residual_selected": rsel,
            "best_residual": {"pairs": best_resid["r"]["pairs"],
                              "tiles": best_resid["r"]["tiles"],
                              "pct_tiles": best_resid["r"]["pct_tiles"],
                              "imbalance": best_resid["imbalance"],
                              "fold_tiles": best_resid["fold_tiles"]}}


# ------------------------------------------------------------------ baseline (frozen split)
r2u_id, u2r_id = build_units([])
log("\n=== BASELINE: the frozen 16-route split, as a control ===")
ft0 = [0, 0, 0]
for r, f in frozen.items():
    ft0[f] += route_tiles[r]
log(f"  fold sizes {ft0[0]:,} / {ft0[1]:,} / {ft0[2]:,}  imbalance {max(ft0)-min(ft0):,}")
base_resid = residual({r: frozen[r] for r in routes}, {r: r for r in routes})
log(f"  cross-fold pairs {base_resid['pairs']:,}, tiles {base_resid['tiles']:,} "
    f"({base_resid['pct_tiles']:.2f} %), naive area {base_resid['naive_area_m2']/1e6:.4f} km²")
log("  by route pair: " + ", ".join(f"{k}: {n:,}"
                                    for k, n in sorted(base_resid["by_route_pair"].items(),
                                                       key=lambda x: -x[1])))

# ------------------------------------------------------------------ Task 4/5 main scenario
r2u_m, u2r_m = build_units(MERGES)
res_merged = search(u2r_m, "TASK 4 - merged {82-20,82-21} and {85-45,85-48}")

# ------------------------------------------------------------------ variant: merge everything entangled
route_pairs_overlapping = sorted({tuple(sorted((p["route_a"], p["route_b"]))) for p in pairs})
log(f"\n\n=== VARIANT: merge EVERY overlapping route pair present in the tile data "
    f"({len(route_pairs_overlapping)} pairs) ===")
log(f"  overlapping route pairs: {route_pairs_overlapping}")
r2u_all, u2r_all = build_units(route_pairs_overlapping)
res_all = search(u2r_all, "VARIANT - all entangled routes merged",
                 extra_note="this is the only variant that can drive the residual to zero")

# ------------------------------------------------------------------ GPU cost
log("\n\n=== TASK 4 - observed compute cost, from the wandb run summaries on disk ===")
jobs = []
for model in sorted(os.listdir(MATRIX)):
    mdir = os.path.join(MATRIX, model)
    if not os.path.isdir(mdir):
        continue
    for job in sorted(os.listdir(mdir)):
        wdir = os.path.join(mdir, job, "logs", "wandb")
        if not os.path.isdir(wdir):
            continue
        train_s, infer_s, n_tiles = None, None, None
        for run in sorted(os.listdir(wdir)):
            sp = os.path.join(wdir, run, "files", "wandb-summary.json")
            if not os.path.isfile(sp):
                continue
            try:
                s = json.load(open(sp, encoding="utf8"))
            except Exception:
                continue
            if "inference_seconds" in s:
                infer_s = (infer_s or 0) + float(s["inference_seconds"])
                n_tiles = s.get("n_tiles_classified", n_tiles)
            elif "_runtime" in s:
                train_s = max(train_s or 0, float(s["_runtime"]))
        if train_s or infer_s:
            jobs.append({"model": model, "job": job, "train_s": train_s,
                         "infer_s": infer_s, "n_tiles_classified": n_tiles})

with open(os.path.join(RAW_DIR, "task4_run_times.csv"), "w", newline="", encoding="utf8") as f:
    w = csv.DictWriter(f, fieldnames=["model", "job", "train_s", "infer_s", "n_tiles_classified"])
    w.writeheader()
    for j in jobs:
        w.writerow(j)

log(f"  jobs with a wandb summary: {len(jobs)}")
per_model = defaultdict(lambda: {"n": 0, "train": 0.0, "infer": 0.0, "n_train": 0, "n_infer": 0})
for j in jobs:
    d = per_model[j["model"]]
    d["n"] += 1
    if j["train_s"]:
        d["train"] += j["train_s"]
        d["n_train"] += 1
    if j["infer_s"]:
        d["infer"] += j["infer_s"]
        d["n_infer"] += 1
log(f"\n  {'model':<18} {'jobs':>5} {'train runs':>11} {'train h':>9} {'mean h/run':>11} "
    f"{'infer runs':>11} {'infer h':>9} {'total h':>9}")
tot_tr = tot_if = 0.0
for m in sorted(per_model):
    d = per_model[m]
    tr, inf = d["train"] / 3600, d["infer"] / 3600
    tot_tr += tr
    tot_if += inf
    mean = tr / d["n_train"] if d["n_train"] else float("nan")
    log(f"  {m:<18} {d['n']:>5} {d['n_train']:>11} {tr:>9.2f} {mean:>11.2f} "
        f"{d['n_infer']:>11} {inf:>9.2f} {tr+inf:>9.2f}")
log(f"  {'TOTAL':<18} {len(jobs):>5} {sum(d['n_train'] for d in per_model.values()):>11} "
    f"{tot_tr:>9.2f} {'':>11} {sum(d['n_infer'] for d in per_model.values()):>11} "
    f"{tot_if:>9.2f} {tot_tr+tot_if:>9.2f}")

n_train_runs = sum(d["n_train"] for d in per_model.values())
log(f"\n  Observed grand total on disk: {tot_tr+tot_if:.1f} GPU-hours over {n_train_runs} training "
    f"runs + {sum(d['n_infer'] for d in per_model.values())} inference runs.")

# cost of rerunning just the 24 published cells (72 fold-runs)
cells24 = {}
for j in jobs:
    mm = re.match(r"^(.*)_fold(\d)(_unw)?$", j["job"])
    if not mm:
        continue
    cell = mm.group(1) + (mm.group(3) or "")
    cells24.setdefault(cell, []).append(j)
pub = [c for c in cells24 if "_lc" not in c]
log(f"  distinct cells reconstructable from job names: {len(cells24)} "
    f"({len(pub)} excluding the lc25/50/75 probes)")
cost_pub = sum((j["train_s"] or 0) + (j["infer_s"] or 0)
               for c in pub for j in cells24[c]) / 3600
log(f"  cost of the {len(pub)} matrix cells alone (train+infer): {cost_pub:.1f} GPU-hours")

# the 24 cells actually published in matrix_results_all_cells.csv = what "rerun the matrix" means
PUBLISHED = [r["cell"] for r in csv.DictReader(
    open(os.path.join(MATRIX, "matrix_results_all_cells.csv"), newline=""))]
have = [c for c in PUBLISHED if c in cells24]
cost24 = sum((j["train_s"] or 0) + (j["infer_s"] or 0) for c in have for j in cells24[c]) / 3600
tr24 = sum(j["train_s"] or 0 for c in have for j in cells24[c]) / 3600
if24 = sum(j["infer_s"] or 0 for c in have for j in cells24[c]) / 3600
n24 = sum(len(cells24[c]) for c in have)
log(f"\n  >>> The 24 cells in matrix_results_all_cells.csv: {len(have)}/{len(PUBLISHED)} matched, "
    f"{n24} fold-runs")
log(f"  >>> RERUN COST of remedy (b) = {cost24:.1f} GPU-hours "
    f"({tr24:.1f} h training + {if24:.1f} h inference)")
log(f"  >>> mean per fold-run: {cost24/n24:.2f} h; on one GPU that is "
    f"{cost24/24:.1f} days of wall clock at 100 % utilisation")
missing24 = [c for c in PUBLISHED if c not in cells24]
if missing24:
    log(f"  >>> cells with no recoverable timing: {missing24}")

summary = {
    "total_tiles": TOTAL,
    "route_tiles": dict(route_tiles),
    "frozen_fold_sizes": ft0,
    "frozen_residual": base_resid,
    "merged_scenario": res_merged,
    "all_merged_variant": res_all,
    "overlapping_route_pairs": [list(p) for p in route_pairs_overlapping],
    "gpu_hours": {"train_h": tot_tr, "infer_h": tot_if, "total_h": tot_tr + tot_if,
                  "n_train_runs": n_train_runs,
                  "n_infer_runs": sum(d["n_infer"] for d in per_model.values()),
                  "per_model": {m: dict(d) for m, d in per_model.items()},
                  "matrix_cells_only_h": cost_pub, "n_cells": len(pub),
                  "published24": {"cells_matched": len(have), "n_fold_runs": n24,
                                  "total_h": cost24, "train_h": tr24, "infer_h": if24,
                                  "missing_timing": missing24}},
}
with open(os.path.join(RAW_DIR, "task4_5_merge_and_cost.json"), "w", encoding="utf8") as f:
    json.dump(summary, f, indent=2, default=str)
with open(os.path.join(RAW_DIR, "task4_5_log.txt"), "w", encoding="utf8") as f:
    f.write("\n".join(out_lines) + "\n")
log(f"\nwrote {RAW_DIR}\\task4_5_merge_and_cost.json, task4_run_times.csv, task4_5_log.txt")

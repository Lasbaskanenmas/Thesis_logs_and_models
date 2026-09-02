#!/usr/bin/env python
# coding: utf-8
"""
Prep + Task 3 for the fold-contamination decision-support work order (2026-08-27).

Builds the canonical contaminated-tile set from cross_route_tile_overlaps.csv, validates it
against all.txt and fold_assignment.csv, and characterises it against tile_inventory.csv.

Read-only outside OUT_DIR.
"""
import csv
import json
import os
import re
import sys
from collections import Counter, defaultdict

import numpy as np

ROOT = r"C:\thesis"
OVERLAPS = os.path.join(ROOT, r"logs_and_models\filename_provenance\cross_route_tile_overlaps.csv")
TILE_INV = os.path.join(ROOT, r"exploratory_data_analysis\results\tables\tile_inventory.csv")
FOLD_CSV = os.path.join(ROOT, r"logs_and_models\route_class_audit\fold_assignment.csv")
ALL_TXT = os.path.join(ROOT, r"multi_channel_dataset_creation\example_dataset\data\all.txt")
CODES = os.path.join(ROOT, r"multi_channel_dataset_creation\example_dataset\labels\codes.txt")
OUT_DIR = os.path.join(ROOT, r"logs_and_models\contamination_decision")
RAW_DIR = os.path.join(OUT_DIR, "raw")

ROUTE_RE = re.compile(r"^O(\d{4})_(\d{2})_(\d{2})_.+_(\d+)_(\d+)\.tif$")
PREDICTED = ["asfalt", "fliser", "grus", "ubefestet", "green_roof",
             "drivhus", "betonflade", "brosten", "solceller"]

os.makedirs(RAW_DIR, exist_ok=True)
log_lines = []


def log(msg=""):
    print(msg, flush=True)
    log_lines.append(str(msg))


def parse_route(fname):
    m = ROUTE_RE.match(fname.strip())
    return None if not m else f"{m.group(2)}-{m.group(3)}"


# ---------------------------------------------------------------- inputs
route_to_fold, route_tiles_declared = {}, {}
with open(FOLD_CSV, newline="") as f:
    for row in csv.DictReader(f):
        route_to_fold[row["route"]] = int(row["fold"])
        route_tiles_declared[row["route"]] = int(row["tiles"])

all_tiles, commented = [], []
for line in open(ALL_TXT, encoding="utf8", errors="replace"):
    s = line.strip()
    if not s:
        continue
    (commented if s.startswith("#") else all_tiles).append(s)

log(f"all.txt: {len(all_tiles):,} active tiles, {len(commented)} commented out")
assert len(all_tiles) == len(set(all_tiles)), "duplicate tiles in all.txt"

tile_fold, tile_route = {}, {}
for t in all_tiles:
    r = parse_route(t)
    assert r in route_to_fold, f"tile {t} -> route {r} not in fold_assignment"
    tile_route[t] = r
    tile_fold[t] = route_to_fold[r]

route_tiles_counted = Counter(tile_route.values())
mismatch = {r: (route_tiles_declared[r], route_tiles_counted[r])
            for r in route_to_fold if route_tiles_declared[r] != route_tiles_counted[r]}
log(f"fold_assignment tile counts match all.txt: {not mismatch}"
    + ("" if not mismatch else f"  MISMATCH {mismatch}"))

fold_sizes = Counter(tile_fold.values())
log(f"fold sizes from all.txt: " + ", ".join(f"fold{f}={fold_sizes[f]:,}" for f in sorted(fold_sizes)))

# ---------------------------------------------------------------- contaminated set
rows = list(csv.DictReader(open(OVERLAPS, newline="")))
log(f"\ncross_route_tile_overlaps.csv: {len(rows):,} cross-route pairs")

cross_fold_rows = [r for r in rows if r["fold_a"] != r["fold_b"]]
log(f"  of which cross-FOLD (fold_a != fold_b): {len(cross_fold_rows):,}")

# Validate the CSV's own fold columns against fold_assignment.csv
fold_disagree = 0
route_disagree = 0
not_in_all = set()
for r in rows:
    for side in ("a", "b"):
        t, rt, fd = r[f"tile_{side}"], r[f"route_{side}"], int(r[f"fold_{side}"])
        if t not in tile_fold:
            not_in_all.add(t)
            continue
        if tile_fold[t] != fd:
            fold_disagree += 1
        if tile_route[t] != rt:
            route_disagree += 1
log(f"  fold column disagreements vs fold_assignment.csv: {fold_disagree}")
log(f"  route column disagreements vs filename:           {route_disagree}")
log(f"  tiles in overlaps CSV not present in all.txt:      {len(not_in_all)}")

contaminated = set()
for r in cross_fold_rows:
    contaminated.add(r["tile_a"])
    contaminated.add(r["tile_b"])
contaminated &= set(all_tiles)
log(f"\nCONTAMINATED TILES (union of both sides of cross-fold pairs): {len(contaminated):,}")
log(f"  as share of {len(all_tiles):,}: {100*len(contaminated)/len(all_tiles):.2f} %")
clean = [t for t in all_tiles if t not in contaminated]
log(f"  clean tiles retained: {len(clean):,}")

# per-tile total cross-fold overlap area
tile_overlap_m2 = defaultdict(float)
tile_pair_count = Counter()
for r in cross_fold_rows:
    a2 = float(r["overlap_m2"])
    for side in ("a", "b"):
        tile_overlap_m2[r[f"tile_{side}"]] += a2
        tile_pair_count[r[f"tile_{side}"]] += 1

by_fold = Counter(tile_fold[t] for t in contaminated)
by_route = Counter(tile_route[t] for t in contaminated)
log("\nContaminated tiles by fold:")
for f in sorted(by_fold):
    log(f"  fold {f}: {by_fold[f]:>5,} / {fold_sizes[f]:,}  = {100*by_fold[f]/fold_sizes[f]:.2f} %")
log("\nContaminated tiles by route:")
for r in sorted(by_route, key=lambda x: -by_route[x]):
    log(f"  {r} (fold {route_to_fold[r]}): {by_route[r]:>5,} / {route_tiles_counted[r]:,}"
        f"  = {100*by_route[r]/route_tiles_counted[r]:.1f} %")

# overlap area distribution
areas_pair = np.array([float(r["overlap_m2"]) for r in cross_fold_rows])
areas_tile = np.array([tile_overlap_m2[t] for t in sorted(contaminated)])
log("\nCross-fold overlap area, PER PAIR (m^2 of a 10,000 m^2 tile):")
for lbl, v in [("min", areas_pair.min()), ("p10", np.percentile(areas_pair, 10)),
               ("median", np.median(areas_pair)), ("mean", areas_pair.mean()),
               ("p90", np.percentile(areas_pair, 90)), ("max", areas_pair.max())]:
    log(f"  {lbl:<7} {v:>10,.1f}")
log("\nCross-fold overlap area, PER CONTAMINATED TILE (summed over its pairs, may exceed 10,000):")
for lbl, v in [("min", areas_tile.min()), ("p10", np.percentile(areas_tile, 10)),
               ("median", np.median(areas_tile)), ("mean", areas_tile.mean()),
               ("p90", np.percentile(areas_tile, 90)), ("max", areas_tile.max())]:
    log(f"  {lbl:<7} {v:>10,.1f}")

# capped (union-free upper bound) per-tile share of the tile that is shared
capped = np.minimum(areas_tile, 10000.0)
log(f"\nPer-tile shared share, capped at the tile area (upper bound on the truly shared fraction):")
log(f"  median {np.median(capped)/100:.1f} %   mean {capped.mean()/100:.1f} %   "
    f"tiles >=50% shared: {int((capped>=5000).sum()):,}   >=90%: {int((capped>=9000).sum()):,}")

# ---------------------------------------------------------------- Task 3: class composition
inv = {}
with open(TILE_INV, newline="") as f:
    rdr = csv.DictReader(f)
    inv_fields = rdr.fieldnames
    for row in rdr:
        inv[row["filename"]] = row
log(f"\ntile_inventory.csv: {len(inv):,} rows")
missing_inv = [t for t in all_tiles if t not in inv]
log(f"  all.txt tiles missing from inventory: {len(missing_inv)}")

inv_fold_disagree = sum(1 for t in all_tiles if t in inv and int(inv[t]["fold"]) != tile_fold[t])
log(f"  inventory 'fold' column disagreements vs fold_assignment.csv: {inv_fold_disagree}")


def agg(tiles):
    px = {c: 0 for c in PREDICTED}
    tl = {c: 0 for c in PREDICTED}
    scored = 0
    for t in tiles:
        row = inv.get(t)
        if row is None:
            continue
        scored += int(row["n_scored_px"])
        for c in PREDICTED:
            v = int(row[f"px_{c}"])
            px[c] += v
            if v > 0:
                tl[c] += 1
    return px, tl, scored


px_all, tl_all, scored_all = agg(all_tiles)
px_con, tl_con, scored_con = agg(sorted(contaminated))
px_cln, tl_cln, scored_cln = agg(clean)

log(f"\nScored (non-unknown) label pixels:  all={scored_all:,}  "
    f"contaminated={scored_con:,} ({100*scored_con/scored_all:.2f} %)  clean={scored_cln:,}")

log("\n=== TASK 3: class support, contaminated set vs whole pool ===")
hdr = (f"{'class':<12} {'px_all':>14} {'px_contam':>13} {'%px lost':>9} "
       f"{'tiles_all':>10} {'tiles_contam':>13} {'%tiles lost':>12} {'tiles_clean':>12}")
log(hdr)
log("-" * len(hdr))
task3 = {}
for c in PREDICTED:
    pl = 100 * px_con[c] / px_all[c] if px_all[c] else float("nan")
    tlp = 100 * tl_con[c] / tl_all[c] if tl_all[c] else float("nan")
    log(f"{c:<12} {px_all[c]:>14,} {px_con[c]:>13,} {pl:>8.2f}% "
        f"{tl_all[c]:>10,} {tl_con[c]:>13,} {tlp:>11.2f}% {tl_cln[c]:>12,}")
    task3[c] = {"px_all": px_all[c], "px_contaminated": px_con[c], "px_clean": px_cln[c],
                "pct_px_lost": pl, "tiles_all": tl_all[c], "tiles_contaminated": tl_con[c],
                "tiles_clean": tl_cln[c], "pct_tiles_lost": tlp}

# representativeness: class mix of contaminated vs pool
log("\nClass mix (share of scored pixels within each set):")
log(f"{'class':<12} {'pool %':>9} {'contam %':>10} {'ratio':>8}")
for c in PREDICTED:
    a = 100 * px_all[c] / scored_all
    b = 100 * px_con[c] / scored_con if scored_con else 0.0
    log(f"{c:<12} {a:>8.4f}% {b:>9.4f}% {(b/a if a else float('nan')):>8.2f}")
    task3[c]["pool_pixel_share_pct"] = a
    task3[c]["contaminated_pixel_share_pct"] = b
    task3[c]["enrichment_ratio"] = (b / a) if a else None

# green_roof / drivhus / betonflade / solceller detail by route
log("\n=== Rare-class tile support by route, contaminated vs total ===")
for c in ["green_roof", "drivhus", "betonflade", "solceller", "brosten"]:
    log(f"\n  {c}:")
    per_route = defaultdict(lambda: [0, 0])   # route -> [tiles_with_class, contaminated_with_class]
    for t in all_tiles:
        row = inv.get(t)
        if row is None or int(row[f"px_{c}"]) == 0:
            continue
        r = tile_route[t]
        per_route[r][0] += 1
        if t in contaminated:
            per_route[r][1] += 1
    for r in sorted(per_route, key=lambda x: -per_route[x][0]):
        tot, con = per_route[r]
        log(f"    {r} (fold {route_to_fold[r]}): {tot:>5,} tiles with {c}, "
            f"{con:>5,} contaminated ({100*con/tot:.1f} %)")
    task3[c]["by_route"] = {r: {"tiles_with_class": v[0], "contaminated": v[1],
                                "fold": route_to_fold[r]} for r, v in per_route.items()}

# ---------------------------------------------------------------- persist
with open(os.path.join(RAW_DIR, "contaminated_tiles.csv"), "w", newline="", encoding="utf8") as f:
    w = csv.writer(f)
    w.writerow(["tile", "route", "fold", "n_cross_fold_pairs", "sum_overlap_m2", "capped_overlap_m2"])
    for t in sorted(contaminated):
        w.writerow([t, tile_route[t], tile_fold[t], tile_pair_count[t],
                    f"{tile_overlap_m2[t]:.1f}", f"{min(tile_overlap_m2[t], 10000.0):.1f}"])

with open(os.path.join(RAW_DIR, "clean_tiles.txt"), "w", encoding="utf8") as f:
    f.write("\n".join(clean) + "\n")
with open(os.path.join(RAW_DIR, "contaminated_tiles.txt"), "w", encoding="utf8") as f:
    f.write("\n".join(sorted(contaminated)) + "\n")

summary = {
    "n_all_tiles": len(all_tiles),
    "n_commented_out": len(commented),
    "n_cross_route_pairs": len(rows),
    "n_cross_fold_pairs": len(cross_fold_rows),
    "n_contaminated": len(contaminated),
    "n_clean": len(clean),
    "pct_contaminated": 100 * len(contaminated) / len(all_tiles),
    "fold_sizes": {str(k): v for k, v in sorted(fold_sizes.items())},
    "contaminated_by_fold": {str(k): v for k, v in sorted(by_fold.items())},
    "contaminated_by_route": dict(by_route),
    "route_to_fold": route_to_fold,
    "route_tiles": dict(route_tiles_counted),
    "scored_px_all": scored_all,
    "scored_px_contaminated": scored_con,
    "scored_px_clean": scored_cln,
    "overlap_per_pair_m2": {"min": float(areas_pair.min()), "median": float(np.median(areas_pair)),
                            "mean": float(areas_pair.mean()), "max": float(areas_pair.max()),
                            "p10": float(np.percentile(areas_pair, 10)),
                            "p90": float(np.percentile(areas_pair, 90))},
    "overlap_per_tile_m2": {"min": float(areas_tile.min()), "median": float(np.median(areas_tile)),
                            "mean": float(areas_tile.mean()), "max": float(areas_tile.max()),
                            "p10": float(np.percentile(areas_tile, 10)),
                            "p90": float(np.percentile(areas_tile, 90))},
    "capped_per_tile": {"median_pct": float(np.median(capped) / 100),
                        "mean_pct": float(capped.mean() / 100),
                        "n_ge_50pct": int((capped >= 5000).sum()),
                        "n_ge_90pct": int((capped >= 9000).sum())},
    "task3_class_support": task3,
    "consistency": {
        "fold_col_disagreements_overlaps_csv": fold_disagree,
        "route_col_disagreements_overlaps_csv": route_disagree,
        "overlap_tiles_not_in_all_txt": len(not_in_all),
        "inventory_fold_disagreements": inv_fold_disagree,
        "all_txt_tiles_missing_from_inventory": len(missing_inv),
        "fold_assignment_count_mismatch": mismatch,
        "n_tile_inventory_rows": len(inv),
    },
}
with open(os.path.join(RAW_DIR, "task3_contamination_profile.json"), "w", encoding="utf8") as f:
    json.dump(summary, f, indent=2)
with open(os.path.join(RAW_DIR, "task3_log.txt"), "w", encoding="utf8") as f:
    f.write("\n".join(log_lines) + "\n")
log(f"\nwrote {RAW_DIR}\\contaminated_tiles.csv, clean_tiles.txt, contaminated_tiles.txt, "
    f"task3_contamination_profile.json, task3_log.txt")

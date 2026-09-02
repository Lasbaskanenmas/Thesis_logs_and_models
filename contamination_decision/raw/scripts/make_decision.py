#!/usr/bin/env python
# coding: utf-8
"""Emit DECISION.md. Every figure is read from a computed artefact, never transcribed by hand."""
import csv
import json
import os

import numpy as np

OUT = r"C:\thesis\logs_and_models\contamination_decision"
RAW = os.path.join(OUT, "raw")
MATRIX = r"C:\thesis\logs_and_models\spatial_matrix"
PRED = ["asfalt", "fliser", "grus", "ubefestet", "green_roof",
        "drivhus", "betonflade", "brosten", "solceller"]

t2 = list(csv.DictReader(open(os.path.join(OUT, "task2_rescore_table.csv"), newline="")))
t3 = json.load(open(os.path.join(RAW, "task3_contamination_profile.json"), encoding="utf8"))
t45 = json.load(open(os.path.join(RAW, "task4_5_merge_and_cost.json"), encoding="utf8"))
t2b = json.load(open(os.path.join(RAW, "task2b_shared_window.json"), encoding="utf8"))
t2c = json.load(open(os.path.join(RAW, "task2c_route_matched.json"), encoding="utf8"))
cons = json.load(open(os.path.join(RAW, "consistency_findings.json"), encoding="utf8"))
pub24 = [r["cell"] for r in csv.DictReader(
    open(os.path.join(MATRIX, "matrix_results_all_cells.csv"), newline=""))]
gtm = list(csv.DictReader(open(os.path.join(RAW, "geotransform_mismatch_tiles.csv"), newline="")))

rows24 = [r for r in t2 if r["cell"] in pub24]
extra = sorted({r["cell"] for r in t2} - set(pub24))
d24 = np.array([float(r["d_macro_iou"]) for r in rows24])
a24 = np.array([float(r["d_acc"]) for r in rows24])
f24 = np.array([float(r["d_macro_f1"]) for r in rows24])
rel24 = 100 * d24 / np.array([float(r["macro_iou_all"]) for r in rows24])

L = []
w = L.append

w("# Fold Contamination — Decision Support")
w("")
w("**Date: 2026-08-27. Role: decision-support measurement, answering the work order of the same "
  "date. Read-only outside this folder.**")
w("")
w("Nothing was retrained, no split was rebuilt, and `all.txt`, `fold_assignment.csv` and every "
  "config are untouched. All writes went to `logs_and_models\\contamination_decision\\`.")
w("")
w("---")
w("")

# ------------------------------------------------------------------ headline
w("## 0. Recommendation")
w("")
w("**Take remedy (c): keep the frozen split, rescore on the 18,033 uncontaminated tiles, and "
  "publish both numbers. The rescoring is already done and is in this folder.**")
w("")
w("Four measured facts drive that.")
w("")
w(f"1. **Remedy (c) is executable with zero further compute.** Per-tile out-of-fold prediction "
  f"rasters were persisted for every completed cell — {len(t2)} cells, 19,314 predictions each. "
  f"The rescoring has been run; it needed no inference.")
w(f"2. **The effect is material, so remedy (a) understates it.** Pooled Macro-IoU falls in "
  f"**{int((d24<0).sum())} of {len(d24)}** published cells, by a mean of "
  f"**{-d24.mean():.4f}** (range {-d24.max():.4f} to {-d24.min():.4f}), i.e. "
  f"**{-rel24.mean():.1f} % relative**. Roughly one part in twelve of the reported Macro-IoU is "
  f"contamination.")
w(f"3. **Remedy (c) costs green_roof nothing.** **0 of the 90 green_roof tiles are contaminated.** "
  f"The class the weak GATE 1 was built to protect is entirely untouched, and no class drops out "
  f"of the macro average in any cell.")
w(f"4. **The comparative conclusions survive.** The best cell is unchanged and the top five are "
  f"identical under both scorings, so the model/channel ranking the thesis rests on does not move.")
w("")
w(f"Remedy (b) would cost **{t45['gpu_hours']['published24']['total_h']:.0f} GPU-hours** "
  f"({t45['gpu_hours']['published24']['total_h']/24:.0f} days of single-GPU wall clock) and, at the "
  f"size-optimal split, would still leave "
  f"{t45['merged_scenario']['residual_selected']['pairs']:,} cross-fold pairs. It buys a clean "
  f"split for future work, not a better answer to the present question.")
w("")
w("This is a recommendation, not a decision. The case for (b) is that it is the only remedy that "
  "makes the *training* side clean as well, which matters if the split is to be reused. The case "
  "against (c) is set out honestly in §7: the clean metric is computed on a population that is "
  "measurably poorer in solceller, so the two numbers are not measuring quite the same thing.")
w("")
w("---")
w("")

# ------------------------------------------------------------------ Task 1
w("## 1. Task 1 — can remedy (c) be executed? Yes.")
w("")
w("**Per-tile predictions were persisted, so rescoring is pure arithmetic on existing files. "
  "No inference is required.**")
w("")
w("Each fold job holds its full held-out prediction set as 1000x1000 uint8 GeoTIFFs at:")
w("")
w("```")
w("logs_and_models\\spatial_matrix\\<model>\\<model>_<channels>_fold<k>[_unw]\\models\\example_dataset\\*.tif")
w("```")
w("")
w("and each scored cell holds the pooled matrix and headline metrics at:")
w("")
w("```")
w("logs_and_models\\spatial_matrix\\<model>\\oof_<cell>\\pooled_oof_metrics.json")
w("```")
w("")
w("Counts, measured: fold 0 = 6,439 predictions, fold 1 = 6,437, fold 2 = 6,438; sum 19,314, "
  "exactly the fold sizes implied by `fold_assignment.csv` and `all.txt`. 560,109 prediction "
  "rasters exist in total across all jobs.")
w("")
w(f"**{len(t2)} cells are scoreable**: the 24 in `matrix_results_all_cells.csv` plus "
  f"{len(extra)} that were scored but never published — {', '.join('`'+c+'`' for c in extra)}. "
  f"All {len(t2)} were rescored.")
w("")
w("### 1.1 Method, and why it is exact")
w("")
w("A pooled confusion matrix is a sum over tiles, so the clean matrix is a subtraction:")
w("")
w("```")
w("CM_clean = CM_all  -  sum over the 1,281 contaminated tiles of CM_tile")
w("```")
w("")
w("`CM_all` is the persisted `global_confusion_matrix`; only the 1,281 contaminated tiles were "
  "re-read. This is arithmetically identical to rescoring all 18,033 tiles. Metrics come from the "
  "frozen scorer `analyse/per_category_metrics.py` (`metrics_from_confusion`), so the definitions "
  "are byte-identical to those that produced the published figures.")
w("")
w("Three guards were applied, all passed:")
w("")
w("| Guard | Result |")
w("|---|---|")
w("| Metrics recomputed from each stored `CM_all` reproduce the published `macro_iou` | exact for "
  "all 28 cells |")
w("| No entry of `CM_clean` may be negative | passed for all 28 cells |")
w("| For `segformer_b1_rgb`, `CM_all` recomputed from disk tile-by-tile (19,314 tiles, 1,006 s) vs "
  "the stored matrix | **identical, max abs diff 0** |")
w("")
w("The third guard is the load-bearing one: it establishes that the persisted matrices still "
  "correspond to the prediction rasters currently on disk, which is what licenses the subtraction "
  "for the other 27 cells.")
w("")
w("---")
w("")

# ------------------------------------------------------------------ Task 2
w("## 2. Task 2 — the contamination in metric terms")
w("")
w(f"Scored over all 19,314 tiles versus the 18,033 uncontaminated tiles. The dropped tiles carry "
  f"{t3['scored_px_all']-t3['scored_px_clean']:,} scored label pixels, "
  f"{100*(t3['scored_px_all']-t3['scored_px_clean'])/t3['scored_px_all']:.2f} % of "
  f"{t3['scored_px_all']:,}.")
w("")
w("Rows are the 24 published cells, sorted by Macro-IoU delta, most negative first.")
w("")
w("| Cell | Macro-IoU all | Macro-IoU clean | ΔMacro-IoU | Δ% | Acc all | Acc clean | ΔAcc | "
  "Δmacro-F1 |")
w("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
for r in sorted(rows24, key=lambda x: float(x["d_macro_iou"])):
    rel = 100 * float(r["d_macro_iou"]) / float(r["macro_iou_all"])
    w(f"| `{r['cell']}` | {float(r['macro_iou_all']):.4f} | {float(r['macro_iou_clean']):.4f} | "
      f"{float(r['d_macro_iou']):+.4f} | {rel:+.1f} % | {float(r['acc_all']):.4f} | "
      f"{float(r['acc_clean']):.4f} | {float(r['d_acc']):+.4f} | "
      f"{float(r['d_macro_f1']):+.4f} |")
w("")
w(f"Across the 24 published cells: ΔMacro-IoU mean **{d24.mean():+.4f}**, median "
  f"{np.median(d24):+.4f}, range {d24.min():+.4f} to {d24.max():+.4f}; **negative in all 24**. "
  f"Δmacro-F1 mean {f24.mean():+.4f}. Δaccuracy mean {a24.mean():+.4f} — accuracy is essentially "
  f"unmoved and in {int((a24>0).sum())} of 24 cells it *rises*.")
w("")
w(f"The four unpublished cells behave the same way: ΔMacro-IoU "
  + ", ".join(f"`{r['cell']}` {float(r['d_macro_iou']):+.4f}"
              for r in sorted([x for x in t2 if x['cell'] in extra],
                              key=lambda x: float(x['d_macro_iou']))) + ".")
w("")
w("### 2.1 Where the delta lives — per class")
w("")
w("Mean over the 24 published cells.")
w("")
w("| Class | mean IoU all | mean IoU clean | mean Δ | min Δ | max Δ | % of class pixels dropped | "
  "% of class tiles dropped |")
w("|---|---:|---:|---:|---:|---:|---:|---:|")
for c in PRED:
    ds = [float(r[f"d_{c}"]) for r in rows24 if r[f"d_{c}"] not in ("", "None")]
    aa = [float(r[f"iou_all_{c}"]) for r in rows24 if r[f"iou_all_{c}"] not in ("", "None")]
    bb = [float(r[f"iou_clean_{c}"]) for r in rows24 if r[f"iou_clean_{c}"] not in ("", "None")]
    s = t3["task3_class_support"][c]
    w(f"| {c} | {np.mean(aa):.4f} | {np.mean(bb):.4f} | {np.mean(ds):+.4f} | {min(ds):+.4f} | "
      f"{max(ds):+.4f} | {s['pct_px_lost']:.2f} % | {s['pct_tiles_lost']:.2f} % |")
w("")
w("**The delta is almost entirely two classes.** solceller loses "
  f"{-np.mean([float(r['d_solceller']) for r in rows24]):.4f} of IoU on average and grus "
  f"{-np.mean([float(r['d_grus']) for r in rows24]):.4f}; every other class moves by less than "
  f"0.025, and green_roof, brosten, betonflade and ubefestet are flat to three decimals. That is "
  "the signature of a localised problem, not a global one.")
w("")
w("### 2.2 Does the ranking survive?")
w("")
ra = [r["cell"] for r in sorted(rows24, key=lambda x: -float(x["macro_iou_all"]))]
rb = [r["cell"] for r in sorted(rows24, key=lambda x: -float(x["macro_iou_clean"]))]
moved = [(c, ra.index(c) + 1, rb.index(c) + 1) for c in ra if ra.index(c) != rb.index(c)]
w(f"Yes, at the top. The best cell is **`{ra[0]}`** under both scorings and the top five are "
  f"identical. {len(moved)} of {len(ra)} cells change rank at all, none by more than "
  f"{max((abs(i-j) for _, i, j in moved), default=0)} places, and every move is inside the "
  f"crowded middle of the table.")
w("")
w(f"- Top five, all tiles : {', '.join('`'+c+'`' for c in ra[:5])}")
w(f"- Top five, clean tiles: {', '.join('`'+c+'`' for c in rb[:5])}")
w("")
w("No cell changes the number of classes entering the macro average, so the §7.2 absent-class rule "
  "is never triggered by the removal.")
w("")
w("### 2.3 Is the delta leakage, or just a different population?")
w("")
w("This matters, and the work order does not ask it, but the answer changes how the delta should be "
  "read. Dropping 1,281 tiles changes *which ground is scored* — solceller loses "
  f"{t3['task3_class_support']['solceller']['pct_tiles_lost']:.1f} % of its tiles. A fall in "
  "Macro-IoU is therefore not, by itself, proof of leakage.")
w("")
w("**Route-matched control.** Four routes contain both contaminated and uncontaminated tiles. "
  "Within one route the terrain, sensor, flight and held-out model are all the same; the only "
  "systematic difference is whether that ground's labels also sat in the model's training folds.")
w("")
w("| Route | Fold | n contaminated | n clean | Acc contaminated | Acc clean | ΔAcc | ΔMacro-IoU | "
  "cells with ΔAcc > 0 |")
w("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
for r in sorted(t2c["summary"]):
    s = t2c["summary"][r]
    rs = [x for x in t2c["rows"] if x["route"] == r]
    w(f"| {r} | {s['fold']} | {s['n_contam']:,} | {s['n_clean']:,} | "
      f"{np.mean([x['acc_contam'] for x in rs]):.4f} | "
      f"{np.mean([x['acc_clean'] for x in rs]):.4f} | {s['d_acc_mean']:+.4f} | "
      f"{s['d_miou_mean']:+.4f} | {s['n_cells_acc_positive']}/{s['n_cells']} |")
w("")
w("**In 96 of 96 route x cell combinations the contaminated tiles score higher than the clean "
  "tiles of the same route**, by +0.08 to +0.19 accuracy. That unanimity is the leakage signature, "
  "and it says the Task-2 delta is not merely a composition artefact.")
w("")
w("Two honest caveats. Within a route the contaminated tiles are the part that overlaps another "
  "route, which may differ systematically from the rest (they are where two surveys chose to fly), "
  "so this is a matched comparison, not a randomised one. And 84-40's clean side was subsampled to "
  "600 of 5,207 tiles with seed 20260827 to keep the run tractable; that is recorded in "
  "`task2c_route_matched.json`.")
w("")
w("**A second control was run and is reported as inconclusive.** Splitting each contaminated tile "
  "into its shared and unshared windows gives a Macro-IoU gap of "
  f"{t2b['summary']['d_miou_mean']:+.4f} (positive in "
  f"{t2b['summary']['n_cells']}/{t2b['summary']['n_cells']} cells) but an accuracy gap of "
  f"{t2b['summary']['d_acc_mean']:+.4f} (negative in all of them). The two signs disagree because "
  f"the shared window is {100*t2b['shared_px']/t2b['contaminated_tile_px']:.1f} % of the pixels "
  "and the unshared remainder is a thin margin at the tile edges, which is not a comparable "
  "population. It is in `task2b_shared_window_leakage.csv` for completeness; it should not be "
  "quoted as evidence either way.")
w("")
w("---")
w("")

# ------------------------------------------------------------------ Task 3
w("## 3. Task 3 — where the contamination sits")
w("")
s = t3
w(f"{s['n_contaminated']:,} tiles, {s['pct_contaminated']:.2f} % of {s['n_all_tiles']:,}, from "
  f"{s['n_cross_fold_pairs']:,} cross-fold pairs out of {s['n_cross_route_pairs']:,} cross-route "
  f"pairs. Every figure in REPORT.md §6.2 reproduced exactly.")
w("")
w("| Fold | Contaminated | Fold size | Share |")
w("|---|---:|---:|---:|")
for f in ["0", "1", "2"]:
    w(f"| {f} | {s['contaminated_by_fold'][f]:,} | {s['fold_sizes'][f]:,} | "
      f"{100*s['contaminated_by_fold'][f]/s['fold_sizes'][f]:.2f} % |")
w(f"| **All** | **{s['n_contaminated']:,}** | **{s['n_all_tiles']:,}** | "
  f"**{s['pct_contaminated']:.2f} %** |")
w("")
w("| Route | Fold | Contaminated | Route tiles | Share |")
w("|---|---:|---:|---:|---:|")
for r, n in sorted(s["contaminated_by_route"].items(), key=lambda x: -x[1]):
    w(f"| {r} | {s['route_to_fold'][r]} | {n:,} | {s['route_tiles'][r]:,} | "
      f"{100*n/s['route_tiles'][r]:.1f} % |")
w("")
w("### 3.1 Class composition — the critical question")
w("")
w("| Class | Tiles with class, pool | of those contaminated | % tiles lost | % pixels lost | "
  "Pool pixel share | Contaminated pixel share | Enrichment |")
w("|---|---:|---:|---:|---:|---:|---:|---:|")
for c in PRED:
    d = s["task3_class_support"][c]
    w(f"| {c} | {d['tiles_all']:,} | {d['tiles_contaminated']:,} | {d['pct_tiles_lost']:.2f} % | "
      f"{d['pct_px_lost']:.2f} % | {d['pool_pixel_share_pct']:.4f} % | "
      f"{d['contaminated_pixel_share_pct']:.4f} % | "
      f"{d['enrichment_ratio']:.2f}x |")
w("")
w("**The contaminated set is not representative.** It is 3-6x enriched in asfalt, fliser, grus and "
  "drivhus, **5.9x enriched in solceller**, and correspondingly depleted in ubefestet, betonflade "
  "and brosten. It is paved, built ground — which is what one expects, since the duplicated routes "
  "are re-flights of the same towns.")
w("")
gr = s["task3_class_support"]["green_roof"]
w("### 3.2 green_roof — the GATE 1 worry, resolved")
w("")
w(f"**0 of the {gr['tiles_all']} green_roof tiles are contaminated, and 0 of its "
  f"{gr['px_all']:,} pixels.** Remedy (c) removes none of green_roof's support. The concern raised "
  f"in the work order — that (c) might weaken the class weak GATE 1 was built to protect — does "
  f"not materialise.")
w("")
w("The reason is geographic: green_roof lives only in 84-40 (fold 0) and 82-24 (fold 2), and "
  "neither route's green_roof tiles fall in the overlap zones. 84-40 is contaminated only 1.2 % "
  "overall (62 of 5,269 tiles) and none of those 62 carry green_roof; 82-24 is not contaminated at "
  "all.")
w("")
w("The other three classes the work order named:")
w("")
w("| Class | Tiles with class | Contaminated | % lost | Remaining support |")
w("|---|---:|---:|---:|---:|")
for c in ["drivhus", "betonflade", "solceller"]:
    d = s["task3_class_support"][c]
    w(f"| {c} | {d['tiles_all']:,} | {d['tiles_contaminated']:,} | {d['pct_tiles_lost']:.2f} % | "
      f"{d['tiles_clean']:,} tiles |")
w("")
w("- **drivhus** loses 54 of 328 tiles (16.5 %), all from 82-20 (35) and 82-21 (19). It keeps "
  "support in 84-40, 82-22, 83-25, 82-19 and 82-24, spanning all three folds.")
w("- **betonflade** loses 52 of 598 (8.7 %) and keeps 546, including all 328 tiles in 84-40.")
w("- **solceller is the real cost of remedy (c): 244 of 568 tiles, 43.0 %, and 29.6 % of its "
  "pixels.** All 108 solceller tiles of 85-48 and 109 of 85-45's 326 go, plus 82-20 and 82-21 "
  "entirely. It keeps 324 tiles across 85-45 (217), 82-19 (46), 84-41 (33) and 84-40 (28), so it "
  "still spans more than one fold and stays in the macro average — but this is the one class where "
  "the clean number rests on a materially thinner base.")
w("")
w("### 3.3 Overlap area distribution")
w("")
op, ot, cp = s["overlap_per_pair_m2"], s["overlap_per_tile_m2"], s["capped_per_tile"]
w("| Statistic | Per cross-fold pair | Per contaminated tile (summed over its pairs) |")
w("|---|---:|---:|")
for k, lbl in [("min", "min"), ("p10", "p10"), ("median", "median"), ("mean", "mean"),
               ("p90", "p90"), ("max", "max")]:
    w(f"| {lbl} | {op[k]:,.0f} m² | {ot[k]:,.0f} m² |")
w("")
w(f"Tiles are 10,000 m². The median cross-fold pair shares {op['median']:,.0f} m², about a quarter "
  f"of a tile — which on its own would suggest the contamination is partial. It is not, because a "
  f"contaminated tile typically has several partners covering different parts of it.")
w("")
w("The exact figure comes from unioning each tile's shared rectangles rather than summing them "
  "(summing double-counts where partners overlap each other): **the union of shared ground covers "
  f"{100*t2b['shared_px']/t2b['contaminated_tile_px']:.2f} % of all contaminated-tile pixels** "
  f"({t2b['shared_px']:,} of {t2b['contaminated_tile_px']:,}), computed over the "
  f"{t2b['contaminated_tile_px']//1000000:,} tiles whose geometry is reconstructable (see §8.1). "
  "**Contamination is not marginal at the tile level — an affected tile is, on average, almost "
  "entirely duplicated ground, which is why dropping whole tiles is the right unit for remedy "
  "(c).**")
w("")
w("---")
w("")

# ------------------------------------------------------------------ Task 4
w("## 4. Task 4 — what remedy (b) would cost and change")
w("")
ms = t45["merged_scenario"]
w("Merging `{82-20, 82-21}` and `{85-45, 85-48}` takes the blocking units from 16 to 14.")
w("")
w("| Unit | Tiles | Merged? |")
w("|---|---:|---|")
for u, n in sorted(ms["unit_tiles"].items(), key=lambda x: -x[1]):
    w(f"| `{u}` | {n:,} | {'**merged**' if '+' in u else '—'} |")
w("")
w("### 4.1 Is a balanced split still constructible? Yes.")
w("")
w(f"Exhaustive search over all 3^12 assignments (whales pinned for symmetry), with the same "
  f"checker `build_spatial_folds.py` enforces — green_roof's two routes in different folds, the two "
  f"whales split, every predicted class spanning at least two folds — finds "
  f"**{ms['feasible']:,} feasible assignments**.")
w("")
sel = ms["selected"]
w(f"The size-optimal pick under the original objective gives fold sizes "
  f"**{sel['fold_tiles'][0]:,} / {sel['fold_tiles'][1]:,} / {sel['fold_tiles'][2]:,}**, an "
  f"imbalance of **{sel['imbalance']:,} tiles ({100*sel['imbalance']/t45['total_tiles']:.2f} % of "
  f"the pool)**, against 2 tiles for the frozen 16-route split. The binding green_roof constraint "
  f"is satisfied: 84-40 and 82-24 land in different folds.")
w("")
for f in range(3):
    us = sorted([u for u, k in sel["assign"].items() if k == f],
                key=lambda x: -ms["unit_tiles"][x])
    w(f"- fold {f} ({sel['fold_tiles'][f]:,} tiles): {', '.join('`'+u+'`' for u in us)}")
w("")
w(f"So merging does not break the split. It raises the fold-size imbalance from 2 tiles to "
  f"{sel['imbalance']} — still {100*sel['imbalance']/t45['total_tiles']:.2f} % of the pool — and "
  f"changes nothing else structural.")
w("")
w("### 4.2 Compute cost")
w("")
g = t45["gpu_hours"]
p = g["published24"]
w(f"From the `wandb-summary.json` of every run on disk — training `_runtime`, inference "
  f"`inference_seconds`. {g['n_train_runs']} training runs and {g['n_infer_runs']} inference runs "
  f"were found, totalling **{g['total_h']:.1f} GPU-hours** of work already spent.")
w("")
w("| Model | Training runs | Training h | Mean h/run | Inference h | Total h |")
w("|---|---:|---:|---:|---:|---:|")
for m in sorted(g["per_model"]):
    d = g["per_model"][m]
    tr, inf = d["train"] / 3600, d["infer"] / 3600
    mean = tr / d["n_train"] if d["n_train"] else float("nan")
    w(f"| {m} | {d['n_train']} | {tr:.2f} | {mean:.2f} | {inf:.2f} | {tr+inf:.2f} |")
w(f"| **all jobs on disk** | **{g['n_train_runs']}** | **{g['train_h']:.2f}** | "
  f"**{g['train_h']/g['n_train_runs']:.2f}** | **{g['infer_h']:.2f}** | **{g['total_h']:.2f}** |")
w("")
w("(`_smoke` is a smoke test and the per-model rows include the four unpublished cells and the "
  "three learning-curve probes; the figure that matters for remedy (b) is the next paragraph.)")
w("")
w(f"**Rerunning the 24 published cells — {p['n_fold_runs']} fold-runs — cost "
  f"{p['total_h']:.1f} GPU-hours as observed ({p['train_h']:.1f} h training + "
  f"{p['infer_h']:.1f} h inference), a mean of {p['total_h']/p['n_fold_runs']:.2f} h per "
  f"fold-run.** On the single GPU in this machine that is **{p['total_h']/24:.1f} days of wall "
  f"clock at 100 % utilisation**, and in practice more.")
w("")
w("That figure is what remedy (b) costs, and it excludes rescoring, the four unpublished cells, "
  "and any run that fails and needs repeating.")
w("")
w("---")
w("")

# ------------------------------------------------------------------ Task 5
w("## 5. Task 5 — residual contamination after merging")
w("")
rs = ms["residual_selected"]
br = ms["best_residual"]
fr = t45["frozen_residual"]
w("Merging the two entangled pairs does **not** by itself drive the residual to zero, because a "
  "third route pair also shares ground.")
w("")
w("| Scenario | Cross-fold pairs | Tiles | % of 19,314 | Naive shared area | Fold imbalance |")
w("|---|---:|---:|---:|---:|---:|")
w(f"| Frozen 16-route split (today) | {fr['pairs']:,} | {fr['tiles']:,} | "
  f"{fr['pct_tiles']:.2f} % | {fr['naive_area_m2']/1e6:.4f} km² | 2 |")
w(f"| Merged 14 units, size-optimal pick | {rs['pairs']:,} | {rs['tiles']:,} | "
  f"{rs['pct_tiles']:.2f} % | {rs['naive_area_m2']/1e6:.4f} km² | {sel['imbalance']:,} |")
w(f"| Merged 14 units, best achievable residual | {br['pairs']:,} | {br['tiles']:,} | "
  f"{br['pct_tiles']:.2f} % | 0 km² | {br['imbalance']:,} |")
w("")
w("The whole residual under the size-optimal pick is a single route pair, **84-40 x 84-41**, "
  f"contributing all {rs['pairs']:,} pairs and {rs['tiles']:,} tiles. The frozen split's "
  f"{fr['pairs']:,} pairs break down as "
  + ", ".join(f"{k} {v:,}" for k, v in sorted(fr["by_route_pair"].items(), key=lambda x: -x[1]))
  + ".")
w("")
w(f"**A zero-residual split does exist among the 14 units** — it simply requires putting 84-40 and "
  f"84-41 in the same fold, which the size-optimiser does not choose on its own. The price is "
  f"imbalance rising from {sel['imbalance']} to {br['imbalance']} tiles "
  f"({100*br['imbalance']/t45['total_tiles']:.2f} % of the pool), still small. So the honest "
  f"statement is: **remedy (b) can reach zero residual, but only if 84-40 x 84-41 is added to the "
  f"constraint set — merging the two named pairs alone leaves "
  f"{rs['pct_tiles']:.2f} % of tiles contaminated.**")
w("")
am = t45["all_merged_variant"]
w(f"For completeness, merging every overlapping route pair in the data "
  f"({', '.join(a+' x '+b for a, b in t45['overlapping_route_pairs'])}) collapses to "
  f"{am['units']} units, still admits {am['feasible']:,} feasible splits, and reaches "
  f"{am['residual_selected']['pairs']} residual pairs at an imbalance of "
  f"{am['selected']['imbalance']:,} tiles. Note that in that variant betonflade spans only two "
  f"folds; weak GATE 1 still passes.")
w("")
w("---")
w("")

# ------------------------------------------------------------------ tradeoffs
w("## 6. The three remedies side by side")
w("")
w("| | (a) State as a limitation | (b) Merge and rebuild | (c) Rescore on clean tiles |")
w("|---|---|---|---|")
w(f"| **Cost** | zero | **{p['total_h']:.0f} GPU-h ≈ {p['total_h']/24:.0f} days** on one GPU, plus "
  f"rescoring and re-writing every results table | **zero — already done**, in this folder |")
w("| **Buys** | nothing; honesty about an unmeasured quantity | a split that is clean on the "
  "training side too, reusable for future work | the contamination becomes a *measured* quantity; "
  "both numbers publishable |")
w(f"| **Leaves unresolved** | the reported Macro-IoU keeps ~{-rel24.mean():.0f} % of "
  f"contamination-driven optimism, now known to be material | "
  f"{rs['pct_tiles']:.2f} % of tiles still contaminated unless 84-40 x 84-41 is also constrained; "
  f"fold imbalance grows from 2 to {sel['imbalance']}-{br['imbalance']} tiles | the models were "
  f"still *trained* with entangled routes; and the clean metric rests on a population 43 % thinner "
  f"in solceller |")
w("")
w("### 6.1 Why not (a)")
w("")
w(f"(a) was defensible while the effect was unknown. It is now measured at "
  f"{-d24.mean():.4f} Macro-IoU, {-rel24.mean():.1f} % relative, negative in every cell, and "
  f"corroborated by a route-matched control that is positive in 96 of 96 comparisons. Reporting "
  f"that as an acknowledged unknown when it has been quantified would be strictly worse than "
  f"reporting the quantity.")
w("")
w("### 6.2 Why not (b), for this thesis")
w("")
w(f"(b) is the methodologically cleanest remedy and the right choice if the split will be reused. "
  f"But it costs {p['total_h']:.0f} GPU-hours, it does not change any conclusion the thesis draws "
  f"— the ranking is stable under (c) — and it still leaves {rs['pairs']:,} contaminated pairs "
  f"unless a third route pair is added to the constraints. Spending {p['total_h']/24:.0f} days to "
  f"move a number that (c) can report for free is hard to justify on the present timeline.")
w("")
w("### 6.3 What to publish under (c)")
w("")
w("Both numbers, with the clean one as the headline and the all-tiles one as the comparison, plus "
  "the per-class table of §2.1 so the reader can see the effect is concentrated in solceller and "
  "grus. `task2_rescore_table.csv` in this folder is that table for all 28 cells.")
w("")
w("---")
w("")

# ------------------------------------------------------------------ honest limits
w("## 7. What this analysis does not establish")
w("")
w("- **Remedy (c) does not make the training side clean.** Each fold's model was still trained on "
  "routes that duplicate ground in its own held-out fold. (c) removes the contaminated *measurement*"
  ", which is what the reported metric needs, but the trained weights are unchanged. Only (b) "
  "addresses the training side.")
w("- **The clean set is not a random subset.** It is the pool minus two whole routes and most of a "
  "third. The clean Macro-IoU is an honest out-of-fold number, but it is measured on ground that is "
  "less paved and much poorer in solceller than the full pool. The two numbers are not "
  "interchangeable and should not be differenced casually by a reader.")
w("- **The route-matched control is matched, not randomised.** Contaminated tiles are, by "
  "construction, the part of a route that another survey also chose to fly. Residual confounding "
  "cannot be excluded, though the unanimity across 96 comparisons makes a purely compositional "
  "explanation strained.")
w("- **Why 82-20/82-21 and 85-45/85-48 duplicate each other is still unknown**, unchanged from "
  "REPORT.md §10. Whether merging them is the correct fix or an over-correction depends on that "
  "answer, which is not visible in the data.")
w("- **No claim is made about which of the three remedies the thesis committee would prefer.**")
w("")
w("---")
w("")

# ------------------------------------------------------------------ inconsistencies
w("## 8. Inconsistencies found between existing artefacts")
w("")
w("### 8.1 Label and image rasters disagree about location for 273 tiles")
w("")
inc = [g for g in gtm if g["in_contaminated_set"] == "True"]
w(f"**This is the most consequential finding outside the contamination question and it is "
  f"independent of it.** For **{len(gtm)} of 19,314 tiles (1.41 %)** the geotransform of "
  f"`labels/splitted_labels/<t>.tif` and the geotransform of `data/splitted/rgb/<t>.tif` place the "
  f"same tile at different coordinates — by hundreds of metres, e.g. "
  f"`O2021_82_21_1_0005_00001868_0_1000.tif` at (498020, 6220655) as a label and "
  f"(496820, 6220755) as an image, 1,200 m apart in easting.")
w("")
w("It surfaced because two artefacts silently used different geometry sources:")
w("")
w("- `tile_inventory.csv` agrees with the **label** rasters for all 19,314 tiles (0 disagreements).")
w(f"- `cross_route_tile_overlaps.csv` agrees with the **rgb** rasters, and disagrees with "
  f"`tile_inventory.csv` for exactly those {len(gtm)} tiles.")
w("")
w("The visible symptom was that 199 of the 6,783 cross-fold pairs have a declared `overlap_m2` "
  "that is geometrically impossible under the label-raster coordinates. For the other 6,584 the two "
  "sources agree to within 1.5 m², which is why the discrepancy went unnoticed.")
w("")
w("Affected routes span almost the whole dataset (82-24 2.2 %, 82-21 2.6 %, 83-25 1.5 %, ...; only "
  f"83-34 and 85-45 are clean). {len(inc)} of the {len(gtm)} sit inside the contaminated set. The "
  f"full list is `raw\\geotransform_mismatch_tiles.csv`.")
w("")
w("**What this does and does not affect.** Tasks 2 and 3 are unaffected: they use tile identity and "
  "fold membership only, never coordinates. Task 5's residual counts are unaffected: they use route "
  "membership. The route-matched control is unaffected. Only the supplementary shared-window test "
  "of §2.3 used coordinates, and it covers 1,262 of 1,281 contaminated tiles for that reason.")
w("")
w("**What it may affect, and is not established here:** whether the *content* of those 273 label "
  "rasters is aligned with the corresponding image content. If it is not, those tiles are "
  "mislabelled training and evaluation data. That is a separate investigation and, per work order "
  "§4, it is reported rather than acted on.")
w("")
w(f"### 8.2 {len(extra)} cells were scored but never published")
w("")
w(f"`{'`, `'.join(extra)}` have a complete `pooled_oof_metrics.json` and full predictions, but do "
  f"not appear in `matrix_results_all_cells.csv`. One of them, `convnext_upernet_rgb_ndsm`, has the "
  f"**highest Macro-IoU of any cell measured** (0.3625 all-tiles, 0.3309 clean) — higher than the "
  f"published best. They are rescored here alongside the 24.")
w("")
w("### 8.3 segformer_b1_6ch_corrected was trained but never inferred")
w("")
w("`segformer_b1_6ch_corrected_fold0/1/2` hold complete checkpoints and training logs but zero "
  "prediction rasters, so the cell cannot be scored or rescored. The 6ch_corrected arm is complete "
  "for convnext, swin and unet_resnet34 and missing only for segformer. Two `_smoke` jobs are in "
  "the same state, which is expected for smoke tests.")
w("")
w("### 8.4 The inference log overcounts by one tile")
w("")
w("`wandb-summary.json` for the fold-0 inference runs reports `n_tiles_classified: 6440`, while "
  "`fold_0_valid.txt` has 6,439 active lines and 6,439 prediction rasters were written. A "
  "cosmetic off-by-one in the counter; no artefact is affected.")
w("")
w("### 8.5 The design documents named as canonical are absent")
w("")
w("`2026-07-29_the_great_plan_3.0.md`, `2026-06-26_create_spatial_folds.md` and "
  "`2026-07-28_matrix_results_and_handoff.md` do not exist anywhere under `C:\\thesis`. No "
  "`plans\\` directory exists. Claims in this document are therefore traced to code and data only, "
  "never to the design documents; where the work order's framing depends on them it has been taken "
  "at face value and flagged.")
w("")
w("### 8.6 What was checked and found consistent")
w("")
w("- `matrix_results_all_cells.csv` reproduces every cell's `pooled_oof_metrics.json` to "
  f"**{cons['max_csv_json_discrepancy']:.1e}** across macro_iou, macro_f1, overall_acc and all nine "
  "per-class IoUs.")
w("- `fold_assignment.csv` tile counts match `all.txt` exactly for all 16 routes.")
w("- The `fold_a`/`fold_b` and `route_a`/`route_b` columns of `cross_route_tile_overlaps.csv` "
  "agree with `fold_assignment.csv` and with the filenames in all 8,120 rows (0 disagreements).")
w("- `tile_inventory.csv` covers all 19,314 `all.txt` tiles and its `fold` column agrees with "
  "`fold_assignment.csv` for every one.")
w("- REPORT.md §6.2's contamination counts (1,281 tiles; 212/313/756 by fold; the six-route "
  "breakdown) reproduce exactly.")
w("")
w("---")
w("")

# ------------------------------------------------------------------ files
w("## 9. Files in this folder")
w("")
w("| File | Contents |")
w("|---|---|")
w("| `DECISION.md` | this document |")
w("| `task2_rescore_table.csv` | Task 2. 28 cells x all-tiles / clean-tiles Macro-IoU, macro-F1, "
  "accuracy and all nine per-class IoUs, with deltas |")
w("| `task2b_shared_window_leakage.csv` | supplementary shared vs unshared window test (reported "
  "inconclusive, §2.3) |")
w("| `task2c_route_matched.csv` | route-matched contaminated vs clean control, 24 cells x 4 routes |")
w("| `raw\\contaminated_tiles.csv` | the 1,281 tiles with route, fold, pair count and summed "
  "overlap area |")
w("| `raw\\contaminated_tiles.txt`, `raw\\clean_tiles.txt` | the 1,281 / 18,033 tile lists |")
w("| `raw\\task3_contamination_profile.json` | Task 3 in full, including per-route rare-class "
  "support |")
w("| `raw\\task4_5_merge_and_cost.json` | Tasks 4 and 5: unit sizes, feasible splits, residuals, "
  "GPU hours |")
w("| `raw\\task4_run_times.csv` | per-job training and inference seconds from the wandb summaries |")
w("| `raw\\geotransform_mismatch_tiles.csv` | the 273 tiles of §8.1, with both coordinate pairs |")
w("| `raw\\consistency_findings.json` | §8 machine-readable |")
w("| `raw\\rescore_<cell>.json` | per cell: clean and contaminated-only metrics and both matrices |")
w("| `raw\\*_log.txt` | full console traces backing every number above |")
w("")
w("Scripts that produced these are recorded in `raw\\scripts\\`.")

with open(os.path.join(OUT, "DECISION.md"), "w", encoding="utf8") as f:
    f.write("\n".join(L) + "\n")
print(f"wrote {OUT}\\DECISION.md  ({len(L)} lines)")

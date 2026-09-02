# Fold Contamination — Decision Support

**Date: 2026-08-27. Role: decision-support measurement, answering the work order of the same date. Read-only outside this folder.**

Nothing was retrained, no split was rebuilt, and `all.txt`, `fold_assignment.csv` and every config are untouched. All writes went to `logs_and_models\contamination_decision\`.

---

## 0. Recommendation

**Take remedy (c): keep the frozen split, rescore on the 18,033 uncontaminated tiles, and publish both numbers. The rescoring is already done and is in this folder.**

Four measured facts drive that.

1. **Remedy (c) is executable with zero further compute.** Per-tile out-of-fold prediction rasters were persisted for every completed cell — 28 cells, 19,314 predictions each. The rescoring has been run; it needed no inference.
2. **The effect is material, so remedy (a) understates it.** Pooled Macro-IoU falls in **24 of 24** published cells, by a mean of **0.0238** (range 0.0171 to 0.0310), i.e. **8.2 % relative**. Roughly one part in twelve of the reported Macro-IoU is contamination.
3. **Remedy (c) costs green_roof nothing.** **0 of the 90 green_roof tiles are contaminated.** The class the weak GATE 1 was built to protect is entirely untouched, and no class drops out of the macro average in any cell.
4. **The comparative conclusions survive.** The best cell is unchanged and the top five are identical under both scorings, so the model/channel ranking the thesis rests on does not move.

Remedy (b) would cost **687 GPU-hours** (29 days of single-GPU wall clock) and, at the size-optimal split, would still leave 478 cross-fold pairs. It buys a clean split for future work, not a better answer to the present question.

This is a recommendation, not a decision. The case for (b) is that it is the only remedy that makes the *training* side clean as well, which matters if the split is to be reused. The case against (c) is set out honestly in §7: the clean metric is computed on a population that is measurably poorer in solceller, so the two numbers are not measuring quite the same thing.

---

## 1. Task 1 — can remedy (c) be executed? Yes.

**Per-tile predictions were persisted, so rescoring is pure arithmetic on existing files. No inference is required.**

Each fold job holds its full held-out prediction set as 1000x1000 uint8 GeoTIFFs at:

```
logs_and_models\spatial_matrix\<model>\<model>_<channels>_fold<k>[_unw]\models\example_dataset\*.tif
```

and each scored cell holds the pooled matrix and headline metrics at:

```
logs_and_models\spatial_matrix\<model>\oof_<cell>\pooled_oof_metrics.json
```

Counts, measured: fold 0 = 6,439 predictions, fold 1 = 6,437, fold 2 = 6,438; sum 19,314, exactly the fold sizes implied by `fold_assignment.csv` and `all.txt`. 560,109 prediction rasters exist in total across all jobs.

**28 cells are scoreable**: the 24 in `matrix_results_all_cells.csv` plus 4 that were scored but never published — `convnext_upernet_6ch_corrected`, `convnext_upernet_rgb_ndsm`, `swin_upernet_6ch_corrected`, `unet_resnet34_6ch_corrected`. All 28 were rescored.

### 1.1 Method, and why it is exact

A pooled confusion matrix is a sum over tiles, so the clean matrix is a subtraction:

```
CM_clean = CM_all  -  sum over the 1,281 contaminated tiles of CM_tile
```

`CM_all` is the persisted `global_confusion_matrix`; only the 1,281 contaminated tiles were re-read. This is arithmetically identical to rescoring all 18,033 tiles. Metrics come from the frozen scorer `analyse/per_category_metrics.py` (`metrics_from_confusion`), so the definitions are byte-identical to those that produced the published figures.

Three guards were applied, all passed:

| Guard | Result |
|---|---|
| Metrics recomputed from each stored `CM_all` reproduce the published `macro_iou` | exact for all 28 cells |
| No entry of `CM_clean` may be negative | passed for all 28 cells |
| For `segformer_b1_rgb`, `CM_all` recomputed from disk tile-by-tile (19,314 tiles, 1,006 s) vs the stored matrix | **identical, max abs diff 0** |

The third guard is the load-bearing one: it establishes that the persisted matrices still correspond to the prediction rasters currently on disk, which is what licenses the subtraction for the other 27 cells.

---

## 2. Task 2 — the contamination in metric terms

Scored over all 19,314 tiles versus the 18,033 uncontaminated tiles. The dropped tiles carry 610,523,718 scored label pixels, 5.01 % of 12,194,633,781.

Rows are the 24 published cells, sorted by Macro-IoU delta, most negative first.

| Cell | Macro-IoU all | Macro-IoU clean | ΔMacro-IoU | Δ% | Acc all | Acc clean | ΔAcc | Δmacro-F1 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `convnext_upernet_10ch` | 0.3447 | 0.3137 | -0.0310 | -9.0 % | 0.9374 | 0.9378 | +0.0004 | -0.0361 |
| `convnext_upernet_rgb` | 0.3586 | 0.3287 | -0.0300 | -8.4 % | 0.9336 | 0.9341 | +0.0005 | -0.0341 |
| `convnext_upernet_rgb_unw` | 0.3336 | 0.3038 | -0.0298 | -8.9 % | 0.9305 | 0.9307 | +0.0002 | -0.0339 |
| `convnext_upernet_10ch_unw` | 0.3307 | 0.3010 | -0.0297 | -9.0 % | 0.9358 | 0.9367 | +0.0008 | -0.0342 |
| `convnext_upernet_6ch` | 0.3374 | 0.3095 | -0.0279 | -8.3 % | 0.9275 | 0.9281 | +0.0005 | -0.0334 |
| `swin_upernet_rgb` | 0.2982 | 0.2712 | -0.0270 | -9.1 % | 0.9175 | 0.9186 | +0.0011 | -0.0286 |
| `segformer_b1_6ch` | 0.2687 | 0.2422 | -0.0265 | -9.9 % | 0.9149 | 0.9175 | +0.0025 | -0.0287 |
| `convnext_upernet_6ch_unw` | 0.3208 | 0.2946 | -0.0261 | -8.2 % | 0.9273 | 0.9276 | +0.0002 | -0.0304 |
| `unet_resnet34_6ch_unw` | 0.2431 | 0.2188 | -0.0243 | -10.0 % | 0.9027 | 0.9047 | +0.0019 | -0.0253 |
| `unet_resnet34_rgb_unw` | 0.2593 | 0.2355 | -0.0239 | -9.2 % | 0.9019 | 0.9036 | +0.0017 | -0.0245 |
| `segformer_b1_rgb_unw` | 0.2751 | 0.2515 | -0.0236 | -8.6 % | 0.9151 | 0.9177 | +0.0025 | -0.0237 |
| `swin_upernet_10ch` | 0.3134 | 0.2903 | -0.0232 | -7.4 % | 0.9299 | 0.9313 | +0.0014 | -0.0248 |
| `unet_resnet34_6ch` | 0.2477 | 0.2246 | -0.0231 | -9.3 % | 0.8977 | 0.9005 | +0.0028 | -0.0243 |
| `segformer_b1_rgb` | 0.2976 | 0.2750 | -0.0226 | -7.6 % | 0.9213 | 0.9248 | +0.0035 | -0.0232 |
| `segformer_b1_6ch_unw` | 0.2564 | 0.2338 | -0.0226 | -8.8 % | 0.9178 | 0.9212 | +0.0034 | -0.0242 |
| `unet_resnet34_rgb` | 0.2695 | 0.2470 | -0.0225 | -8.3 % | 0.8973 | 0.8996 | +0.0023 | -0.0231 |
| `swin_upernet_6ch_unw` | 0.2970 | 0.2760 | -0.0210 | -7.1 % | 0.9272 | 0.9292 | +0.0020 | -0.0219 |
| `swin_upernet_rgb_unw` | 0.3183 | 0.2974 | -0.0209 | -6.6 % | 0.9269 | 0.9283 | +0.0015 | -0.0220 |
| `unet_resnet34_10ch_unw` | 0.2423 | 0.2214 | -0.0209 | -8.6 % | 0.9118 | 0.9153 | +0.0035 | -0.0222 |
| `swin_upernet_6ch` | 0.2956 | 0.2749 | -0.0207 | -7.0 % | 0.9235 | 0.9249 | +0.0014 | -0.0227 |
| `segformer_b1_10ch` | 0.2924 | 0.2720 | -0.0204 | -7.0 % | 0.9269 | 0.9297 | +0.0028 | -0.0209 |
| `swin_upernet_10ch_unw` | 0.3013 | 0.2812 | -0.0201 | -6.7 % | 0.9268 | 0.9284 | +0.0016 | -0.0204 |
| `unet_resnet34_10ch` | 0.2523 | 0.2346 | -0.0177 | -7.0 % | 0.9095 | 0.9131 | +0.0035 | -0.0179 |
| `segformer_b1_10ch_unw` | 0.2513 | 0.2342 | -0.0171 | -6.8 % | 0.9238 | 0.9273 | +0.0035 | -0.0212 |

Across the 24 published cells: ΔMacro-IoU mean **-0.0238**, median -0.0231, range -0.0310 to -0.0171; **negative in all 24**. Δmacro-F1 mean -0.0259. Δaccuracy mean +0.0019 — accuracy is essentially unmoved and in 24 of 24 cells it *rises*.

The four unpublished cells behave the same way: ΔMacro-IoU `convnext_upernet_6ch_corrected` -0.0383, `unet_resnet34_6ch_corrected` -0.0344, `convnext_upernet_rgb_ndsm` -0.0317, `swin_upernet_6ch_corrected` -0.0252.

### 2.1 Where the delta lives — per class

Mean over the 24 published cells.

| Class | mean IoU all | mean IoU clean | mean Δ | min Δ | max Δ | % of class pixels dropped | % of class tiles dropped |
|---|---:|---:|---:|---:|---:|---:|---:|
| asfalt | 0.5115 | 0.4893 | -0.0222 | -0.0349 | -0.0078 | 14.25 % | 11.25 % |
| fliser | 0.1743 | 0.1524 | -0.0218 | -0.0503 | -0.0064 | 14.55 % | 11.36 % |
| grus | 0.1951 | 0.1482 | -0.0469 | -0.0967 | -0.0167 | 18.91 % | 14.23 % |
| ubefestet | 0.9505 | 0.9513 | +0.0008 | -0.0000 | +0.0026 | 3.77 % | 6.22 % |
| green_roof | 0.0029 | 0.0029 | +0.0000 | +0.0000 | +0.0001 | 0.00 % | 0.00 % |
| drivhus | 0.0759 | 0.0625 | -0.0134 | -0.0653 | +0.0039 | 17.51 % | 16.46 % |
| betonflade | 0.0511 | 0.0511 | -0.0000 | -0.0025 | +0.0026 | 1.40 % | 8.70 % |
| brosten | 0.0298 | 0.0298 | +0.0000 | -0.0002 | +0.0004 | 0.07 % | 1.66 % |
| solceller | 0.6359 | 0.5248 | -0.1111 | -0.1568 | -0.0568 | 29.58 % | 42.96 % |

**The delta is almost entirely two classes.** solceller loses 0.1111 of IoU on average and grus 0.0469; every other class moves by less than 0.025, and green_roof, brosten, betonflade and ubefestet are flat to three decimals. That is the signature of a localised problem, not a global one.

### 2.2 Does the ranking survive?

Yes, at the top. The best cell is **`convnext_upernet_rgb`** under both scorings and the top five are identical. 11 of 24 cells change rank at all, none by more than 4 places, and every move is inside the crowded middle of the table.

- Top five, all tiles : `convnext_upernet_rgb`, `convnext_upernet_10ch`, `convnext_upernet_6ch`, `convnext_upernet_rgb_unw`, `convnext_upernet_10ch_unw`
- Top five, clean tiles: `convnext_upernet_rgb`, `convnext_upernet_10ch`, `convnext_upernet_6ch`, `convnext_upernet_rgb_unw`, `convnext_upernet_10ch_unw`

No cell changes the number of classes entering the macro average, so the §7.2 absent-class rule is never triggered by the removal.

### 2.3 Is the delta leakage, or just a different population?

This matters, and the work order does not ask it, but the answer changes how the delta should be read. Dropping 1,281 tiles changes *which ground is scored* — solceller loses 43.0 % of its tiles. A fall in Macro-IoU is therefore not, by itself, proof of leakage.

**Route-matched control.** Four routes contain both contaminated and uncontaminated tiles. Within one route the terrain, sensor, flight and held-out model are all the same; the only systematic difference is whether that ground's labels also sat in the model's training folds.

| Route | Fold | n contaminated | n clean | Acc contaminated | Acc clean | ΔAcc | ΔMacro-IoU | cells with ΔAcc > 0 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 82-20 | 2 | 522 | 86 | 0.8252 | 0.7437 | +0.0816 | +0.0078 | 24/24 |
| 84-40 | 0 | 62 | 600 | 0.9833 | 0.7939 | +0.1894 | +0.4080 | 24/24 |
| 84-41 | 2 | 61 | 282 | 0.9908 | 0.9148 | +0.0760 | +0.5985 | 24/24 |
| 85-45 | 2 | 173 | 228 | 0.9669 | 0.8764 | +0.0905 | +0.1549 | 24/24 |

**In 96 of 96 route x cell combinations the contaminated tiles score higher than the clean tiles of the same route**, by +0.08 to +0.19 accuracy. That unanimity is the leakage signature, and it says the Task-2 delta is not merely a composition artefact.

Two honest caveats. Within a route the contaminated tiles are the part that overlaps another route, which may differ systematically from the rest (they are where two surveys chose to fly), so this is a matched comparison, not a randomised one. And 84-40's clean side was subsampled to 600 of 5,207 tiles with seed 20260827 to keep the run tractable; that is recorded in `task2c_route_matched.json`.

**A second control was run and is reported as inconclusive.** Splitting each contaminated tile into its shared and unshared windows gives a Macro-IoU gap of +0.1135 (positive in 24/24 cells) but an accuracy gap of -0.0373 (negative in all of them). The two signs disagree because the shared window is 92.6 % of the pixels and the unshared remainder is a thin margin at the tile edges, which is not a comparable population. It is in `task2b_shared_window_leakage.csv` for completeness; it should not be quoted as evidence either way.

---

## 3. Task 3 — where the contamination sits

1,281 tiles, 6.63 % of 19,314, from 6,783 cross-fold pairs out of 8,120 cross-route pairs. Every figure in REPORT.md §6.2 reproduced exactly.

| Fold | Contaminated | Fold size | Share |
|---|---:|---:|---:|
| 0 | 212 | 6,439 | 3.29 % |
| 1 | 313 | 6,437 | 4.86 % |
| 2 | 756 | 6,438 | 11.74 % |
| **All** | **1,281** | **19,314** | **6.63 %** |

| Route | Fold | Contaminated | Route tiles | Share |
|---|---:|---:|---:|---:|
| 82-20 | 2 | 522 | 608 | 85.9 % |
| 82-21 | 1 | 313 | 313 | 100.0 % |
| 85-45 | 2 | 173 | 401 | 43.1 % |
| 85-48 | 0 | 150 | 150 | 100.0 % |
| 84-40 | 0 | 62 | 5,269 | 1.2 % |
| 84-41 | 2 | 61 | 343 | 17.8 % |

### 3.1 Class composition — the critical question

| Class | Tiles with class, pool | of those contaminated | % tiles lost | % pixels lost | Pool pixel share | Contaminated pixel share | Enrichment |
|---|---:|---:|---:|---:|---:|---:|---:|
| asfalt | 5,919 | 666 | 11.25 % | 14.25 % | 6.7141 % | 19.1106 % | 2.85x |
| fliser | 3,934 | 447 | 11.36 % | 14.55 % | 1.9017 % | 5.5270 % | 2.91x |
| grus | 3,936 | 560 | 14.23 % | 18.91 % | 1.6951 % | 6.4014 % | 3.78x |
| ubefestet | 17,626 | 1,096 | 6.22 % | 3.77 % | 87.4736 % | 65.8849 % | 0.75x |
| green_roof | 90 | 0 | 0.00 % | 0.00 % | 0.0117 % | 0.0000 % | 0.00x |
| drivhus | 328 | 54 | 16.46 % | 17.51 % | 0.0044 % | 0.0152 % | 3.50x |
| betonflade | 598 | 52 | 8.70 % | 1.40 % | 0.7320 % | 0.2053 % | 0.28x |
| brosten | 1,928 | 32 | 1.66 % | 0.07 % | 0.9867 % | 0.0147 % | 0.01x |
| solceller | 568 | 244 | 42.96 % | 29.58 % | 0.4808 % | 2.8408 % | 5.91x |

**The contaminated set is not representative.** It is 3-6x enriched in asfalt, fliser, grus and drivhus, **5.9x enriched in solceller**, and correspondingly depleted in ubefestet, betonflade and brosten. It is paved, built ground — which is what one expects, since the duplicated routes are re-flights of the same towns.

### 3.2 green_roof — the GATE 1 worry, resolved

**0 of the 90 green_roof tiles are contaminated, and 0 of its 1,430,413 pixels.** Remedy (c) removes none of green_roof's support. The concern raised in the work order — that (c) might weaken the class weak GATE 1 was built to protect — does not materialise.

The reason is geographic: green_roof lives only in 84-40 (fold 0) and 82-24 (fold 2), and neither route's green_roof tiles fall in the overlap zones. 84-40 is contaminated only 1.2 % overall (62 of 5,269 tiles) and none of those 62 carry green_roof; 82-24 is not contaminated at all.

The other three classes the work order named:

| Class | Tiles with class | Contaminated | % lost | Remaining support |
|---|---:|---:|---:|---:|
| drivhus | 328 | 54 | 16.46 % | 274 tiles |
| betonflade | 598 | 52 | 8.70 % | 546 tiles |
| solceller | 568 | 244 | 42.96 % | 324 tiles |

- **drivhus** loses 54 of 328 tiles (16.5 %), all from 82-20 (35) and 82-21 (19). It keeps support in 84-40, 82-22, 83-25, 82-19 and 82-24, spanning all three folds.
- **betonflade** loses 52 of 598 (8.7 %) and keeps 546, including all 328 tiles in 84-40.
- **solceller is the real cost of remedy (c): 244 of 568 tiles, 43.0 %, and 29.6 % of its pixels.** All 108 solceller tiles of 85-48 and 109 of 85-45's 326 go, plus 82-20 and 82-21 entirely. It keeps 324 tiles across 85-45 (217), 82-19 (46), 84-41 (33) and 84-40 (28), so it still spans more than one fold and stays in the macro average — but this is the one class where the clean number rests on a materially thinner base.

### 3.3 Overlap area distribution

| Statistic | Per cross-fold pair | Per contaminated tile (summed over its pairs) |
|---|---:|---:|
| min | 9 m² | 1,488 m² |
| p10 | 456 m² | 10,000 m² |
| median | 2,370 m² | 20,700 m² |
| mean | 2,707 m² | 28,671 m² |
| p90 | 5,456 m² | 57,000 m² |
| max | 9,603 m² | 103,100 m² |

Tiles are 10,000 m². The median cross-fold pair shares 2,370 m², about a quarter of a tile — which on its own would suggest the contamination is partial. It is not, because a contaminated tile typically has several partners covering different parts of it.

The exact figure comes from unioning each tile's shared rectangles rather than summing them (summing double-counts where partners overlap each other): **the union of shared ground covers 92.58 % of all contaminated-tile pixels** (1,168,348,100 of 1,262,000,000), computed over the 1,262 tiles whose geometry is reconstructable (see §8.1). **Contamination is not marginal at the tile level — an affected tile is, on average, almost entirely duplicated ground, which is why dropping whole tiles is the right unit for remedy (c).**

---

## 4. Task 4 — what remedy (b) would cost and change

Merging `{82-20, 82-21}` and `{85-45, 85-48}` takes the blocking units from 16 to 14.

| Unit | Tiles | Merged? |
|---|---:|---|
| `84-40` | 5,269 | — |
| `83-25` | 3,630 | — |
| `82-24` | 1,529 | — |
| `82-11` | 1,441 | — |
| `82-22` | 1,360 | — |
| `83-26` | 1,228 | — |
| `82-13` | 1,043 | — |
| `83-31` | 1,020 | — |
| `82-20+82-21` | 921 | **merged** |
| `82-19` | 591 | — |
| `85-45+85-48` | 551 | **merged** |
| `82-16` | 378 | — |
| `84-41` | 343 | — |
| `83-34` | 10 | — |

### 4.1 Is a balanced split still constructible? Yes.

Exhaustive search over all 3^12 assignments (whales pinned for symmetry), with the same checker `build_spatial_folds.py` enforces — green_roof's two routes in different folds, the two whales split, every predicted class spanning at least two folds — finds **349,920 feasible assignments**.

The size-optimal pick under the original objective gives fold sizes **6,421 / 6,457 / 6,436**, an imbalance of **36 tiles (0.19 % of the pool)**, against 2 tiles for the frozen 16-route split. The binding green_roof constraint is satisfied: 84-40 and 82-24 land in different folds.

- fold 0 (6,421 tiles): `84-40`, `82-19`, `85-45+85-48`, `83-34`
- fold 1 (6,457 tiles): `83-25`, `82-11`, `82-13`, `84-41`
- fold 2 (6,436 tiles): `82-24`, `82-22`, `83-26`, `83-31`, `82-20+82-21`, `82-16`

So merging does not break the split. It raises the fold-size imbalance from 2 tiles to 36 — still 0.19 % of the pool — and changes nothing else structural.

### 4.2 Compute cost

From the `wandb-summary.json` of every run on disk — training `_runtime`, inference `inference_seconds`. 90 training runs and 87 inference runs were found, totalling **829.4 GPU-hours** of work already spent.

| Model | Training runs | Training h | Mean h/run | Inference h | Total h |
|---|---:|---:|---:|---:|---:|
| _smoke | 1 | 0.67 | 0.67 | 0.00 | 0.67 |
| convnext_upernet | 24 | 221.86 | 9.24 | 6.88 | 228.74 |
| segformer_b1 | 20 | 172.39 | 8.62 | 5.26 | 177.66 |
| swin_upernet | 21 | 209.80 | 9.99 | 6.09 | 215.89 |
| unet_resnet34 | 24 | 199.61 | 8.32 | 6.82 | 206.43 |
| **all jobs on disk** | **90** | **804.32** | **8.94** | **25.06** | **829.38** |

(`_smoke` is a smoke test and the per-model rows include the four unpublished cells and the three learning-curve probes; the figure that matters for remedy (b) is the next paragraph.)

**Rerunning the 24 published cells — 72 fold-runs — cost 687.4 GPU-hours as observed (666.5 h training + 20.9 h inference), a mean of 9.55 h per fold-run.** On the single GPU in this machine that is **28.6 days of wall clock at 100 % utilisation**, and in practice more.

That figure is what remedy (b) costs, and it excludes rescoring, the four unpublished cells, and any run that fails and needs repeating.

---

## 5. Task 5 — residual contamination after merging

Merging the two entangled pairs does **not** by itself drive the residual to zero, because a third route pair also shares ground.

| Scenario | Cross-fold pairs | Tiles | % of 19,314 | Naive shared area | Fold imbalance |
|---|---:|---:|---:|---:|---:|
| Frozen 16-route split (today) | 6,783 | 1,281 | 6.63 % | 18.3640 km² | 2 |
| Merged 14 units, size-optimal pick | 478 | 123 | 0.64 % | 1.2608 km² | 36 |
| Merged 14 units, best achievable residual | 0 | 0 | 0.00 % | 0 km² | 181 |

The whole residual under the size-optimal pick is a single route pair, **84-40 x 84-41**, contributing all 478 pairs and 123 tiles. The frozen split's 6,783 pairs break down as 82-20 x 82-21 3,286, 85-45 x 85-48 3,019, 84-40 x 84-41 478.

**A zero-residual split does exist among the 14 units** — it simply requires putting 84-40 and 84-41 in the same fold, which the size-optimiser does not choose on its own. The price is imbalance rising from 36 to 181 tiles (0.94 % of the pool), still small. So the honest statement is: **remedy (b) can reach zero residual, but only if 84-40 x 84-41 is added to the constraint set — merging the two named pairs alone leaves 0.64 % of tiles contaminated.**

For completeness, merging every overlapping route pair in the data (82-16 x 82-24, 82-20 x 82-21, 84-40 x 84-41, 85-45 x 85-48) collapses to 12 units, still admits 37,908 feasible splits, and reaches 0 residual pairs at an imbalance of 181 tiles. Note that in that variant betonflade spans only two folds; weak GATE 1 still passes.

---

## 6. The three remedies side by side

| | (a) State as a limitation | (b) Merge and rebuild | (c) Rescore on clean tiles |
|---|---|---|---|
| **Cost** | zero | **687 GPU-h ≈ 29 days** on one GPU, plus rescoring and re-writing every results table | **zero — already done**, in this folder |
| **Buys** | nothing; honesty about an unmeasured quantity | a split that is clean on the training side too, reusable for future work | the contamination becomes a *measured* quantity; both numbers publishable |
| **Leaves unresolved** | the reported Macro-IoU keeps ~8 % of contamination-driven optimism, now known to be material | 0.64 % of tiles still contaminated unless 84-40 x 84-41 is also constrained; fold imbalance grows from 2 to 36-181 tiles | the models were still *trained* with entangled routes; and the clean metric rests on a population 43 % thinner in solceller |

### 6.1 Why not (a)

(a) was defensible while the effect was unknown. It is now measured at 0.0238 Macro-IoU, 8.2 % relative, negative in every cell, and corroborated by a route-matched control that is positive in 96 of 96 comparisons. Reporting that as an acknowledged unknown when it has been quantified would be strictly worse than reporting the quantity.

### 6.2 Why not (b), for this thesis

(b) is the methodologically cleanest remedy and the right choice if the split will be reused. But it costs 687 GPU-hours, it does not change any conclusion the thesis draws — the ranking is stable under (c) — and it still leaves 478 contaminated pairs unless a third route pair is added to the constraints. Spending 29 days to move a number that (c) can report for free is hard to justify on the present timeline.

### 6.3 What to publish under (c)

Both numbers, with the clean one as the headline and the all-tiles one as the comparison, plus the per-class table of §2.1 so the reader can see the effect is concentrated in solceller and grus. `task2_rescore_table.csv` in this folder is that table for all 28 cells.

---

## 7. What this analysis does not establish

- **Remedy (c) does not make the training side clean.** Each fold's model was still trained on routes that duplicate ground in its own held-out fold. (c) removes the contaminated *measurement*, which is what the reported metric needs, but the trained weights are unchanged. Only (b) addresses the training side.
- **The clean set is not a random subset.** It is the pool minus two whole routes and most of a third. The clean Macro-IoU is an honest out-of-fold number, but it is measured on ground that is less paved and much poorer in solceller than the full pool. The two numbers are not interchangeable and should not be differenced casually by a reader.
- **The route-matched control is matched, not randomised.** Contaminated tiles are, by construction, the part of a route that another survey also chose to fly. Residual confounding cannot be excluded, though the unanimity across 96 comparisons makes a purely compositional explanation strained.
- **Why 82-20/82-21 and 85-45/85-48 duplicate each other is still unknown**, unchanged from REPORT.md §10. Whether merging them is the correct fix or an over-correction depends on that answer, which is not visible in the data.
- **No claim is made about which of the three remedies the thesis committee would prefer.**

---

## 8. Inconsistencies found between existing artefacts

### 8.1 Label and image rasters disagree about location for 273 tiles

**This is the most consequential finding outside the contamination question and it is independent of it.** For **273 of 19,314 tiles (1.41 %)** the geotransform of `labels/splitted_labels/<t>.tif` and the geotransform of `data/splitted/rgb/<t>.tif` place the same tile at different coordinates — by hundreds of metres, e.g. `O2021_82_21_1_0005_00001868_0_1000.tif` at (498020, 6220655) as a label and (496820, 6220755) as an image, 1,200 m apart in easting.

It surfaced because two artefacts silently used different geometry sources:

- `tile_inventory.csv` agrees with the **label** rasters for all 19,314 tiles (0 disagreements).
- `cross_route_tile_overlaps.csv` agrees with the **rgb** rasters, and disagrees with `tile_inventory.csv` for exactly those 273 tiles.

The visible symptom was that 199 of the 6,783 cross-fold pairs have a declared `overlap_m2` that is geometrically impossible under the label-raster coordinates. For the other 6,584 the two sources agree to within 1.5 m², which is why the discrepancy went unnoticed.

Affected routes span almost the whole dataset (82-24 2.2 %, 82-21 2.6 %, 83-25 1.5 %, ...; only 83-34 and 85-45 are clean). 19 of the 273 sit inside the contaminated set. The full list is `raw\geotransform_mismatch_tiles.csv`.

**What this does and does not affect.** Tasks 2 and 3 are unaffected: they use tile identity and fold membership only, never coordinates. Task 5's residual counts are unaffected: they use route membership. The route-matched control is unaffected. Only the supplementary shared-window test of §2.3 used coordinates, and it covers 1,262 of 1,281 contaminated tiles for that reason.

**What it may affect, and is not established here:** whether the *content* of those 273 label rasters is aligned with the corresponding image content. If it is not, those tiles are mislabelled training and evaluation data. That is a separate investigation and, per work order §4, it is reported rather than acted on.

### 8.2 4 cells were scored but never published

`convnext_upernet_6ch_corrected`, `convnext_upernet_rgb_ndsm`, `swin_upernet_6ch_corrected`, `unet_resnet34_6ch_corrected` have a complete `pooled_oof_metrics.json` and full predictions, but do not appear in `matrix_results_all_cells.csv`. One of them, `convnext_upernet_rgb_ndsm`, has the **highest Macro-IoU of any cell measured** (0.3625 all-tiles, 0.3309 clean) — higher than the published best. They are rescored here alongside the 24.

### 8.3 segformer_b1_6ch_corrected was trained but never inferred

`segformer_b1_6ch_corrected_fold0/1/2` hold complete checkpoints and training logs but zero prediction rasters, so the cell cannot be scored or rescored. The 6ch_corrected arm is complete for convnext, swin and unet_resnet34 and missing only for segformer. Two `_smoke` jobs are in the same state, which is expected for smoke tests.

### 8.4 The inference log overcounts by one tile

`wandb-summary.json` for the fold-0 inference runs reports `n_tiles_classified: 6440`, while `fold_0_valid.txt` has 6,439 active lines and 6,439 prediction rasters were written. A cosmetic off-by-one in the counter; no artefact is affected.

### 8.5 The design documents named as canonical are absent

`2026-07-29_the_great_plan_3.0.md`, `2026-06-26_create_spatial_folds.md` and `2026-07-28_matrix_results_and_handoff.md` do not exist anywhere under `C:\thesis`. No `plans\` directory exists. Claims in this document are therefore traced to code and data only, never to the design documents; where the work order's framing depends on them it has been taken at face value and flagged.

### 8.6 What was checked and found consistent

- `matrix_results_all_cells.csv` reproduces every cell's `pooled_oof_metrics.json` to **0.0e+00** across macro_iou, macro_f1, overall_acc and all nine per-class IoUs.
- `fold_assignment.csv` tile counts match `all.txt` exactly for all 16 routes.
- The `fold_a`/`fold_b` and `route_a`/`route_b` columns of `cross_route_tile_overlaps.csv` agree with `fold_assignment.csv` and with the filenames in all 8,120 rows (0 disagreements).
- `tile_inventory.csv` covers all 19,314 `all.txt` tiles and its `fold` column agrees with `fold_assignment.csv` for every one.
- REPORT.md §6.2's contamination counts (1,281 tiles; 212/313/756 by fold; the six-route breakdown) reproduce exactly.

---

## 9. Files in this folder

| File | Contents |
|---|---|
| `DECISION.md` | this document |
| `task2_rescore_table.csv` | Task 2. 28 cells x all-tiles / clean-tiles Macro-IoU, macro-F1, accuracy and all nine per-class IoUs, with deltas |
| `task2b_shared_window_leakage.csv` | supplementary shared vs unshared window test (reported inconclusive, §2.3) |
| `task2c_route_matched.csv` | route-matched contaminated vs clean control, 24 cells x 4 routes |
| `raw\contaminated_tiles.csv` | the 1,281 tiles with route, fold, pair count and summed overlap area |
| `raw\contaminated_tiles.txt`, `raw\clean_tiles.txt` | the 1,281 / 18,033 tile lists |
| `raw\task3_contamination_profile.json` | Task 3 in full, including per-route rare-class support |
| `raw\task4_5_merge_and_cost.json` | Tasks 4 and 5: unit sizes, feasible splits, residuals, GPU hours |
| `raw\task4_run_times.csv` | per-job training and inference seconds from the wandb summaries |
| `raw\geotransform_mismatch_tiles.csv` | the 273 tiles of §8.1, with both coordinate pairs |
| `raw\consistency_findings.json` | §8 machine-readable |
| `raw\rescore_<cell>.json` | per cell: clean and contaminated-only metrics and both matrices |
| `raw\*_log.txt` | full console traces backing every number above |

Scripts that produced these are recorded in `raw\scripts\`.

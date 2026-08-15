# Filename Provenance and Frame-Level Overlap — Findings

**Date: 2026-08-04. Role: measurement report answering the work order
`2026-08-04_filename_provenance_and_frame_overlap.md`. Read-only investigation.**

Every number below was computed from the data on this machine. Nothing was moved, renamed, deleted or
rewritten inside `multi_channel_dataset_creation`. All writes went to this folder only. Source data:
`C:\thesis\multi_channel_dataset_creation\example_dataset`.

---

## 0. Headline

Five things, in order of how much they matter.

1. **H1 is confirmed, decisively.** A flight route is a set of heavily overlapping aerial frames.
   Consecutive frames along a line share a **median 53.1 %** of their ground footprint. Field 5 is the
   **flight line (strip) index**: adjacent field-5 groups share a median **21.6 %** of their area, and
   the offset between them runs roughly **east–west** while the offset between consecutive frames runs
   roughly **north–south**. That is textbook photogrammetric block geometry — north–south flight lines
   with forward overlap, flown alternately up and down, with sidelap between neighbouring lines.

2. **The honest coverage number is 75.45 km², not 193.14 km².** The 19,314 labelled tiles sum to
   193.14 km² of tile area but cover only **75.45 km² of distinct ground**. The redundancy factor is
   **2.56x**. Roughly three fifths of the labelled tile area is a second, third or fourth photograph of
   ground already covered.

3. **The frozen 3-fold split is not geographically airtight.** This is the one finding that touches a
   locked design decision, so per work order §6 it is reported and **not acted on**. **6,783 pairs of
   labelled tiles that sit in different folds share ground.** 1,281 tiles (6.63 % of the dataset) are
   involved. Deduplicated, fold 1 and fold 2 share **1.84 km²** (6.2 % of fold 1's ground, 7.9 % of
   fold 2's) and fold 0 and fold 2 share **0.48 km²**. Fold 0 and fold 1 share nothing.

4. **On that shared ground the labels are byte-identical — 100.00 % agreement over 23.0 million pixels
   across 40 sampled pairs.** The imagery is not identical (the same place seen from a different
   exposure, pixel agreement 0.7–9.6 %, correlation 0.21–0.86), but the ground truth is the same because
   every label raster is rasterised from the same GeoPackage onto the same grid. So the duplication is
   real leakage of *label* information, not merely of appearance.

5. **Corrections A, B, C and D in the work order are all confirmed**, and D is now quantified: **2,386
   of 19,314 tiles (12.35 %)** carry a filename offset that does not match their own geotransform.

---

## 1. How the names are built, end to end

### 1.1 The two levels

```
example_dataset/
  data/
    original_data/            <basename>_rgb.tif , <basename>_DSM.tif , ...   (delivery form)
    rgb/  cir/  DSM/  DTM/  OrtoRGB/  OrtoCIR/
                              <basename>.tif                                  PARENT FRAMES  (1,298 rgb)
    splitted/<channel>/       <basename>_<x>_<y>.tif                          TILES          (103,261 rgb)
  labels/
    large_label/              <basename>.tif                                  parent-sized labels (799)
    splitted_labels/          <basename>_<x>_<y>.tif                          tile labels    (60,123)
```

`move_data_to_separate_folders.py` drives `rename_files.py` with
`replacestring = "_" + datatype + ".tif"` and `newstring = ".tif"`
([move_data_to_separate_folders.py:39-40](multi_channel_dataset_creation/src/multi_channel_dataset_creation/move_data_to_separate_folders.py#L39-L40)),
so `<basename>_DSM.tif` becomes `DSM/<basename>.tif`. **The basename is the join key across all six
channels and the label folder.** That is exactly what
[create_all_and_valid_txt.py:59-62](multi_channel_dataset_creation/src/multi_channel_dataset_creation/create_all_and_valid_txt.py#L59-L62)
relies on: a tile enters `all.txt` only if the identically named file exists in every listed datasource
folder.

Labels are generated per *parent frame*, one label raster per frame in the folder named by
`images_that_define_areas_to_create_labels_for = example_dataset/data/OrtoRGB`
([create_dataset_example_dataset.ini:35](multi_channel_dataset_creation/configs/create_dataset_example_dataset.ini#L35)).
Measured: all 799 `large_label` basenames exist in `OrtoRGB`; only 760 of them exist in `rgb`.

### 1.2 The parent-frame name, field by field

For `O2021_82_11_1_0025_00003594.tif`:

| # | Value | Meaning | Status after this investigation |
|---|---|---|---|
| 1 | `O2021` | "Orto" + acquisition year | Established. Measured values: 2021, 2023 only |
| 2 | `82` | Flight block (81 Nordjylland … 85 Sjælland) | Established. Measured: 82, 83, 84, 85 |
| 3 | `11` | Flight route in the block; route key `82-11` | Established. Measured: **17** route keys in `data/rgb` |
| 4 | `1` | — | **Not determined. Constant `1` for all 1,298 parents**, so the data carries no information about it |
| 5 | `0025` | **Flight line / strip index within a route and year** | **Established this session** (§3) |
| 6 | `00003594` | Frame (exposure) identifier, consecutive along a line | **Confirmed** (§3): median frame-number step of 1 between consecutive frames |
| 7 | `7000` | Crop offset in **x** (easting / column) in pixels | **Confirmed empirically** (§5) |
| 8 | `5000` | Crop offset in **y** (northing / row) in pixels | **Confirmed empirically** (§5) |

Field 5 is scoped **within a route and year**, not globally: it restarts per route, and no route reuses
a field-5 value across its two years. Measured for the three two-year routes — 82-24, 84-40 and 84-41
each have **zero** shared field-5 values between 2021 and 2023.

Field 5 is not a time-ordered counter across a route. In 82-11, line `0023` carries frame 3029, `0024`
carries 2864, `0025` carries 3593–3599, `0026` carries 2614. Frame numbers are sequential *within* a
line, not across lines.

### 1.3 Where the names get messy

Three real defects, all in the naming, all found by scanning every file:

- **`_10cm` survives into the basename for 414 files across 77 distinct basenames.** Some deliveries were
  named `<basename>_10cm_<channel>.tif`, so stripping `_<channel>.tif` leaves `<basename>_10cm`. Worse, it
  is **inconsistent between channels**: all 77 appear in DSM, DTM, OrtoRGB and OrtoCIR, but only 53 appear
  in rgb and cir. For the remaining **24** frames — `O2021_82_24_1_0019_00004349_10cm` and its neighbours
  — the elevation and oblique channels carry the `_10cm` name while rgb and cir carry the plain one. Since
  the basename is the join key, those frames can never satisfy the all-datasources check. Measured effect:
  the union over the six channel folders is 1,345 basenames but only **1,294** exist in all six.
- **One corrupted rename**: `data/rgb/O2021_82_24_1_0022_00001765_cirO2021_82_24_1_0022_00001765.tif`
  — a channel name and a second copy of the basename spliced into the middle. rgb only.
- **Three `.tif.ovr` pyramid files** left loose in `data/rgb`, and one **corrupt DTM**,
  `DTM/O2021_82_21_1_0004_00002039.tif`, whose header reports a pixel size of `-5.59e+29` and whose
  strip data is truncated (`TIFFReadEncodedStrip` fails at scanline 1817). Its rgb, cir, DSM, OrtoRGB and
  OrtoCIR siblings are fine.

### 1.4 The tile name

`split.py` writes `basename + "_" + str(i) + "_" + str(j) + extension`
([split.py:214-241](multi_channel_dataset_creation/src/multi_channel_dataset_creation/split.py#L214-L241)),
`i` being the column (x) and `j` the row (y). Parent recovery is `"_".join(filename.split("_")[0:-2])`
— strip the last two underscore fields
([create_all_and_valid_txt.py:189](multi_channel_dataset_creation/src/multi_channel_dataset_creation/create_all_and_valid_txt.py#L189)).
That recovery is safe even for the `_10cm` names, because it counts from the end.

---

## 2. Task 1 — parent frame inventory

`parent_frame_inventory.csv`, 1,298 rows, one per `.tif` in `data/rgb`. All 1,298 opened successfully.

| Property | Measured |
|---|---|
| Parents in `data/rgb` | **1,298** |
| Distinct route keys | **17** (`82-11,13,16,19,20,21,22,24`, `83-25,26,31,34`, `84-40,41,42`, `85-45,48`) |
| Years | 2021, 2023 |
| Field-4 values | `1` only |
| CRS | EPSG **25832** on all 1,298 |
| Pixel size | **(0.1, −0.1)** m on all 1,298 |
| Bands / dtype | 3 / uint8 on all 1,298 |
| **Frame dimensions** | **425 distinct (w,h) pairs — frames are NOT one size** |
| Frame footprint | width 770–1,821 m (median 970), height 318–1,245 m (median 715) |
| Frame area | 0.268–2.232 km², median 0.699 km², **naive sum 933.84 km²** |

**Frame sizes vary, and this matters.** The delivered products are not uniform raw camera frames: within
a single route the number of distinct sizes runs from 1 (82-19, 82-22, 83-34, 84-42) to 107 (82-24) and
105 (84-40). Routes with a single size (exactly 11000x7000 or 17000x12000 px) look like frames clipped to
a nominal rectangle; routes with hundreds of distinct sizes look like frames clipped to an irregular area
of interest. Any statement in the thesis of the form "a frame is N by M" is false — quote the
distribution.

Per-route counts, years and strip counts are in `raw_log_step2.txt` and `raw_step1.json`. The largest
routes by frame count are 84-40 (532), 84-41 (156), 82-24 (131) and 83-25 (102).

---

## 3. Tasks 2 and 3 — the flight geometry. H1 confirmed.

### 3.1 Within a strip (task 2)

Grouping by `(route_key, year, field5)` and sorting by frame id gives 142 groups with at least two
frames and **1,153 consecutive pairs**.

| Consecutive-frame overlap | Value |
|---|---|
| Median | **53.12 %** |
| Mean | 48.51 % |
| p10 / p90 | 20.55 % / 77.83 % |
| Pairs with any overlap | 1,116 / 1,153 = **96.8 %** |
| Pairs with more than 10 % overlap | 1,088 = **94.4 %** |

The work order's own threshold — *"if the median is above roughly 10 %, H1 is confirmed"* — is cleared by
a factor of five. **Frame-level duplication is real and substantial.**

The offset bearing between consecutive frames is **~0° or ~180°**, i.e. **flight lines run north–south**.
The per-strip median bearing alternates between the two: in route 82-13, line 0024 runs at 359.4°, line
0025 at 179.9°, line 0026 at 0.6°. That is the classic back-and-forth (boustrophedon) survey pattern, and
it is independent evidence that field 5 orders the lines as flown.

Along-track spacing is 154 m (82-22) to 532 m (82-20) depending on route, which is consistent with the
per-route variation in frame height.

### 3.2 Between strips (task 3)

109 adjacent-field-5 pairs, compared as unioned strip footprints.

| Adjacent strip pairs | Value |
|---|---|
| Median overlap | **21.6 %** |
| Mean overlap | 22.1 % |
| Pairs with any overlap | **99 %** |
| Pairs with more than 10 % overlap | **92 %** |

Offset bearing histogram (30° bins): 60° → 40 pairs, 90° → 40, 120° → 7, 150° → 7, 30° → 4, 0° → 10.
**Dominantly east-ish, i.e. perpendicular to the north–south along-track direction.** This is exactly the
prediction the work order made for H1, and it is what settles field 5: it is the flight line index, and
`0024` and `0025` are *neighbouring parallel strips of the same block*.

**H2 is rejected** (field 5 is geographically coherent, not administrative). **H3 is rejected** (the
delivered products are plainly not trimmed to abut).

19 non-adjacent field-5 pairs also overlap, mean 26.2 %, max 59.7 %. Field-5 numbering is therefore
approximately but not strictly spatially ordered.

---

## 4. Task 4 — how much ground is actually covered

### 4.1 Parent frames

| | Naive sum | Unique (unioned) | Redundancy |
|---|---:|---:|---:|
| All 1,298 parents | 933.84 km² | **374.03 km²** | **2.50x** |

Per route the redundancy runs from 1.30x (82-16, 83-31) to 4.73x (85-45) and 4.60x (85-48). Full table in
`raw_log_step2.txt`.

### 4.2 The labelled tiles — the number for the chapter

19,314 tiles, each read from its own geotransform. **All 19,314 are exactly 1000 x 1000 px at 0.1 m in
EPSG 25832, i.e. exactly 1 ha each.**

| | Value |
|---|---:|
| Naive sum of tile areas | 193.14 km² |
| **Unique labelled ground** | **75.45 km²** |
| **Redundancy factor** | **2.560x** |
| Share of Denmark (~42,900 km²) | **0.176 %** (not 0.45 %) |

Per route:

| Route | Tiles | Naive km² | Unique km² | Redundancy |
|---|---:|---:|---:|---:|
| 82-11 | 1,441 | 14.41 | 8.05 | 1.79 |
| 82-13 | 1,043 | 10.43 | 6.08 | 1.72 |
| 82-16 | 378 | 3.78 | 2.33 | 1.62 |
| 82-19 | 591 | 5.91 | 2.26 | 2.62 |
| 82-20 | 608 | 6.08 | 2.49 | 2.44 |
| 82-21 | 313 | 3.13 | 1.84 | 1.70 |
| 82-22 | 1,360 | 13.60 | 2.49 | **5.47** |
| 82-24 | 1,529 | 15.29 | 5.28 | 2.90 |
| 83-25 | 3,630 | 36.30 | 13.87 | 2.62 |
| 83-26 | 1,228 | 12.28 | 7.19 | 1.71 |
| 83-31 | 1,020 | 10.20 | 6.79 | 1.50 |
| 83-34 | 10 | 0.10 | 0.07 | 1.54 |
| 84-40 | 5,269 | 52.69 | 17.35 | 3.04 |
| 84-41 | 343 | 3.43 | 1.57 | 2.18 |
| 85-45 | 401 | 4.01 | 0.75 | **5.35** |
| 85-48 | 150 | 1.50 | 0.30 | **5.07** |

Route sizes are even more uneven in ground terms than in tile counts. 84-40 is 27 % of the tiles but 23 %
of the ground; 82-22 is 7 % of the tiles but only 3.3 % of the ground.

### 4.3 Where the duplication comes from

Overlapping tile pairs within the same route, split by origin:

| Source | Pairs | Summed overlap |
|---|---:|---:|
| Same parent frame (the `split.py` edge clamp, §5) | 3,655 | 21.30 km² |
| **Different parent frames, same route (photogrammetric overlap)** | **86,981** | **246.78 km²** |

So **97 % of the within-route duplication is the flight overlap**, not the tiling. The tiling artefact is
a rounding error by comparison. This is the quantitative form of the work order's §1.2 point: the "40 px
overlap" story was never where the duplication lived.

---

## 5. Corrections A–D, all confirmed

**A — the "256x256 tiles" figure is wrong.** Measured on all 19,314 tiles in `all.txt`: **1000 x 1000 px**,
one distinct size, no exceptions. 256 is the internal GeoTIFF block size from `-co TILED=YES`. The handoff
document `2026-07-28_matrix_results_and_handoff.md` §1 needs correcting.

**B — production used `overlap = 0`, not 40.** Measured over all 1,297 parents present in
`splitted/rgb`: the y-offset step is **1000 in 8,140 of 8,140 cases**, and the x-offset step is 1000 in
11,231 cases with the remainder being the clamp residuals described below. Had `overlap = 40` been used
the step would be 960 everywhere. The Karasiak buffer-distance analogy resting on 40 px must be dropped.
The blocking argument stands on the far stronger footing measured in §3.

**C — the regex group labels were transposed.** Verified directly, not from the code: for each tile,
`origin_x_parent + name_field_7 * 0.1` was compared with the tile's own `min_x`, and
`origin_y_parent − name_field_8 * 0.1` with its `max_y`. **87.65 % match exactly.** Under the transposed
reading almost nothing would match. Field 7 is x (easting), field 8 is y (northing). Docs need fixing,
code does not — both groups are discarded.

**D — edge tiles carry misleading offsets, and it is 12.35 % of the dataset.**
**2,386 of 19,314 tiles** have a name offset that disagrees with their own geotransform. The mechanism is
now pinned exactly. In [split.py:214-232](multi_channel_dataset_creation/src/multi_channel_dataset_creation/split.py#L214-L232)
the filename is built *before* the clamp, then both `i` and `j` are reassigned to their clamped values.
`j` is refreshed from `range` on the next inner iteration, but `i` is not — it stays clamped for the rest
of that column. Consequences, both observed:

- The **y** offset in a name is never clamped, so it is always a multiple of 1000, and it is **wrong for
  the last row of every column**. Example: `O2021_82_11_1_0023_00003029_0_7000.tif` sits 60 m north of
  where its name says.
- The **x** offset is unclamped only in the first row of the last column and clamped in every row after,
  so **one crop column can appear under two different x values**. Example:
  `..._11000_0.tif` and `..._10960_1000.tif` are the same column; the file named `_11000_0` is really at
  x = 10960, a 4 m discrepancy, and no `_10960_0` exists.

**Never derive position from a tile filename. Read the geotransform.** This report did.

---

## 6. Task 5 — route-key integrity. This is the finding that matters.

### 6.1 Parent level

**983 pairs of parent frames with different route keys overlap on the ground**, across five route pairs:

| Route pair | Overlapping frame pairs | Deduplicated shared ground | Folds |
|---|---:|---:|---|
| 85-45 x 85-48 | 711 | 5.00 km² = 40.8 % of 85-45, **85.5 % of 85-48** | 2 / 0 |
| 84-41 x 84-42 | 99 | 4.84 km² = 10.4 % / 74.3 % | 2 / not in split |
| 84-40 x 84-41 | 69 | 1.17 km² = 1.0 % / 2.5 % | 0 / 2 |
| 82-16 x 82-24 | 54 | 2.00 km² = 49.4 % / 2.4 % | 2 / 2 (same) |
| 82-20 x 82-21 | 50 | 5.53 km² = 65.4 % / **59.0 %** | 2 / 1 |

**A route key is not a geographic partition.** Some routes are largely re-flights of the same ground
under a different route number, in the same year: 82-20 and 82-21 are both 2021; 85-45 and 85-48 are both
2023.

### 6.2 Tile level — the number that decides whether this is a problem

Parent overlap only matters if it reaches the labelled tiles. It does.

| | Value |
|---|---:|
| Overlapping labelled tile pairs, same route | 90,636 |
| Overlapping labelled tile pairs, **different route** | 8,120 |
| Overlapping labelled tile pairs, **different fold** | **6,783** |

Deduplicated ground shared between folds:

| Fold pair | Shared ground | As share of each fold's ground |
|---|---:|---|
| 0 x 1 | **0.0000 km²** | 0 % / 0 % — clean |
| 0 x 2 | 0.4779 km² | 1.96 % / 2.04 % |
| **1 x 2** | **1.8397 km²** | **6.15 % / 7.85 %** |

Tiles affected:

| Fold | Tiles sharing ground with another fold | Of total |
|---|---:|---:|
| 0 | 212 | 3.29 % |
| 1 | 313 | 4.86 % |
| 2 | 756 | **11.74 %** |
| **All** | **1,281** | **6.63 %** |

By route, the exposure is extremely concentrated:

| Route | Fold | Affected tiles | Share of that route |
|---|---|---:|---:|
| **82-21** | 1 | 313 / 313 | **100 %** |
| **85-48** | 0 | 150 / 150 | **100 %** |
| 82-20 | 2 | 522 / 608 | 85.9 % |
| 85-45 | 2 | 173 / 401 | 43.1 % |
| 84-41 | 2 | 61 / 343 | 17.8 % |
| 84-40 | 0 | 62 / 5,269 | 1.2 % |

**Two entire routes — 82-21 (fold 1, 313 tiles) and 85-48 (fold 0, 150 tiles) — consist wholly of tiles
whose ground is also covered by a route in a different fold.** Route 82-21's footprint is 99.76 %
contained within route 82-20's; route 85-48's is 94.37 % contained within 85-45's.

Overlap size distribution over the 6,783 cross-fold pairs: median 2,370 m² of a 10,000 m² tile, mean
2,707 m², 894 pairs sharing more than half a tile, 23 sharing more than 90 %.

### 6.3 What is actually shared — imagery versus labels

Twelve cross-fold pairs were compared pixel by pixel in their shared window, on the rgb tiles. The
imagery is **not** duplicated: identical-pixel rates of 0.7–9.6 %, mean absolute difference 4.8–34.7 DN,
correlation 0.21–0.86. These are genuinely different photographs — different exposure, different viewing
angle, different time within the sortie.

The **labels are duplicated exactly**. Forty cross-fold pairs with more than 4,000 m² of shared ground
were compared on `splitted_labels`, **23,006,800 pixels** in total:

> **Label agreement on shared ground: mean 100.00 %, median 100.00 %, minimum 100.00 %. 40 of 40 pairs
> above 95 %.**

That is the expected result and it is the point. Both label rasters are burned from the same
`example_dataset_ground_surface.gpkg` onto the same 0.1 m grid, so a given square metre of Denmark gets
the same class in every tile that contains it. **A model trained on fold 1 has therefore seen the exact
ground-truth polygons of 6.15 % of fold 2's held-out ground, under different illumination.** That is a
textbook spatial leakage channel, and it is precisely the one route-blocking was built to close.

### 6.4 Standing per work order §6

The work order says: *"If any task reveals something that would change a locked design decision, stop and
report rather than acting on it."* This is that case. **Nothing has been changed.** `fold_assignment.csv`,
`all.txt` and every config are untouched.

For calibration, the effect is bounded and reportable rather than fatal:

- Fold 0 versus fold 1 is completely clean.
- The contaminated ground is 6.15 % of fold 1 and 7.85 % of fold 2, 2 % between folds 0 and 2.
- 93.4 % of all labelled tiles are unaffected.
- The imagery is not duplicated, only the labels and the location; the model does not see the same
  pixels twice.
- The pooled out-of-fold confusion matrix counts every pixel once, so the *arithmetic* of the headline
  metric is unaffected; what is affected is the independence assumption behind it.

The cheapest honest remedies, for the author to weigh and not implemented here: (a) report the measured
contamination as a stated limitation with these numbers; (b) merge the geographically entangled route
pairs into a single blocking unit — `{82-20, 82-21}`, `{85-45, 85-48}`, and note `{84-40, 84-41}` at
1.2 % — and rebuild the split, which would cost a rerun of the matrix; or (c) keep the split and drop the
1,281 contaminated tiles from the *held-out* side when scoring, which costs no retraining at all and is
computable from `cross_route_tile_overlaps.csv`. Option (c) is the only one that fits the timeline in
Great Plan 3.0 §8 without touching the frozen runs.

---

## 7. Task 6 — cross-year geography

Three routes were flown in both 2021 and 2023. Year-collapsing the route key was designed to contain
this; here is what it actually contains.

| Route | 2021 ground | 2023 ground | Shared | % of 2021 | % of 2023 |
|---|---:|---:|---:|---:|---:|
| 82-24 | 12.00 km² | 74.91 km² | 4.24 km² | **35.3 %** | 5.7 % |
| 84-40 | 34.30 km² | 88.95 km² | 11.12 km² | **32.4 %** | 12.5 % |
| 84-41 | 10.09 km² | 36.63 km² | **0.00 km²** | 0.0 % | 0.0 % |

For 82-24 and 84-40 the design justification is now measured rather than asserted: about a third of the
2021 footprint was re-flown in 2023, and collapsing the years into one route key does keep that
same-place-different-year pair inside one fold. **For 84-41 it is vacuous** — the 2021 and 2023 flights
under that route number cover entirely disjoint ground, so year-collapsing 84-41 buys nothing and merely
makes the blocking unit larger and more heterogeneous. Worth one sentence in the method chapter.

Note the interaction with §6: 84-41 (fold 2) overlaps 84-40 (fold 0) by 0.199 km² at tile level. The
year-collapse design handled the within-route case but not the between-route case.

---

## 8. Task 7 — channel alignment

Twenty basenames present in all six channel folders, chosen with a fixed seed (20260804).

**Geometry.** 19 of 20 agree exactly across all six channels on width, height, full affine geotransform
and CRS. The one failure is **`O2021_82_21_1_0004_00002039`**, where the **DTM** reports a pixel size of
`-5.592396466345195e+29` against 0.1 in every other channel, and reading the band fails with a truncated
strip. The file is corrupt, not misaligned.

**Types.** Consistent across the sample: rgb, cir, OrtoRGB, OrtoCIR are 3-band uint8; DSM and DTM are
1-band float32.

**DSM / DTM information content — measured, not eyeballed.** The work order asked for this explicitly.
Full-frame statistics for the 19 readable samples (`dsm_dtm_value_stats.csv`):

- Value ranges are plausible physical elevations in metres, e.g. DSM −1.73 to 29.33, DTM 46.77 to 55.83,
  DSM 20.31 to 120.73.
- **Distinct-value counts are enormous: 406,566 to 4,577,257 distinct float32 values per frame**, i.e.
  between roughly 5,800 and 60,700 distinct values per million pixels.
- DSM consistently spans a wider range than DTM on the same frame (surface versus terrain), as expected,
  and DSM ≥ DTM everywhere in the samples.

**Conclusion: DSM and DTM are not low-information layers.** Whatever the F4 channel result turns out to
be, "the elevation channels are visually smooth so they must be near-constant" is not supportable — a
frame with 4.5 million distinct elevation values has not been trivially upsampled from something coarse.
The smoothness is the terrain, not the encoding. If bilinear upsampling from a coarser native grid did
occur, it did not collapse the value distribution, and testing that properly needs a spectral or
autocorrelation check rather than a distinct-value count.

---

## 9. Dataset bookkeeping, incidental but load-bearing

- **`all.txt` holds 19,318 non-blank lines: 19,314 active plus 4 commented out with a leading `#`.**
  The commented four are `#O2021_82_13_1_0024_00141735_7000_0.tif`,
  `#O2021_82_13_1_0024_00141802_8150_2000.tif`, `#O2021_82_13_1_0025_00144229_8160_1000.tif`,
  `#O2021_82_22_1_0031_00000390_8000_1000.tif`. No duplicates. This is where 19,314 comes from — worth
  knowing, because a naive line count gives 19,318 and any consumer that does not skip `#` will crash or
  silently mis-key.
- **757 parent frames** are referenced by `all.txt`, out of 1,298 in `data/rgb`. All 757 have a
  `large_label` and exist in `data/rgb`. The 541 unused parents are concentrated in 84-40 (233), 84-41
  (129), 82-24 (60), 85-45 (35), 83-34 (24) and 84-42 (17).
- **Route 84-42 exists in the imagery (17 frames, 6.51 km²) but contributes zero labelled tiles**, which
  is why the frozen split has 16 routes and the inventory has 17. It overlaps 84-41 by 4.84 km² (74 % of
  84-42). Not a problem — it is simply not in the dataset — but it explains the 16-versus-17 discrepancy
  and it should not be silently added later.
- Tiles per parent: min 1, median 18, max 127.
- `splitted/rgb` holds 103,261 tiles; `splitted_labels` holds 60,123; 56,703 basenames are in both. All
  19,314 `all.txt` tiles have both. The gap is the ~40k label-less tiles already noted in Great Plan 3.0
  §0.
- Channel tile counts differ (`splitted/rgb` 103,261, `splitted/cir` 103,181, `splitted/DSM` 106,797,
  `splitted/DTM` 106,695, `splitted/OrtoRGB` 107,031, `splitted/OrtoCIR` 106,419), which is the tile-level
  shadow of the parent-level basename mismatch in §1.3.

---

## 10. What is settled, and what is not

**Settled by measurement:**

- Field 5 is the flight line index within a route and year (§3.2).
- Field 6 is the exposure counter along a line (§3.1).
- Fields 7 and 8 are x and y crop offsets in pixels, in that order (§5, correction C).
- A route is a photogrammetric block of overlapping frames, north–south lines, 53 % forward overlap,
  22 % sidelap (§3).
- Tiles are 1000 x 1000 px, 1 ha, cut with `overlap = 0` (§5, corrections A and B).
- Unique labelled ground is 75.45 km², redundancy 2.56x (§4.2).
- Route keys are not a geographic partition, and the frozen folds share ground (§6).
- Labels on shared ground are identical to the pixel (§6.3).
- DSM and DTM carry millions of distinct values (§8).

**Not settled, honestly:**

- **Field 4 is not determined.** It is the constant `1` in all 1,298 parent frames. The data cannot
  identify it. It is most likely a version, camera or product-variant code that never varied in this
  extract, but that is an inference from constancy, not a measurement. Ask Rasmus Johansson, or leave it
  described as "constant in this dataset, meaning not established."
- **Why some routes duplicate each other's ground** (82-20/82-21, 85-45/85-48) is not determined. The
  geometry is measured; whether they are re-flights, deliveries from two contractors, or an
  administrative re-numbering is not visible in the data. This matters for §6 because it decides whether
  merging the pairs into one blocking unit is the correct fix or an over-correction.
- Whether `all.txt` is the complete training footprint still needs Rasmus's confirmation, unchanged from
  the work order §7.
- Whether the DSM/DTM upsampling in `extract_data_from_vrt.py` was applied to *these* frames is not
  established. The distinct-value counts rule out a degenerate result but do not identify the native
  resolution.

---

## 11. Deliverables in this folder

| File | Contents |
|---|---|
| `REPORT.md` | this document |
| `parent_frame_inventory.csv` | task 1. 1,298 rows: parsed name fields, dimensions, pixel size, CRS, origin, bounds, area |
| `overlap_pairs.csv` | 1,111 rows. Consecutive-frame pairs (task 2), strip pairs (task 3), cross-route parent pairs (task 5), with `overlap_m2`, `overlap_pct_a/b`, `bearing_deg` |
| `within_strip_groups.csv` | per `(route, year, field5)` group: n frames, mean/median/max overlap %, median along-track distance, median bearing, frame-number steps |
| `strip_pair_overlap.csv` | task 3 detail, every strip pair with areas, overlap, bearing, adjacency flag |
| `cross_route_tile_overlaps.csv` | **8,120 rows.** Every labelled-tile pair from different routes that shares ground, with both folds and the overlap area. Filter `fold_a != fold_b` for the 6,783 cross-fold pairs |
| `dsm_dtm_value_stats.csv` | task 7. Per sampled frame: dtype, min, max, distinct-value count, pixel count |
| `raw_step1..5.json`, `raw_log_step2..5.txt` | the raw computed values and full console traces backing every number above |

**Assumptions stated explicitly.** Footprints are treated as axis-aligned bounding boxes from the
geotransform. This is exact, not an approximation: the rotation terms `b` and `d` were checked and found
to be 0 in **all 1,298 rgb parents and all 19,314 labelled tiles**, so every raster is north-up and its
bounding box is its true footprint. Overlap is geometric ground overlap
and takes no account of nodata or black borders inside a frame, so §4's unique-area figures are an upper
bound on genuinely imaged ground and §6's overlaps are an upper bound on genuinely shared imagery. The
label comparison in §6.3 is unaffected by this, since it compared actual label rasters. Frame footprints
were read from `data/rgb` only; the other five channels were checked for agreement on a 20-frame sample
(§8), not exhaustively.

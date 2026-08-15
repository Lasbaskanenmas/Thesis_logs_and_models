# Dataset Inventory — Chapter 2 Summary Figures

**Date: 2026-08-10. Role: discovery report answering the work order
`2026-08-06_locate_dataset_inventory.md`. Read-only.**

Nothing was moved, renamed, deleted or rewritten. All writes went to
`C:\thesis\logs_and_models\dataset_inventory\` only. No new analysis code was written; every figure
below was either read from an existing artefact or produced by a single shell command, stated with
each figure.

**Provenance key used throughout:**

- **[A]** read from an existing artefact on disk, named at the point of use
- **[C]** counted directly this session, with the command given in §9
- **[G]** `gdalinfo` spot check this session

---

## 0. Headline answers

| Question | Answer | Prov |
|---|---|---|
| Parent frames (union over all six channels) | **1,345** distinct basenames | [C] |
| Parent frames in `rgb` | **1,298** | [A] |
| Tiles per channel | **103,181 – 107,031**, not equal | [C] |
| Labelled tiles in the pool | **19,314** | [A] |
| Label folder in use | `labels\splitted_labels` — 60,123 rasters, of which 19,314 are in the pool | [A][C] |
| Acquisition years | **2021 and 2023 only** — 630 and 715 frames | [C] |
| Distinct routes | **18** across all channels, **17** in `rgb`, **16** carry labelled tiles | [C] |
| Tile geometry | 1000 x 1000 px, 0.1 m, EPSG 25832 — **all six channels and the labels agree** | [G] |
| **Total volume of `C:\thesis`** | **4.834 TB** (4.397 TiB), 1,595,477 files | [C] |
| Of that, the six channels as .tif | **2.658 TB** | [C] |

**The "three to four terabyte" figure in the thesis is too low.** The true total on this machine is
**4.834 TB**. See §7 — the number depends heavily on what is being counted, and the report gives
four defensible variants so the thesis can state the one it means.

---

## 1. Per-channel counts and volumes

Counted this session with `Get-ChildItem -File` filtered to `.tif`, `Measure-Object -Sum Length`
(§9, command C1). Byte figures are exact, not rounded from a viewer. **[C]**

### 1.1 Parent frames — `example_dataset\data\<channel>\`

| Channel | .tif files | Bytes | GB (1e9) | GiB |
|---|---:|---:|---:|---:|
| rgb | 1,298 | 20,789,862,027 | 20.79 | 19.36 |
| cir | 1,295 | 19,676,464,003 | 19.68 | 18.33 |
| DSM | 1,343 | 386,316,710,344 | 386.32 | 359.79 |
| DTM | 1,343 | 382,756,173,246 | 382.76 | 356.47 |
| OrtoRGB | 1,344 | 290,764,172,476 | 290.76 | 270.80 |
| OrtoCIR | 1,344 | 288,939,969,492 | 288.94 | 269.10 |
| **Total** | **7,967** | **1,389,243,351,588** | **1,389.24** | **1,293.83** |

Non-`.tif` strays live in three of these folders: `rgb` holds 1,301 files total (3 extra `.tif.ovr`
pyramids, 31,458,423 bytes), `cir` 1,297, `OrtoRGB` 1,346. Every other folder is pure `.tif`. **[C]**

**Note the size asymmetry.** DSM and DTM are 386 GB and 383 GB against rgb's 21 GB, an **18.6x**
ratio, despite covering the same ground. They are Float32 single-band against Byte three-band, so
4 bytes per pixel against 3, and the LZW compression achieves far less on continuous elevation data
than on imagery. This is worth one sentence in Chapter 2: **the elevation channels dominate storage
while contributing, as currently normalised, almost nothing to the model** (SQ1 finding F8).

### 1.2 Tiles — `example_dataset\data\splitted\<channel>\`

| Channel | .tif files | Bytes | GB (1e9) | GiB |
|---|---:|---:|---:|---:|
| rgb | 103,261 | 238,994,748,282 | 238.99 | 222.58 |
| cir | 103,181 | 253,352,713,526 | 253.35 | 235.95 |
| DSM | 106,797 | 166,980,819,412 | 166.98 | 155.51 |
| DTM | 106,695 | 162,238,554,274 | 162.24 | 151.10 |
| OrtoRGB | 107,031 | 218,342,055,839 | 218.34 | 203.35 |
| OrtoCIR | 106,419 | 228,884,295,113 | 228.88 | 213.17 |
| **Total** | **633,384** | **1,268,793,186,446** | **1,268.79** | **1,181.66** |

`splitted\rgb` holds one extra non-`.tif` file, `splitted\OrtoRGB` one. **[C]**

### 1.3 Labels

| Folder | .tif files | .tif bytes | All files | All bytes |
|---|---:|---:|---:|---:|
| `labels\splitted_labels` | **60,123** | **606,859,863** | 60,124 | 606,860,310 |
| `labels\large_label` (top level only) | 799 | 620,151,145 | 5,593 | 707,653,370 |
| `labels\large_label` (recursive, incl. `reclass\`) | — | — | 9,588 | ~1.60 GB |

**The folder used by the current pool is `labels\splitted_labels`.** All 19,314 tiles in `all.txt`
have a label there — verified in a previous session and recorded in
`logs_and_models\filename_provenance\REPORT.md` §9. **[A]** The other 40,809 rasters in that folder
are tiles that never entered the pool.

`large_label` carries heavy sidecar baggage: 5,593 files at top level for only 799 rasters, the rest
being `.tfw`, `.tif.ovr`, `.tif.aux.xml` and `.tif.vat.cpg`. **[C]**

---

## 2. Do the channels have equal counts? No.

**Parent level.** Union across the six channels is **1,345** basenames; the intersection is
**1,294**. **[C]**

| Channel | Has | Missing from union | Of which: `_10cm` partner present | Genuinely absent |
|---|---:|---:|---:|---:|
| rgb | 1,298 | 47 | 21 | **26** |
| cir | 1,295 | 50 | 20 | **30** |
| DSM | 1,343 | 2 | 0 | 2 |
| DTM | 1,343 | 2 | 0 | 2 |
| OrtoRGB | 1,344 | 1 | 0 | 1 |
| OrtoCIR | 1,344 | 1 | 0 | 1 |

**The two known causes do not account for the whole discrepancy.** The work order named a `_10cm`
basename mismatch and a corrupt DTM. Measured:

1. **The `_10cm` mismatch is real and explains 21 of rgb's 47 and 20 of cir's 50.** These are frames
   where the four auxiliary channels carry `<basename>_10cm` while rgb and cir carry the plain
   `<basename>`, or the reverse. Mechanism documented in `REPORT.md` §1.3. **[A]**

2. **The corrupt DTM explains none of it.** `DTM\O2021_82_21_1_0004_00002039.tif` **exists** and is
   counted; it is unreadable, not absent. It is a data-integrity defect, not a count discrepancy.
   The work order conflates the two.

3. **A third cause, not previously recorded: an entire route is missing from rgb and cir.**
   **Route 82-12 has 10 frames** (`O2021_82_12_1_0003_00002571` through `..._0004_00002474`) present
   in DSM, DTM, OrtoRGB and OrtoCIR and **absent from rgb and cir entirely**. **[C]**

4. **The remaining 16 rgb / 20 cir absences are scattered single frames** across routes 82-21, 82-22,
   82-24, 83-34, 84-40 and 84-41, each present in all four auxiliary channels and missing from the
   nadir ones. Full list in §10.

5. **Two one-off name defects.** `O2021_82_24_1_0022_00001765_cirO2021_82_24_1_0022_00001765` exists
   in rgb only — a corrupted rename, documented in `REPORT.md` §1.3. **[A]**
   `O2023_82_24_1_0013_00000580` is present in rgb, cir, OrtoRGB and OrtoCIR but absent from DSM and
   DTM. **[C]**

**Tile level.** Counts range 103,181 to 107,031. The ordering follows the parent counts, so most of
the spread is inherited. It is not purely inherited, because `create_patches.py` calls
`splitdst(..., stop_on_error=False)`, which logs and skips a frame whose split throws rather than
aborting. **No log of skipped frames was found on disk**, so the split-failure component cannot be
separated from the inherited component. Stated as a gap rather than estimated.

**None of this affects the labelled pool.** `create_all_and_valid_txt.py` admits a tile only if the
identically named file exists in every datasource folder, so all 19,314 pool tiles are complete
across all six channels by construction.

---

## 3. Acquisition years

Counted over the union of basenames across all six channels, parsed from the filename year field. **[C]**

| Year | Frames |
|---|---:|
| 2021 | 630 |
| 2023 | 715 |
| **Total** | **1,345** |

**Confirmed: 2021 and 2023 are the only two years.** Restricted to `rgb` alone the split is 583 /
715 — the 47 frames rgb lacks are all 2021. **[C]** This also matches
`parent_frame_inventory.csv`, which records exactly two distinct year values. **[A]**

---

## 4. Routes

Counted over the union of all six channels. **[C]**

| Route | Frames | Years | In `rgb`? | Labelled tiles? |
|---|---:|---|---|---|
| 82-11 | 23 | 2021 | yes | yes (1,441) |
| **82-12** | **10** | 2021 | **no** | **no** |
| 82-13 | 34 | 2021 | yes | yes (1,043) |
| 82-16 | 16 | 2021 | yes | yes (378) |
| 82-19 | 24 | 2021 | yes | yes (591) |
| 82-20 | 8 | 2021 | yes | yes (608) |
| 82-21 | 12 | 2021 | yes | yes (313) |
| 82-22 | 60 | 2021 | yes | yes (1,360) |
| 82-24 | 158 | 2021+2023 | yes | yes (1,529) |
| 83-25 | 102 | 2021 | yes | yes (3,630) |
| 83-26 | 27 | 2021 | yes | yes (1,228) |
| 83-31 | 19 | 2021 | yes | yes (1,020) |
| 83-34 | 27 | 2021 | yes | yes (10) |
| 84-40 | 533 | 2021+2023 | yes | yes (5,269) |
| 84-41 | 158 | 2021+2023 | yes | yes (158) |
| **84-42** | **17** | 2021 | yes | **no** |
| 85-45 | 80 | 2023 | yes | yes (401) |
| 85-48 | 37 | 2023 | yes | yes (150) |

Labelled tile counts from `route_class_audit.csv`. **[A]**

**Three different route counts, all correct, for three different populations:**

- **18** distinct routes across all six channel folders **[C]**
- **17** in `rgb`, which is what `parent_frame_inventory.csv` reports **[A]**
- **16** carrying labelled tiles, which is what `fold_assignment.csv` blocks on **[A]**

**The work order's §4.5 statement is confirmed but incomplete.** 84-42 is indeed an imagery route
with no labelled tiles. It is not the only route outside the labelled pool — **82-12 is a second
one, and it is missing from `rgb` and `cir` altogether**, which is why it never appeared in the
rgb-only inventory. Neither route is in the frozen split, so neither affects any result; both should
be excluded explicitly rather than silently if the footprint is ever recomputed.

---

## 5. Geometry per channel

`gdalinfo` on three tiles per channel, the same three basenames each time, all drawn from `all.txt`
so they are representative of the pool: `O2021_82_11_1_0023_00003029_0_0`,
`O2021_84_40_1_0049_00072941_2000_3000`, `O2023_85_45_1_0025_00001586_3000_0`. **[G]**

| Channel | Size | Pixel size | CRS | Bands | Type | Three agree? |
|---|---|---|---|---:|---|---|
| rgb | 1000 x 1000 | 0.1, −0.1 | EPSG 25832 | 3 | Byte | yes |
| cir | 1000 x 1000 | 0.1, −0.1 | EPSG 25832 | 3 | Byte | yes |
| DSM | 1000 x 1000 | 0.1, −0.1 | EPSG 25832 | 1 | Float32 | yes |
| DTM | 1000 x 1000 | 0.1, −0.1 | EPSG 25832 | 1 | Float32 | yes |
| OrtoRGB | 1000 x 1000 | 0.1, −0.1 | EPSG 25832 | 3 | Byte | yes |
| OrtoCIR | 1000 x 1000 | 0.1, −0.1 | EPSG 25832 | 3 | Byte | yes |
| **label** (`splitted_labels`) | 1000 x 1000 | 0.1, −0.1 | EPSG 25832 | 1 | Byte | yes |

**Confirmed: all six channels and the label raster agree with rgb.** Each tile is 100 m x 100 m =
1 ha on the ground.

Two corroborations from existing artefacts rather than this spot check:

- All **19,314** pool tiles were verified 1000 x 1000 at 0.1 m in EPSG 25832 — an exhaustive check,
  not a sample (`REPORT.md` §4.2, §5 correction A). **[A]**
- A 20-basename cross-channel alignment check found **19 of 20 agreeing exactly** on width, height,
  full affine transform and CRS, with the single failure being the corrupt
  `DTM\O2021_82_21_1_0004_00002039.tif` (`REPORT.md` §8). **[A]**

**Parent frames are a different matter and must not be described as one size.** They range from
7,700 x 5,720 to 18,210 x 12,010 px across **425 distinct (width, height) pairs**
(`parent_frame_inventory.csv`, 1,298 rows). **[A]** Only the tiles are uniform.

---

## 6. What the numbers roll up to

| Population | Files | Bytes | TB (1e12) | TiB |
|---|---:|---:|---:|---:|
| Six channels, parents, .tif | 7,967 | 1,389,243,351,588 | 1.389 | 1.264 |
| Six channels, tiles, .tif | 633,384 | 1,268,793,186,446 | 1.269 | 1.154 |
| Labels, both folders, .tif | 60,922 | 1,227,011,008 | 0.001 | 0.001 |
| **The 14 folders above** | **702,273** | **2,659,263,549,042** | **2.659** | **2.419** |

---

## 7. Total volume, and the "three to four TB" claim

| Scope | Files | Bytes | TB (1e12) | TiB |
|---|---:|---:|---:|---:|
| The 14 inventoried folders, .tif only | 702,273 | 2,659,263,549,042 | **2.659** | 2.419 |
| `example_dataset\` entire tree | 822,599 | 2,854,986,668,523 | **2.855** | 2.597 |
| `logs_and_models\` entire tree | 679,187 | 1,970,897,148,909 | **1.971** | 1.793 |
| `envs\` | 92,971 | 8,077,054,534 | 0.008 | 0.007 |
| `exploratory_data_analysis\` | 58 | 25,827,627 | 0.000 | 0.000 |
| `ML_sdfi_fastai2\` | 523 | 4,687,814 | 0.000 | 0.000 |
| **`C:\thesis` entire tree** | **1,595,477** | **4,834,069,124,138** | **4.834** | **4.397** |

**Stated plainly: the thesis's three-to-four-terabyte figure is too low for the project as a whole,
and too high for the imagery the models actually consume.** Neither reading makes it correct. Pick
the scope deliberately:

- **2.66 TB** — the six channels plus labels as GeoTIFFs. This is the honest "the dataset is N TB"
  number for a Data chapter.
- **2.86 TB** — everything under `example_dataset\`, including 108 GB of building masks, 66 GB of
  5 cm resampled tiles and various `old_*` staging folders that are not part of the pool.
- **4.83 TB** — the whole working tree, dominated by the **1.97 TB of model outputs** in
  `logs_and_models\` (the 72-run matrix and its 463,536 out-of-fold predictions).

The 196 GB gap between the first two lines is accounted for: `buildings\splitted_buildings` 108.35 GB,
`splitted\5cm5cmsampled` 64.40 GB, `splitted\5cm10cmresampled` 1.23 GB, `labels\splitted_labels_5cm`
9.12 GB, `data\original_data` 8.80 GB, `data\original_data_backup` 2.30 GB, plus `large_label`
sidecars and the sub-gigabyte `old_*` folders. **[C]**

---

## 8. Artefacts checked, and what they did and did not hold

Per §2 of the work order, discovery came before counting.

| Artefact | Held what was needed? |
|---|---|
| `logs_and_models\filename_provenance\parent_frame_inventory.csv` | **Yes, partially.** 1,298 rgb rows with year, block, route, field-5, geometry. Gave the rgb route and year breakdown with no recomputation. Covers **rgb only**, which is why it reports 17 routes and missed 82-12 |
| `logs_and_models\filename_provenance\REPORT.md` | **Yes.** §1 the naming scheme and the `_10cm` defect, §4 tile geometry and areas, §8 the channel alignment check, §9 the `all.txt` bookkeeping and the 84-42 route |
| `exploratory_data_analysis\results\tables\tile_inventory.csv` + provenance | Per-tile composition, 19,314 rows. No per-channel file counts or volumes |
| `exploratory_data_analysis\results\tables\route_composition.csv` | Per-route class shares, fold, sealed fraction, centroid. No frame counts |
| `class_pixel_audit.json`, `route_class_audit.csv` | Class distribution and per-route tile counts. No storage figures |
| `SQ1_findings.md` | Narrative synthesis. No storage figures |
| `multi_channel_dataset_creation` — `image_stats_calculation.py` | **Never produced a file.** The script only `print`s to stdout; it opens no output handle. No stats output exists anywhere to find |
| `example_dataset\data\*.txt` manifests | Tile lists, not counts by channel. `error_labels.txt` is a diagnostic report, not an inventory |
| `logs_and_models\**` grep for `OrtoRGB`, `total size`, `GB`, `TB` | 117 hits, **all** either `filename_provenance` output from a prior session or wandb run logs recording the `datatypes` config list. **No prior session ever recorded per-channel counts or volumes** |
| `C:\thesis\plans\` | **Does not exist** on this machine |

So §1's four "Missing" rows genuinely had to be counted. Everything marked Known or Partially known
was read, not recomputed.

---

## 9. Commands used

- **C1, counts and bytes per folder:**
  `Get-ChildItem -LiteralPath <folder> -File | Where-Object { $_.Extension -eq '.tif' } | Measure-Object -Property Length -Sum`
  run per folder, alongside an unfiltered `Measure-Object` for the all-files column.
- **C2, tree totals:**
  `Get-ChildItem -LiteralPath <dir> -Recurse -File -Force | Measure-Object -Property Length -Sum`
- **C3, basename sets, routes, years:** `Get-ChildItem ... | ForEach-Object { $_.BaseName }` into a
  `HashSet`, then set differences and a `[regex]::Match` on the year/block/route fields.
- **G1, geometry:** `gdalinfo <file>` from `c:\thesis\envs\multi-channel-env` (GDAL 3.10.2), three
  tiles per channel, key lines extracted with `Select-String`.

No script files were created. Counts are exact sweeps, not samples or extrapolations.

---

## 10. Inconsistencies found between artefacts

Reported, not resolved, per §5.

**I1 — Two different `all.txt` files disagree.**
`C:\thesis\all.txt` holds **19,324** entries. `example_dataset\data\all.txt` holds 19,318 lines =
**19,314 active plus 4 commented out** with a leading `#`. The difference is 10 tiles:

- The **4 commented tiles are exactly the 4 corrupt tiles** listed in `C:\thesis\bad_tiles_scan.txt`
  (`O2021_82_13_1_0024_00141735_7000_0`, `O2021_82_13_1_0024_00141802_8150_2000`,
  `O2021_82_13_1_0025_00144229_8160_1000`, `O2021_82_22_1_0031_00000390_8000_1000`, each failing to
  read in DSM or DTM). The root copy has them **live**. This closes a question left open in
  `REPORT.md` §9, which noted the four `#` lines without knowing why they were there.
- **6 further tiles** are in the root copy but absent from the dataset copy entirely: five from
  route 83-25 (`..._0023_00001881_10000_7000`, `..._0023_00001892_3000_5000`,
  `..._0022_00002146_9000_7000`, `..._0023_00001883_8000_5000`, `..._0023_00001882_10000_0`) and one
  from 82-13 (`..._0026_00144921_3000_1000`). No record was found of why they were removed.

The root `all.txt` is therefore a **stale copy** and must not be used. Everything in this project —
the pixel audit, the fold assignment, the matrix — keys off the dataset copy and its 19,314.

**I2 — Route count depends on the artefact consulted, and no artefact states all three.**
18 routes in the imagery across all channels, 17 in `parent_frame_inventory.csv` (rgb only), 16 in
`fold_assignment.csv`. All three are correct for their population. Route **82-12 appears in no
existing artefact at all**, because every prior inventory read `data\rgb`, where it does not exist.

**I3 — `REPORT.md` §1.3 and this report count the `_10cm` mismatch differently.**
`REPORT.md` states 24 frames where the auxiliary channels carry `_10cm` and rgb/cir carry the plain
name. This session's set-difference classification gives 21 for rgb and 20 for cir. The two use
different rules: `REPORT.md` counted basenames present in all four auxiliary channels and absent from
both nadir ones; this report counts, per channel, missing basenames whose `_10cm`-toggled partner is
present in that same channel. Both are defensible; they answer slightly different questions. **The
figure to quote depends on the sentence being written**, so neither is corrected here.

**I4 — Split-failure logging does not exist.**
`create_patches.py` collects `failed_files` from `splitdst(..., stop_on_error=False)` and prints them,
but writes no file. The tile-count spread between channels therefore cannot be fully decomposed into
"inherited from missing parents" versus "failed during split". Recorded as an open gap.

---

## 11. Figures that could not be established

- **How much of the per-channel tile-count spread is split failure** rather than inherited from
  missing parents (I4). No log exists.
- **Why 6 tiles present in the root `all.txt` were dropped** from the dataset `all.txt` (I1). No
  record found.
- **Why routes 82-12 and 84-42 have no labelled tiles**, and why 82-12 has no nadir imagery. This is
  a data-delivery question, not answerable from disk.
- **Uncompressed volume.** Every figure here is on-disk size with LZW compression applied. The
  uncompressed footprint was not computed and is not estimated.

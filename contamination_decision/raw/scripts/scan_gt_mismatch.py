"""How many of the 19,314 all.txt tiles have a label/image geotransform disagreement?

Header-only scan (no pixel reads). Compares splitted_labels/<t> against splitted/rgb/<t> and
against tile_inventory.csv, and reports per route.
"""
import csv
import os
import re
from collections import Counter, defaultdict

import rasterio

ROOT = r"C:\thesis"
LAB = os.path.join(ROOT, r"multi_channel_dataset_creation\example_dataset\labels\splitted_labels")
RGB = os.path.join(ROOT, r"multi_channel_dataset_creation\example_dataset\data\splitted\rgb")
ALL_TXT = os.path.join(ROOT, r"multi_channel_dataset_creation\example_dataset\data\all.txt")
INV = os.path.join(ROOT, r"exploratory_data_analysis\results\tables\tile_inventory.csv")
OUT = os.path.join(ROOT, r"logs_and_models\contamination_decision\raw")
CONTAM = os.path.join(OUT, "contaminated_tiles.txt")
ROUTE_RE = re.compile(r"^O(\d{4})_(\d{2})_(\d{2})_.+_(\d+)_(\d+)\.tif$")

tiles = [l.strip() for l in open(ALL_TXT, encoding="utf8", errors="replace")
         if l.strip() and not l.strip().startswith("#")]
inv = {r["filename"]: (float(r["easting"]), float(r["northing"]))
       for r in csv.DictReader(open(INV, newline=""))}
contam = set(l.strip() for l in open(CONTAM) if l.strip())


def org(p):
    with rasterio.open(p) as d:
        t = d.transform
        return round(t.c, 3), round(t.f, 3)


bad, bad_inv_lab, bad_inv_rgb = [], 0, 0
per_route = defaultdict(lambda: [0, 0])
for i, t in enumerate(tiles):
    r = f"{ROUTE_RE.match(t).group(2)}-{ROUTE_RE.match(t).group(3)}"
    per_route[r][0] += 1
    le, ln = org(os.path.join(LAB, t))
    re_, rn = org(os.path.join(RGB, t))
    if (le, ln) != (re_, rn):
        per_route[r][1] += 1
        bad.append((t, r, le, ln, re_, rn))
    ie, inn = inv[t]
    if (round(ie, 3), round(inn, 3)) != (le, ln):
        bad_inv_lab += 1
    if (round(ie, 3), round(inn, 3)) != (re_, rn):
        bad_inv_rgb += 1
    if (i + 1) % 4000 == 0:
        print(f"  {i+1:,}/{len(tiles):,} scanned, {len(bad):,} mismatched", flush=True)

print(f"\ntiles scanned: {len(tiles):,}")
print(f"label vs rgb geotransform MISMATCH: {len(bad):,} ({100*len(bad)/len(tiles):.2f} %)")
print(f"tile_inventory disagrees with LABEL geotransform: {bad_inv_lab:,}")
print(f"tile_inventory disagrees with RGB   geotransform: {bad_inv_rgb:,}")

print("\nper route (mismatched / total):")
for r in sorted(per_route, key=lambda x: -per_route[x][1]):
    tot, b = per_route[r]
    if b:
        print(f"  {r}: {b:,} / {tot:,}  ({100*b/tot:.1f} %)")
print("  routes with zero mismatch: "
      + ", ".join(r for r in sorted(per_route) if per_route[r][1] == 0))

nc = sum(1 for t, *_ in bad if t in contam)
print(f"\nof the {len(bad):,} mismatched tiles, {nc:,} are in the 1,281 contaminated set "
      f"({100*nc/len(bad):.1f} %)")

offs = Counter((round(re_ - le, 1), round(rn - ln, 1)) for _, _, le, ln, re_, rn in bad)
print("\nmost common (rgb - label) origin offsets, metres:")
for k, v in offs.most_common(10):
    print(f"  dE={k[0]:+.1f}  dN={k[1]:+.1f}  : {v:,} tiles")

with open(os.path.join(OUT, "geotransform_mismatch_tiles.csv"), "w", newline="",
          encoding="utf8") as f:
    w = csv.writer(f)
    w.writerow(["tile", "route", "label_E", "label_N", "rgb_E", "rgb_N", "dE", "dN",
                "in_contaminated_set"])
    for t, r, le, ln, re_, rn in bad:
        w.writerow([t, r, le, ln, re_, rn, round(re_ - le, 3), round(rn - ln, 3), t in contam])
print(f"\nwrote {OUT}\\geotransform_mismatch_tiles.csv")

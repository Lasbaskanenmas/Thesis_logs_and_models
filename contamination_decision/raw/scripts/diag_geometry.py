"""Why do 199 of the 6,783 cross-fold pairs yield no rectangle from tile_inventory.csv geometry?"""
import csv
import os
from collections import Counter

ROOT = r"C:\thesis"
OVERLAPS = os.path.join(ROOT, r"logs_and_models\filename_provenance\cross_route_tile_overlaps.csv")
TILE_INV = os.path.join(ROOT, r"exploratory_data_analysis\results\tables\tile_inventory.csv")
SIDE = 100.0

geom = {r["filename"]: (float(r["easting"]), float(r["northing"]))
        for r in csv.DictReader(open(TILE_INV, newline=""))}
rows = [r for r in csv.DictReader(open(OVERLAPS, newline="")) if r["fold_a"] != r["fold_b"]]

bad, ok = [], 0
for r in rows:
    ta, tb = r["tile_a"], r["tile_b"]
    if ta not in geom or tb not in geom:
        bad.append((r, "tile missing from inventory", None))
        continue
    ex, ny = geom[ta]
    ox, oy = geom[tb]
    x0, x1 = max(ex, ox), min(ex + SIDE, ox + SIDE)
    y0, y1 = max(ny - SIDE, oy - SIDE), min(ny, oy)
    area = (x1 - x0) * (y1 - y0) if (x1 > x0 and y1 > y0) else 0.0
    if area <= 0:
        bad.append((r, "empty intersection", (x1 - x0, y1 - y0)))
    else:
        ok += 1

print(f"cross-fold pairs: {len(rows):,}   with a rectangle: {ok:,}   without: {len(bad):,}")
print(f"reasons: {Counter(b[1] for b in bad)}")

print("\ndeclared overlap_m2 of the failing pairs:")
a = sorted(float(b[0]["overlap_m2"]) for b in bad)
print(f"  min {a[0]:,.1f}  median {a[len(a)//2]:,.1f}  max {a[-1]:,.1f}")
print(f"  all <= 100 m2: {a[-1] <= 100}")

print("\nroute pairs affected:")
for k, v in Counter((b[0]['route_a'], b[0]['route_b']) for b in bad).most_common():
    print(f"  {k[0]} x {k[1]}: {v}")

print("\nfirst 6 failing pairs (dx, dy of the attempted intersection):")
for r, why, d in bad[:6]:
    ex, ny = geom[r["tile_a"]]
    ox, oy = geom[r["tile_b"]]
    print(f"  {r['tile_a']}\n    vs {r['tile_b']}\n    declared {float(r['overlap_m2']):>8,.1f} m2 "
          f"| A origin ({ex:.1f},{ny:.1f}) B origin ({ox:.1f},{oy:.1f}) "
          f"| dx={ox-ex:+.1f} dy={oy-ny:+.1f} | intersect {d}")

# how many DISTINCT tiles lose all their windows
lost = set()
for r, _, _ in bad:
    lost.add(r["tile_a"])
    lost.add(r["tile_b"])
kept = set()
for r in rows:
    ta, tb = r["tile_a"], r["tile_b"]
    if ta in geom and tb in geom:
        ex, ny = geom[ta]
        ox, oy = geom[tb]
        if min(ex + SIDE, ox + SIDE) > max(ex, ox) and min(ny, oy) > max(ny - SIDE, oy - SIDE):
            kept.add(ta)
            kept.add(tb)
print(f"\ntiles touched by a failing pair: {len(lost):,}; "
      f"of those with NO surviving window: {len(lost - kept):,}")

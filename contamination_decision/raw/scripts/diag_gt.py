"""Which artefact is wrong for the 199 pairs: tile_inventory.csv coords, or overlap_m2?

Reads the true geotransform from the label rasters and compares against both sources.
"""
import csv
import os

TILES = [
    "O2021_82_20_1_0023_00004973_14000_11000.tif",
    "O2021_82_20_1_0023_00004973_15000_11000.tif",
    "O2021_82_21_1_0005_00001868_0_1000.tif",
    "O2021_82_20_1_0023_00004974_14000_6000.tif",
    "O2021_82_21_1_0005_00001869_0_1000.tif",
]
ROOT = r"C:\thesis"
LAB = os.path.join(ROOT, r"multi_channel_dataset_creation\example_dataset\labels\splitted_labels")
RGB = os.path.join(ROOT, r"multi_channel_dataset_creation\example_dataset\data\splitted\rgb")
INV = os.path.join(ROOT, r"exploratory_data_analysis\results\tables\tile_inventory.csv")

try:
    import rasterio
    opener = "rasterio"
except ImportError:
    rasterio = None
    from osgeo import gdal
    opener = "gdal"
print("reader:", opener)

geom = {r["filename"]: (float(r["easting"]), float(r["northing"]))
        for r in csv.DictReader(open(INV, newline="")) if r["filename"] in TILES}


def origin(path):
    if rasterio:
        with rasterio.open(path) as d:
            t = d.transform
            return t.c, t.f, d.width, d.height, t.a, t.e
    d = gdal.Open(path)
    g = d.GetGeoTransform()
    return g[0], g[3], d.RasterXSize, d.RasterYSize, g[1], g[5]


print(f"\n{'tile':<46}{'inv_E':>12}{'inv_N':>13}{'gt_E':>12}{'gt_N':>13}{'dE':>9}{'dN':>9}")
for t in TILES:
    for folder, tag in ((LAB, "label"), (RGB, "rgb")):
        p = os.path.join(folder, t)
        if not os.path.isfile(p):
            print(f"{t:<46}  MISSING in {tag}")
            continue
        e, n, w, h, px, py = origin(p)
        ie, inn = geom.get(t, (float("nan"), float("nan")))
        print(f"{(t + ' [' + tag + ']'):<46}{ie:>12.1f}{inn:>13.1f}{e:>12.1f}{n:>13.1f}"
              f"{ie-e:>+9.1f}{inn-n:>+9.1f}   ({w}x{h} @ {px},{py})")

# recompute the declared overlap from true geotransforms
print("\noverlap recomputed from the TRUE geotransforms:")
pairs = [("O2021_82_20_1_0023_00004973_14000_11000.tif",
          "O2021_82_21_1_0005_00001868_0_1000.tif", 893.0),
         ("O2021_82_20_1_0023_00004973_15000_11000.tif",
          "O2021_82_21_1_0005_00001868_0_1000.tif", 3807.0),
         ("O2021_82_20_1_0023_00004974_14000_6000.tif",
          "O2021_82_21_1_0005_00001868_0_1000.tif", 1560.0)]
for a, b, declared in pairs:
    ea, na, wa, ha, pxa, _ = origin(os.path.join(LAB, a))
    eb, nb, wb, hb, pxb, _ = origin(os.path.join(LAB, b))
    sa, sb = wa * pxa, wb * pxb
    x0, x1 = max(ea, eb), min(ea + sa, eb + sb)
    y0, y1 = max(na - ha * pxa, nb - hb * pxb), min(na, nb)
    area = (x1 - x0) * (y1 - y0) if (x1 > x0 and y1 > y0) else 0.0
    print(f"  declared {declared:>8,.1f}  from geotransform {area:>8,.1f}  "
          f"{'MATCH' if abs(area-declared) < 1.5 else 'DISAGREE'}")

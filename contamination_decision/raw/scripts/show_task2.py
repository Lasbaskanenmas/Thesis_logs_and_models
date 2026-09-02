import csv
import os

OUT = r"C:\thesis\logs_and_models\contamination_decision"
PRED = ["asfalt", "fliser", "grus", "ubefestet", "green_roof",
        "drivhus", "betonflade", "brosten", "solceller"]
rows = list(csv.DictReader(open(os.path.join(OUT, "task2_rescore_table.csv"), newline="")))
print(f"cells: {len(rows)}")

print(f"\n{'cell':<34}{'mIoU_all':>9}{'mIoU_cln':>10}{'d_mIoU':>9}"
      f"{'acc_all':>9}{'acc_cln':>9}{'d_acc':>9}{'mF1_all':>9}{'mF1_cln':>9}{'d_mF1':>9}")
for r in sorted(rows, key=lambda x: float(x["d_macro_iou"])):
    print(f"{r['cell']:<34}{float(r['macro_iou_all']):>9.4f}{float(r['macro_iou_clean']):>10.4f}"
          f"{float(r['d_macro_iou']):>+9.4f}{float(r['acc_all']):>9.4f}{float(r['acc_clean']):>9.4f}"
          f"{float(r['d_acc']):>+9.4f}{float(r['macro_f1_all']):>9.4f}"
          f"{float(r['macro_f1_clean']):>9.4f}{float(r['d_macro_f1']):>+9.4f}")

d = [float(r["d_macro_iou"]) for r in rows]
da = [float(r["d_acc"]) for r in rows]
print(f"\nd_macro_iou : min {min(d):+.4f}  max {max(d):+.4f}  mean {sum(d)/len(d):+.4f}  "
      f"all negative: {all(x < 0 for x in d)}")
print(f"d_accuracy  : min {min(da):+.4f} max {max(da):+.4f} mean {sum(da)/len(da):+.4f}")

print("\nper-class IoU delta (clean - all), mean over the 28 cells:")
print(f"{'class':<12}{'mean d':>10}{'min d':>10}{'max d':>10}{'mean IoU all':>14}{'mean IoU clean':>16}")
for c in PRED:
    vs = [float(r[f"d_{c}"]) for r in rows if r[f"d_{c}"] not in ("", "None")]
    a = [float(r[f"iou_all_{c}"]) for r in rows if r[f"iou_all_{c}"] not in ("", "None")]
    b = [float(r[f"iou_clean_{c}"]) for r in rows if r[f"iou_clean_{c}"] not in ("", "None")]
    if not vs:
        print(f"{c:<12}{'n/a':>10}")
        continue
    print(f"{c:<12}{sum(vs)/len(vs):>+10.4f}{min(vs):>+10.4f}{max(vs):>+10.4f}"
          f"{sum(a)/len(a):>14.4f}{sum(b)/len(b):>16.4f}")

print("\nranking stability (by Macro-IoU):")
ra = [r["cell"] for r in sorted(rows, key=lambda x: -float(x["macro_iou_all"]))]
rb = [r["cell"] for r in sorted(rows, key=lambda x: -float(x["macro_iou_clean"]))]
moved = [(c, ra.index(c) + 1, rb.index(c) + 1) for c in ra if ra.index(c) != rb.index(c)]
print(f"  cells changing rank: {len(moved)} of {len(ra)}")
for c, i, j in moved:
    print(f"    {c:<34} {i:>2} -> {j:>2}")
print(f"  top-5 all  : {ra[:5]}")
print(f"  top-5 clean: {rb[:5]}")
print(f"  best cell unchanged: {ra[0] == rb[0]}  ({ra[0]})")

# excluded classes / macro count changes
ch = [r for r in rows if r["n_macro_all"] != r["n_macro_clean"]]
print(f"\ncells where the number of macro classes changed: {len(ch)}")
for r in ch:
    print(f"    {r['cell']}: {r['n_macro_all']} -> {r['n_macro_clean']} "
          f"(excluded: {r['excluded_clean']})")

print(f"\npixels: all {int(rows[0]['px_all']):,}  clean {int(rows[0]['px_clean']):,}  "
      f"dropped {int(rows[0]['px_all'])-int(rows[0]['px_clean']):,} "
      f"({100*(int(rows[0]['px_all'])-int(rows[0]['px_clean']))/int(rows[0]['px_all']):.2f} %)")

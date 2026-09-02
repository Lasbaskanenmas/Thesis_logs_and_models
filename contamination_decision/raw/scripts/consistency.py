"""Cross-artefact consistency audit for the DECISION.md inconsistency section."""
import csv
import json
import os

ROOT = r"C:\thesis"
MATRIX = os.path.join(ROOT, r"logs_and_models\spatial_matrix")
RESCSV = os.path.join(MATRIX, "matrix_results_all_cells.csv")
OUT = os.path.join(ROOT, r"logs_and_models\contamination_decision\raw")
PRED = ["asfalt", "fliser", "grus", "ubefestet", "green_roof",
        "drivhus", "betonflade", "brosten", "solceller"]
findings = []


def note(sev, msg):
    findings.append({"severity": sev, "finding": msg})
    print(f"[{sev}] {msg}")


# 1. published results CSV vs each cell's pooled_oof_metrics.json
pub = list(csv.DictReader(open(RESCSV, newline="")))
print(f"matrix_results_all_cells.csv: {len(pub)} rows\n")
oof = {}
for m in sorted(os.listdir(MATRIX)):
    d = os.path.join(MATRIX, m)
    if not os.path.isdir(d):
        continue
    for c in sorted(os.listdir(d)):
        p = os.path.join(d, c, "pooled_oof_metrics.json")
        if c.startswith("oof_") and os.path.isfile(p):
            oof[c[4:]] = p

worst = 0.0
for r in pub:
    cell = r["cell"]
    if cell not in oof:
        note("HIGH", f"published cell '{cell}' has no pooled_oof_metrics.json")
        continue
    h = json.load(open(oof[cell], encoding="utf8"))["headline_pooled_oof"]
    for key, col in (("macro_iou", "macro_iou"), ("macro_f1", "macro_f1"),
                     ("overall_accuracy", "overall_acc")):
        d = abs(h[key] - float(r[col]))
        worst = max(worst, d)
        if d > 1e-9:
            note("MEDIUM", f"{cell}: {col} CSV {r[col]} vs json {h[key]} (diff {d:.2e})")
    for c in PRED:
        if r[c] in ("", "-"):
            continue
        v = h["per_class"][c]["iou"]
        if v is None:
            note("MEDIUM", f"{cell}: {c} IoU is null in json but {r[c]} in the CSV")
            continue
        d = abs(v - float(r[c]))
        worst = max(worst, d)
        if d > 1e-9:
            note("MEDIUM", f"{cell}: {c} IoU CSV {r[c]} vs json {v} (diff {d:.2e})")
    if int(r["tiles"]) != 19314:
        note("MEDIUM", f"{cell}: CSV tiles={r['tiles']}, expected 19314")
print(f"max |CSV - json| discrepancy over every published figure: {worst:.3e}\n")

# 2. oof cells not in the published CSV
extra = sorted(set(oof) - {r["cell"] for r in pub})
if extra:
    note("INFO", f"{len(extra)} scored cells exist on disk but are absent from "
                 f"matrix_results_all_cells.csv: {extra}")

# 3. trained-but-never-scored arms
for m in sorted(os.listdir(MATRIX)):
    d = os.path.join(MATRIX, m)
    if not os.path.isdir(d):
        continue
    for job in sorted(os.listdir(d)):
        jd = os.path.join(d, job)
        if job.startswith("oof_") or not os.path.isdir(jd):
            continue
        mdl = os.path.join(jd, "models")
        pdir = os.path.join(mdl, "example_dataset")
        has_ckpt = os.path.isdir(mdl) and any(f.endswith(".pth") for f in os.listdir(mdl))
        n_pred = len([f for f in os.listdir(pdir) if f.endswith(".tif")]) \
            if os.path.isdir(pdir) else 0
        if has_ckpt and n_pred == 0:
            note("HIGH", f"{m}/{job}: trained (checkpoints present) but ZERO predictions "
                         f"-> inference never run, cell cannot be scored or rescored")

# 4. design documents named as canonical by the work order
for doc in ["2026-07-29_the_great_plan_3.0.md", "2026-06-26_create_spatial_folds.md",
            "2026-07-28_matrix_results_and_handoff.md"]:
    hits = []
    for dp, _, fs in os.walk(ROOT):
        if any(x in dp for x in ("\\envs\\", "\\wandb\\", "\\.git")):
            continue
        if doc in fs:
            hits.append(os.path.join(dp, doc))
    if not hits:
        note("HIGH", f"design document '{doc}' named by the work order is NOT present anywhere "
                     f"under C:\\thesis - claims could not be checked against it")

with open(os.path.join(OUT, "consistency_findings.json"), "w", encoding="utf8") as f:
    json.dump({"max_csv_json_discrepancy": worst, "findings": findings}, f, indent=2)
print(f"\n{len(findings)} findings -> {OUT}\\consistency_findings.json")

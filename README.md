# Thesis results and provenance

Scores, logs and split definitions from the 72-run spatial
cross-validation matrix (2026-06-27 to 2026-07-25).

## What is here
- `route_class_audit/` — the frozen 3-fold route-blocked split.
  `fold_assignment.csv` is load-bearing: all 72 models are tied to it.
- `spatial_matrix/<model>/oof_<cell>/pooled_oof_metrics.json` — the 24
  pooled out-of-fold results, one per cell.
- `spatial_matrix/<model>/<job>/logs/` — per-epoch metrics and job
  dictionaries for all 72 runs.
- `class_pixel_audit/` — per-class pixel counts behind the
  effective-number loss weights.
- `dataset_inventory/`, `filename_provenance/` — dataset audits.

## What is not here, and why
Model weights (60 GB), per-epoch checkpoints (657 GB) and the 463,536
out-of-fold prediction GeoTIFFs are excluded by `.gitignore`. The 72
final models and the 24 scores are mirrored to the private HF repo
`Lasbaskanenmas/befaestelsesdata-spatial-matrix`. Predictions are
regenerable by re-running inference from those weights.
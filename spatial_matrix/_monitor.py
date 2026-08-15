"""Spatial-matrix progress monitor.

Stateless w.r.t. the training run; keeps its own snapshot in _monitor_state.json
and emits EVENTS (newly-succeeded steps, failed steps, crash/done) by diffing the
filesystem against the previous snapshot. Detection is artifact-based because the
driver .cmd has no error handling and no stdout capture.

  train step success  -> <run>/models/<run>.pth exists
  infer step success  -> <run>/models/example_dataset/ has >0 files
  failure             -> a step BEHIND the frontier never produced its artifact
  crash               -> matrix incomplete AND no ML python.exe alive
  done                -> final unweighted infer artifact present
"""
import json, os, sys, subprocess, datetime

BASE = r"C:\thesis\logs_and_models\spatial_matrix"
STATE = os.path.join(BASE, "_monitor_state.json")

MODELS   = ["unet_resnet34", "segformer_b1", "convnext_upernet", "swin_upernet"]
VARIANTS = ["rgb", "6ch", "10ch"]
FOLDS    = ["fold0", "fold1", "fold2"]

def runs(suffix):
    out = []
    for m in MODELS:
        for v in VARIANTS:
            for f in FOLDS:
                out.append((m, f"{m}_{v}_{f}{suffix}"))
    return out

# Global ordered step list, exactly matching run_spatial_matrix.cmd phase order.
STEPS = []  # (phase, model, run, kind)
for m, r in runs(""):      STEPS.append(("w_train",  m, r, "train"))
for m, r in runs(""):      STEPS.append(("w_infer",  m, r, "infer"))
for m, r in runs("_unw"):  STEPS.append(("u_train",  m, r, "train"))
for m, r in runs("_unw"):  STEPS.append(("u_infer",  m, r, "infer"))

def pth_path(m, r):  return os.path.join(BASE, m, r, "models", f"{r}.pth")
def pred_dir(m, r):  return os.path.join(BASE, m, r, "models", "example_dataset")

def step_done(kind, m, r):
    if kind == "train":
        return os.path.isfile(pth_path(m, r))
    d = pred_dir(m, r)
    return os.path.isdir(d) and any(os.scandir(d))

def ml_python_alive():
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "(Get-Process python -ErrorAction SilentlyContinue | Measure-Object).Count"],
            capture_output=True, text=True, timeout=30).stdout.strip()
        return int(out or "0") > 0
    except Exception:
        return True  # fail safe: don't cry crash on a transient query error

def main():
    done = [step_done(k, m, r) for (_, m, r, k) in STEPS]
    frontier = max((i for i, d in enumerate(done) if d), default=-1)
    completed = [i for i, d in enumerate(done) if d]
    failed = [i for i in range(frontier) if not done[i]]  # gaps behind frontier
    alive = ml_python_alive()
    all_done = all(done)
    # crash = work remains, nothing running, and we actually started
    crashed = (not all_done) and (not alive) and (frontier >= 0)

    prev = {}
    if os.path.isfile(STATE):
        try: prev = json.load(open(STATE))
        except Exception: prev = {}
    prev_completed = set(prev.get("completed", []))
    prev_failed    = set(prev.get("failed", []))
    prev_crashed   = prev.get("crashed", False)
    prev_done      = prev.get("all_done", False)

    # ---- daily digest bookkeeping ----
    today = datetime.date.today().isoformat()
    last_digest_date     = prev.get("last_digest_date", today)
    last_digest_frontier = prev.get("last_digest_frontier", frontier)
    digest_due = (last_digest_date != today)

    def label(i):
        ph, m, r, k = STEPS[i]
        return f"{r} [{k}]"

    events = []
    for i in completed:
        if i not in prev_completed:
            events.append(("SUCCESS", label(i)))
    for i in failed:
        if i not in prev_failed:
            events.append(("FAILED", label(i)))
    if crashed and not prev_crashed:
        events.append(("CRASH", f"frontier at step {frontier+1}/{len(STEPS)} ({label(frontier)})"))
    if all_done and not prev_done:
        events.append(("DONE", "all 144 train+infer artifacts present"))

    # consume the digest if due (so it only fires once per calendar day)
    if digest_due:
        new_digest_date, new_digest_frontier = today, frontier
    else:
        new_digest_date, new_digest_frontier = last_digest_date, last_digest_frontier

    json.dump({"ts": datetime.datetime.now().isoformat(timespec="seconds"),
               "completed": completed, "failed": failed,
               "crashed": crashed, "all_done": all_done,
               "frontier": frontier,
               "last_digest_date": new_digest_date,
               "last_digest_frontier": new_digest_frontier},
              open(STATE, "w"), indent=2)

    n_train = sum(1 for i in completed if STEPS[i][3] == "train")
    n_infer = sum(1 for i in completed if STEPS[i][3] == "infer")
    print(f"TS {datetime.datetime.now():%Y-%m-%d %H:%M:%S}")
    print(f"ALIVE={alive}  FRONTIER={frontier+1}/{len(STEPS)}  "
          f"TRAIN_DONE={n_train}/72  INFER_DONE={n_infer}/72")
    cur = STEPS[frontier+1] if frontier+1 < len(STEPS) else None
    if cur: print(f"NEXT/CURRENT: {cur[2]} [{cur[3]}]")
    # Immediate-alert events: crash / failed / done. SUCCESS is routine -> digest only.
    alert_events = [(k, l) for (k, l) in events if k in ("FAILED", "CRASH", "DONE")]
    if not alert_events:
        print("ALERTS: none")
    else:
        for kind, lab in alert_events:
            print(f"ALERT {kind}: {lab}")

    if digest_due:
        newly = [label(i) for i in completed if i > last_digest_frontier]
        print(f"DIGEST_DUE (since {last_digest_date}, prev frontier "
              f"{last_digest_frontier+1}): {len(newly)} new run(s) completed")
        for lab in newly:
            print(f"  + {lab}")
    else:
        print("DIGEST: not due today")

if __name__ == "__main__":
    main()

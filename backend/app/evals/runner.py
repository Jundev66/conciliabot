from __future__ import annotations

import json
import os
import shutil
import tempfile
from typing import Any

from .. import db
from ..agent import pipeline
from ..seed import _seed_duplicate_reference
from .golden import GOLDEN, evaluate_thresholds


def run_evals() -> dict[str, Any]:
    """Run the golden dataset against the real pipeline in an isolated DB.

    Returns per-case results and aggregate metrics. The caller (or CI) decides
    whether to gate a deploy based on `passed`.
    """
    original_db_path = db.DB_PATH
    tmp_dir = tempfile.mkdtemp(prefix="conciliabot-evals-")
    db.DB_PATH = os.path.join(tmp_dir, "eval.db")
    try:
        db.init_db()
        _seed_duplicate_reference()

        cases: list[dict[str, Any]] = []
        status_ok = format_ok = fiscal_ok = 0
        disc_ok = 0
        dup_tp = dup_fp = dup_fn = 0
        traj_ok = 0

        for case in GOLDEN:
            inv, _ = pipeline.run_pipeline(case.text, case.filename, case.source)

            s_ok = inv.status.value == case.expected_status
            f_ok = inv.format.value == case.expected_format
            fi_ok = inv.fiscal.verified == case.expect_fiscal
            has_disc = len(inv.discrepancies) > 0
            d_ok = has_disc == case.expect_discrepancy
            is_dup = inv.status.value == "duplicate"

            if case.expect_duplicate and is_dup:
                dup_tp += 1
            elif is_dup and not case.expect_duplicate:
                dup_fp += 1
            elif case.expect_duplicate and not is_dup:
                dup_fn += 1

            present = {s.key for s in inv.pipeline if s.status.value in {"done", "warning"}}
            t_ok = all(step in present for step in case.expected_steps)

            status_ok += int(s_ok)
            format_ok += int(f_ok)
            fiscal_ok += int(fi_ok)
            disc_ok += int(d_ok)
            traj_ok += int(t_ok)

            cases.append(
                {
                    "id": case.id,
                    "expected_status": case.expected_status,
                    "actual_status": inv.status.value,
                    "ok": s_ok and f_ok and fi_ok and d_ok and t_ok,
                    "status_ok": s_ok,
                    "format_ok": f_ok,
                    "fiscal_ok": fi_ok,
                    "discrepancy_ok": d_ok,
                    "trajectory_ok": t_ok,
                }
            )

        n = len(GOLDEN)
        duplicate_denom = dup_tp + dup_fn
        metrics = {
            "status_accuracy": round(status_ok / n, 3),
            "format_accuracy": round(format_ok / n, 3),
            "fiscal_accuracy": round(fiscal_ok / n, 3),
            "discrepancy_accuracy": round(disc_ok / n, 3),
            "duplicate_recall": round(dup_tp / duplicate_denom, 3) if duplicate_denom else 1.0,
            "trajectory_pass_rate": round(traj_ok / n, 3),
        }
        passed, thresholds = evaluate_thresholds(metrics)
        return {
            "cases": cases,
            "metrics": metrics,
            "thresholds": thresholds,
            "passed": passed,
            "case_count": n,
        }
    finally:
        db.DB_PATH = original_db_path
        shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == "__main__":
    result = run_evals()
    print(json.dumps(result, indent=2, ensure_ascii=False))
    raise SystemExit(0 if result["passed"] else 1)

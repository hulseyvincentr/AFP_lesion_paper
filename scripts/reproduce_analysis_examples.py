#!/usr/bin/env python3
"""Verify included analysis inputs and regenerate Figure 3E review plots."""
import argparse
from pathlib import Path
import subprocess
import sys

import numpy as np
import pandas as pd


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outdir", type=Path, default=Path("outputs/analysis_examples"))
    parser.add_argument("--dpi", type=int, default=100)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    inputs = root / "examples/figure_inputs"
    stats = root / "examples/statistics_inputs"
    out = args.outdir.resolve()
    subprocess.run([sys.executable, str(root / "scripts/check_figure3_pair_inputs.py"),
                    "--pair-metrics", str(inputs / "figure3_balanced_pair_metrics.csv")], check=True)
    pairs = pd.read_csv(inputs / "figure3_balanced_pair_metrics.csv")
    clusters = pd.read_csv(inputs / "figure4_medial_lateral_cluster_BC.csv")
    if clusters.duplicated(["animal_id", "syllable"]).any():
        raise RuntimeError("Duplicate acoustic bird/syllable rows.")
    thresholds = pairs.groupby("animal_id").delta_cv.quantile(0.75)
    selected = pairs.assign(expected_q75=pairs.delta_cv >= pairs.animal_id.map(thresholds))
    merged = clusters.merge(selected[["animal_id", "syllable", "expected_q75"]],
                            on=["animal_id", "syllable"], how="left", validate="one_to_one")
    if merged.expected_q75.isna().any() or not np.array_equal(merged.is_q75, merged.expected_q75):
        raise RuntimeError("Acoustic Q75 flags differ from phrase-duration selection.")
    reference = pd.read_csv(stats / "panelD_pooled_ML_Q75_by_bird.csv")
    for flag, prefix in [(True, "q75"), (False, "below_q75")]:
        actual = clusters[clusters.is_q75.eq(flag)].groupby("animal_id").agg(
            pre=("pre_bc", "median"), post=("post_bc", "median"))
        joined = actual.merge(reference, on="animal_id", how="outer", indicator=True)
        if len(joined) != 8 or not joined["_merge"].eq("both").all():
            raise RuntimeError("Figure 4D bird set differs.")
        for field in ["pre", "post"]:
            if not np.allclose(joined[field], joined[f"{prefix}_{field}_bc"], rtol=0, atol=1e-12):
                raise RuntimeError(f"Figure 4D {prefix} {field} BC differs.")
    print("PASS: 61 medial+lateral cluster rows reproduce Q75 selection and both Figure 4D subsets for 8 birds.", flush=True)
    subprocess.run([sys.executable, str(root / "code/figure_generation/figure3_timecourse.py"),
                    "--pair-metrics", str(inputs / "figure3_balanced_pair_metrics.csv"),
                    "--duration-long-csv", str(inputs / "figure3_phrase_duration_long.csv.gz"),
                    "--output", str(out / "figure3_timecourse"), "--dpi", str(args.dpi)], check=True)
    print(f"PASS: Figure 3E and individual time-course review plots generated in {out}.")
    print("These plots are for verification; submission TIFFs and raw-annotation/NPZ analyses are separate.")


if __name__ == "__main__":
    main()

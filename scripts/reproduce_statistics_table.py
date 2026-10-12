#!/usr/bin/env python3
"""Regenerate all 14 statistics-table rows and compare them with the submitted results."""
import argparse
from pathlib import Path
import subprocess
import sys

import numpy as np
import pandas as pd


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outdir", type=Path, default=Path("outputs/statistics_table_check"))
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    inputs = root / "examples/statistics_inputs"
    outdir = args.outdir.resolve()
    subprocess.run([
        sys.executable, str(root / "code/analysis/make_eneuro_statistics_table_combined.py"),
        "--quantiles", str(inputs / "01_bird_level_Q60_Q75_Q90.csv"),
        "--permutation-results", str(inputs / "03_pairwise_exact_permutation_tests.csv"),
        "--panel-c", str(inputs / "panelC_all_qualifying_by_lesion_group_by_bird.csv"),
        "--panel-d", str(inputs / "panelD_pooled_ML_Q75_by_bird.csv"),
        "--outdir", str(outdir), "--bootstrap-reps", "200000", "--seed", "123",
    ], check=True)
    actual = pd.read_csv(outdir / "statistics_full_precision.csv")
    expected = pd.read_csv(inputs / "expected_statistics_full_precision.csv")
    keys = ["row", "figure", "comparison", "n"]
    if len(actual) != 14 or not actual[keys].equals(expected[keys]):
        raise RuntimeError("Statistics-table row order, labels or sample sizes do not match.")
    for column in ["effect", "ci_low", "ci_high", "test_statistic", "p_raw", "p_adjusted"]:
        if not np.allclose(actual[column], expected[column], rtol=0, atol=1e-10):
            raise RuntimeError(f"Statistics-table values do not match: {column}")
    print("PASS: all 14 rows match the manuscript reference values.")
    print(f"Word table and CSVs: {outdir}")


if __name__ == "__main__":
    main()

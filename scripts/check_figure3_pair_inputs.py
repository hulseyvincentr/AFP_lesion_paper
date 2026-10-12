#!/usr/bin/env python3
"""Find balanced-pair inputs whose bird quantiles match the manuscript reference."""
import argparse
import importlib.util
from pathlib import Path
import sys

import numpy as np
import pandas as pd


def compare(actual, expected):
    keys = ["animal_id", "group", "quantile"]
    if actual.duplicated(keys).any() or expected.duplicated(keys).any():
        raise ValueError("Duplicate bird/group/quantile records.")
    merged = actual.merge(expected, on=keys, how="outer", suffixes=("_actual", "_expected"), indicator=True)
    if len(merged) != len(expected) or not merged["_merge"].eq("both").all():
        return False, "Bird IDs, lesion groups or quantiles differ."
    if not np.array_equal(merged.n_qualifying_syllables_actual, merged.n_qualifying_syllables_expected):
        return False, "Qualifying-syllable counts differ."
    differences = np.abs(merged.quantile_delta_cv_actual - merged.quantile_delta_cv_expected)
    if not np.allclose(differences, 0, rtol=0, atol=1e-10):
        return False, f"Quantile values differ (maximum absolute difference {differences.max():.6g})."
    return True, f"All {len(expected)} bird-level quantiles and syllable counts match."


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pair-metrics", type=Path)
    parser.add_argument("--search-root", type=Path, nargs="+")
    args = parser.parse_args()
    if bool(args.pair_metrics) == bool(args.search_root):
        parser.error("Provide either --pair-metrics or --search-root.")
    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location("quantile_sensitivity_check", root / "code/analysis/quantile_sensitivity_table.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    expected = pd.read_csv(root / "examples/statistics_inputs/01_bird_level_Q60_Q75_Q90.csv")
    if args.pair_metrics:
        paths = [args.pair_metrics.expanduser().resolve()]
    else:
        paths = sorted({path.resolve() for folder in args.search_root if folder.expanduser().exists()
                        for path in folder.expanduser().rglob("figure3_balanced_pair_metrics.csv")})
    if not paths:
        print("No balanced-pair input files found in the supplied folders.")
        return 1
    matches = 0
    for path in paths:
        try:
            actual = module.make_bird_quantiles(module.load_data(path), "linear")
            passed, detail = compare(actual, expected)
        except Exception as error:
            passed, detail = False, str(error).splitlines()[0]
        print(f"{'MATCH' if passed else 'NO MATCH'}: {path}\n  {detail}")
        matches += int(passed)
    print(f"\nMatching inputs: {matches} of {len(paths)} candidates.")
    print("A match establishes downstream summary agreement; annotation provenance and time-course inputs still require verification.")
    return 0 if matches else 1


if __name__ == "__main__":
    raise SystemExit(main())

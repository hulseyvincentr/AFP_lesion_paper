# Manuscript-to-code map and inputs

## Verified Table 1 entry point

Run `python scripts/reproduce_statistics_table.py`. This invokes
`code/analysis/make_eneuro_statistics_table_combined.py` with the four included
CSV inputs, seed 123 and 200,000 bootstrap draws, and checks all 14 rows against
`examples/statistics_inputs/expected_statistics_full_precision.csv`.

The included inputs are:

| File | Meaning |
|---|---|
| `01_bird_level_Q60_Q75_Q90.csv` | One quantile summary per bird per quantile; group sizes 9 medial+lateral, 8 lateral-only and 4 sham |
| `03_pairwise_exact_permutation_tests.csv` | Reference exact-permutation results, checked against recalculation |
| `panelC_all_qualifying_by_lesion_group_by_bird.csv` | Paired pre/post median BC for 20 birds; 8 medial+lateral, 8 lateral-only, 4 sham |
| `panelD_pooled_ML_Q75_by_bird.csv` | Paired BC for ≥Q75 and <Q75 subsets in 8 medial+lateral birds |

Bird 20 is included in phrase-duration analyses but excluded from acoustic
analyses because no cluster met the four-period data requirement. The Panel C
input is the version whose medial+lateral pre/post medians round to 0.9907 and
0.9758. File modification times alone are not used to select versions.

These inputs are analysis summaries. They allow independent reproduction of
the reported Table 1 calculations, but not of upstream annotation or balancing.

## Main manuscript mapping

| Manuscript item | Script / input | Verification status |
|---|---|---|
| Table 1, rows a–n | `code/analysis/make_eneuro_statistics_table_combined.py` | Verified with included study data |
| Figure 3A–B, quantile selection and bird-level tests | `code/figure_generation/figure3_q75_phrase_duration.py` | Requires balanced-pair and long-duration input; full rerun pending |
| Figure 3E daily CV | `code/figure_generation/figure3_timecourse.py` from supplied UPDATED_v2 source | Settings match Methods; original-data/output comparison pending |
| Extended Data Table 3-2 | `code/analysis/quantile_sensitivity_table.py` | Requires balanced-pair input; downstream tests verified through Table 1 |
| Figure 4C–D | `code/figure_generation/figure4_bhattacharyya_q75.py` | Requires final qualifying cluster-level BC CSV and Q75 selection CSV |
| Cluster-level BC | `code/analysis/bhattacharyya_cluster_analysis.py` with bundled `code/helpers/bhattacharyya_spectrogram_export.py` and `pre_post_syllable_spectrograms.py` | Helper wiring checked; full data rerun pending |
| Extended Data Figure 2-1 UMAPs, Figure 3-1 duration examples | `code/figure_generation/suppfig2_annotation_qc.py`, `phrase_duration_examples.py` | Require per-bird annotation and embedding data |
| Extended Data Table 3-1 | Animal metadata and qualifying-syllable counts | Need original metadata/source output to verify regeneration |
| Figure 1, Figure 3C–D | Anatomical schematic and histology images | Prepared outside the quantitative analysis scripts |

## Generate Figure 3 inputs from decoded JSONs

```bash
python code/analysis/generate_figure3_inputs_from_json.py /path/to/AFP_lesion_jsons \
  --output outputs/figure3_inputs \
  --pre-start-day -14 --pre-end-day -1 \
  --post-start-day 1 --post-end-day 14 \
  --min-period-phrases 10 --min-period-days 2 --balance-draws 200 --seed 123
```

The input directory contains `AFP_lesion_bird_metadata.json` keyed by bird,
and per-bird `<bird>_decoded_database.json` files (searched recursively).
Each metadata entry supplies lesion group and surgery date; each decoded JSON
supplies recording dates and `syllable_onsets_offsets_ms`. The generator writes
balanced-pair, period-statistics, long-duration, audit and configuration files.
It retains all dated recordings in the long table by default. To reproduce
the windowed v2 long-table behavior, add `--long-start-day -30 --long-end-day 30`;
the ±14-day balanced-pair calculation is unchanged.

## Figure 3 inputs and explicit settings

The primary Q75 plotting script reads:

- Balanced-pair CSV: `animal_id`, `syllable`, `lesion_group_detailed`, `pre_cv`,
  `post_cv`, `delta_cv`. Each row is a qualifying bird/syllable pair.
- Long-duration CSV: `animal_id`, `syllable`, `relative_day`, `phrase_duration_s`
  (accepted aliases are listed in `load_long_csv`). Durations must be in seconds.

The balanced-pair file must already reflect the manuscript's inclusion and
balancing rules: at least 10 phrases and two recording days in each period,
late pre-lesion days −14 through −1, post-lesion days +1 through +14, 200 draws.
The input generator below recreates those inclusion/balancing decisions from
decoded JSONs; the plotting script reads the resulting table.

Example command with manuscript-stated daily settings:

```bash
python code/figure_generation/figure3_q75_phrase_duration.py \
  --pair-metrics /path/to/figure3_balanced_pair_metrics.csv \
  --duration-long-csv /path/to/all_birds_phrase_duration_long.csv \
  --output outputs/figure3_q75 \
  --quantiles 0.75 \
  --late-pre-start -14 --late-pre-end -1 \
  --min-daily-phrases 10 --min-birds-for-summary 3 \
  --rolling-window-days 7 --normalize-mode subtract --seed 123
```

This is a documented command matching the manuscript settings, not a claim
that the published panel was originally generated by this exact command.
Historical defaults remain unchanged (5 daily phrases and 2 birds) to avoid
silently changing older analyses. Confirm panel provenance before rerunning.

Quantile sensitivity uses the same all-qualifying balanced-pair file:

```bash
python code/analysis/quantile_sensitivity_table.py \
  --input /path/to/figure3_balanced_pair_metrics.csv \
  --output outputs/quantile_sensitivity --seed 123
```

Its legacy Word output filename may contain `Supplemental`; use the manuscript
label Extended Data Table 3-2 when naming the final submission file.

## Figure 3E and individual time courses

```bash
python code/figure_generation/figure3_timecourse.py \
  --pair-metrics outputs/figure3_inputs/figure3_balanced_pair_metrics.csv \
  --duration-long-csv outputs/figure3_inputs/figure3_phrase_duration_long.csv \
  --output outputs/figure3_timecourse \
  --min-daily-phrases 10 --min-birds-for-summary 3
```

This supplied UPDATED_v2 implementation uses Q75, median daily syllable CV,
late-pre baseline subtraction, equal bird weighting, and centered 7-day median
smoothing separately before/after lesion. The plotted range is −28 to +28 days.
Bird 17/21 annotation mappings are preserved. The older raw version uses a
5-phrase daily minimum; it is not selected for the current manuscript settings.
Verify real output agreement before replacing any saved figure.

## Acoustic inputs and explicit settings

Cluster-level analysis requires a per-bird NPZ with `embedding_outputs`,
`hdbscan_labels`, `s`, `file_indices` and `file_map`, plus the lesion metadata
workbook used to identify treatment dates. The NPZ already contains UMAP
coordinates; this archive is not the original TweetyBERT/UMAP fitting pipeline.
The wrapper's default export helper now resolves inside this repository.

The following flags express the manuscript-stated BC processing choices:

```bash
python code/analysis/bhattacharyya_cluster_analysis.py \
  --npz-path /path/to/BIRD.npz \
  --metadata-excel-path /path/to/lesion_metadata.xlsx \
  --spectrogram-script code/helpers/pre_post_syllable_spectrograms.py \
  --out-dir outputs/bc_clusters --animal-id BIRD \
  --period-mode early_late_pre_post \
  --bc-analysis-mode run_balanced_full_contiguous \
  --fill-noise-labels-from-nearest-nonnoise \
  --apply-majority-vote-label-smoothing --majority-vote-window-bins 200 \
  --min-runs-per-group 15 --min-balanced-duration-s 10 \
  --min-full-run-duration-ms 100 --min-run-group-fraction 0.80 \
  --umap-density-bins 20 --bc-grid-point-coverage 0.99
```

Confirm the original seed, run cap, early/late splitting method, selected BC
variant and per-file smoothing settings from saved run logs. They are not
recoverable solely from the four bird-level input CSVs. Do not assume that
unconfirmed historical defaults are the manuscript's original settings.

Group plots require the qualifying cluster-level input to contain the final
selected BC variant and duration-filtered clusters:

```bash
python code/figure_generation/figure4_bhattacharyya_q75.py \
  --bc-csv /path/to/final_qualifying_cluster_BC.csv \
  --quantile-selection-csv /path/to/syllable_level_quantile_selection.csv \
  --selection-column selected_Q75 --out-dir outputs/figure4
```

## Annotation and preprocessing

`code/helpers/merge_annotations_from_split_songs.py` combines detection JSONs
and decoded annotation JSONs using the included detection/annotation helpers.
Supplied annotation source snapshots are included under `code/annotation/`.
See `annotation_workflow.md`. Checkpoints, original sampling records and the
original execution environments remain external; analysis-stage verification
is not a raw-annotation pipeline rerun.

## Historical / exploratory scripts

The difference-in-differences, quantile-profile, pooled-selection robustness,
outlier, legacy CV and candidate longevity scripts are retained for context.
Their outputs are not automatically additional submitted results and their
bootstrap/test configurations may differ from the final Table 1 calculation.
Refer to the combined statistics generator for the final interval method.

## Identify the saved balanced-pair input

```bash
python scripts/check_figure3_pair_inputs.py \
  --search-root /path/to/manuscript_analysis /path/to/cutoff_outputs
```

The checker compares each exact-named balanced-pair CSV against all 63 saved
Q60/Q75/Q90 bird-level summaries, including lesion groups and qualifying-syllable
counts. Multiple matching copies can be equivalent. A match does not by itself
validate raw annotations or longitudinal values.

## Included real-data figure example

Run `python scripts/reproduce_analysis_examples.py` to verify all 63 bird
quantiles, reconstruct acoustic Q75 flags from the phrase-duration input,
check both Figure 4D subsets, and regenerate Figure 3E/individual review plots.
The saved Figure 3 input has 441 qualifying bird/syllable pairs and 2,070,655
occurrence rows spanning days −30 through +30. Its saved settings are included
as `examples/figure_inputs/figure3_saved_input_settings.json`, with paths made
relative. For this saved-input configuration, pass `--long-start-day -30
--long-end-day 30` to the JSON generator.

The gzip duration CSV contains `animal_id`, `syllable`, `relative_day`, and
`phrase_duration_s`, retaining every input row. Redundant metadata and local
source paths were removed from this review copy; the original full table is
unchanged. Pandas reads `.csv.gz` directly; no manual decompression is needed.

The Figure 4D saved export repeats each cluster once in a legacy top-variance
subset. Only `set_name=all_clusters` rows are retained in the example (61 unique
bird/syllable pairs). This removes duplicate export rows without changing the
original data, Q75 labels or BC values. The exported cluster data covers only
medial+lateral birds. Full sham/lateral cluster inputs are still external.

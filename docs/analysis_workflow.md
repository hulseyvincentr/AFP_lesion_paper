# AFP lesion manuscript analysis workflow

This document maps the publication-facing analyses and figures to the corresponding scripts in this repository.

## Phrase-duration variability

- `code/figure_generation/figure3_q75_phrase_duration.py`
  - Primary Figure 3 phrase-duration variability analysis.
  - Primary syllable-selection threshold: Q75.
  - Late-pre baseline: days -14 through -1.
  - Daily syllable CV requires at least 5 phrase occurrences per syllable per day.
  - Longitudinal summaries use a centered 7-day rolling window.

- `code/analysis/phrase_duration_difference_in_differences.py`
  - Difference-in-differences analysis comparing post-lesion change with pre-lesion baseline drift.

- `code/analysis/quantile_sensitivity_table.py`
  - Sensitivity analysis across syllable-selection quantile thresholds.

- `code/analysis/phrase_duration_quantile_profile.py`
  - Quantile-profile analysis of phrase-duration variability changes.

- `code/analysis/phrase_duration_robustness_pooled_selection.py`
  - Additional robustness analyses using alternative syllable-selection procedures.

## Acoustic stability

- `code/analysis/bhattacharyya_cluster_analysis.py`
  - Within-bird latent-space stability analysis using the Bhattacharyya coefficient.

- `code/analysis/bhattacharyya_group_summary.py`
  - Bird-level and lesion-group summaries of Bhattacharyya coefficient results.

- `code/figure_generation/figure4_bhattacharyya_q75.py`
  - Figure 4 summaries for all clusters and Q75-selected syllable clusters.

## Annotation and visualization QC

- `code/figure_generation/suppfig2_annotation_qc.py`
  - Supplemental pre/post UMAP and phrase-duration QC used to assess annotation stability after lesion.

- `code/figure_generation/phrase_duration_examples.py`
  - Bird-level pre/post phrase-duration examples.

## Figure 3E

- `code/figure_generation/figure3_panelE_longevity_normalized_sd_cv_v4.py`
  - Candidate Figure 3E implementation retained while the final panel is selected.

## Helper code

Files in `code/helpers/` provide annotation-merging, spectrogram-export, outlier-analysis, and robustness-analysis functionality required by the manuscript-facing scripts.

Input and output paths are supplied through command-line arguments rather than machine-specific paths.

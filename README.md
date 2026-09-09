# AFP Lesion Paper

Analysis and figure-generation code supporting the manuscript on anterior forebrain pathway (AFP) involvement in adult canary song variability and sequencing.

## Repository structure

- `code/analysis/` — statistical and quantitative analyses used for manuscript results
- `code/figure_generation/` — manuscript and supplemental figure-generation scripts
- `code/helpers/` — helper and preprocessing scripts required by the main analyses
- `metadata/` — lightweight metadata files
- `figures/` — finalized or lightweight figure assets
- `docs/` — analysis and reproducibility documentation

## Main analysis scripts

### Phrase-duration variability

- `code/analysis/phrase_duration_quantile_profile.py`
  - Calculates within-bird phrase-duration variability changes across syllables and quantile-based selections.

- `code/analysis/phrase_duration_difference_in_differences.py`
  - Tests early-pre, late-pre, and post-lesion changes using a difference-in-differences framework.

- `code/analysis/quantile_sensitivity_table.py`
  - Generates sensitivity analyses across Q60, Q75, and Q90 syllable-selection thresholds.

### Acoustic stability

- `code/analysis/bhattacharyya_cluster_analysis.py`
  - Calculates within-syllable latent-space overlap using the Bhattacharyya coefficient.

- `code/analysis/bhattacharyya_group_summary.py`
  - Generates bird- and lesion-group summaries of Bhattacharyya coefficient results.

## Figure-generation scripts

- `code/figure_generation/figure3_q75_phrase_duration.py`
  - Current Q75-based phrase-duration variability plots and equal-bird time courses.

- `code/figure_generation/figure4_bhattacharyya_q75.py`
  - Figure 4 Bhattacharyya coefficient summaries for all clusters and Q75-selected clusters.

- `code/figure_generation/phrase_duration_examples.py`
  - Bird-level pre/post phrase-duration example plots.

- `code/figure_generation/suppfig2_annotation_qc.py`
  - Supplemental UMAP and phrase-duration QC plots used to evaluate post-lesion annotation stability.

The current candidate implementation for Figure 3E is retained separately while the final version of that panel is being selected.

## Environment

Install the Python dependencies with:

```bash
pip install -r requirements.txt
```

Core dependencies are NumPy, pandas, Matplotlib, SciPy, seaborn, openpyxl, and python-docx.

## Data availability

Large raw audio files, TweetyBERT `.npz` files, and generated intermediate outputs are not stored directly in this GitHub repository.

Analysis and plotting scripts accept local input and output paths through command-line arguments. Data underlying the manuscript results will be linked here through the associated public data repository when available.

## Reproducibility

Publication-facing scripts are separated from exploratory and superseded development versions so that the analysis code associated with the submitted manuscript can be identified directly.

Input requirements, analysis parameters, and command-line options are documented in the scripts and manuscript Methods.

## Preprint

A previous version of this work is available on bioRxiv:

**Hulsey-Vincent et al. (2026).**
doi: `10.64898/2026.07.11.737998`

## Status

Repository supporting the AFP lesion manuscript in preparation for journal submission.

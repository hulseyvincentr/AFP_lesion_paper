# Figure 4 Bhattacharyya-Coefficient Analysis Provenance

## Purpose

This document records the provenance checks performed for the Bhattacharyya-coefficient (BC) analysis underlying Figure 4 of the AFP lesion manuscript.

The goal of this audit was to verify that the cluster-level BC values used to generate Figure 4C could be traced back to the original per-bird analysis outputs and raw `.npz` inputs.

Figure 4D and the bird-level statistical table were verified separately. This document focuses primarily on the upstream provenance of Figure 4C.

---

## Figure 4C analysis structure

Figure 4C compares Pre versus Post Bhattacharyya coefficients across lesion groups using all qualifying syllable clusters.

For each bird:

1. BC values are calculated separately for qualifying syllable clusters.
2. Each cluster contributes a Pre BC and Post BC value.
3. The median BC across qualifying clusters is calculated separately for Pre and Post.
4. These bird-level values are used for the lesion-group comparison and statistical testing shown in Figure 4C.

The groups represented in Figure 4C are:

- sham saline injection
- lateral lesion only
- pooled medial and lateral lesions

---

## Raw NPZ inputs located

The original analysis `.npz` files for all sham and lateral-only birds represented in Figure 4C were located under:

```text
/Volumes/my_own_SSD/updated_AreaX_outputs/<ANIMAL_ID>/<ANIMAL_ID>.npz
```

### Sham birds

- USA5271
- USA5283
- USA5494
- USA5506

### Lateral-only lesion birds

- R08
- R09
- R10
- USA5336
- USA5347
- USA5483
- USA5499
- USA5510

All 12 expected sham/lateral Figure 4C birds therefore have corresponding raw analysis `.npz` files.

---

## NPZ contents verified

Each of the 12 sham/lateral `.npz` files was inspected.

All contained the fields required by the BC analysis, including:

```text
hdbscan_labels
embedding_outputs
s
```

The NPZ files also contained additional annotation and spectrogram-related fields including:

```text
ground_truth_labels
predictions
hdbscan_colors
ground_truth_colors
original_spectogram
vocalization
file_indices
dataset_indices
file_map
```

For each bird, the first dimension of `hdbscan_labels`, `embedding_outputs`, and `s` was consistent, indicating that cluster labels, embedding coordinates, and spectrogram-derived values were aligned across the analyzed time bins.

---

## USA5347 duplicate NPZ check

Two copies of the USA5347 NPZ were found:

```text
/Volumes/my_own_SSD/updated_AreaX_outputs/USA5347.npz

/Volumes/my_own_SSD/updated_AreaX_outputs/USA5347/USA5347.npz
```

Their SHA-256 hashes were compared and were identical:

```text
1e44d1b0221fb79abf947f05f33e77916742711aa8e0c097056663c7db844372
```

The files also had the same size and modification timestamp.

They are therefore byte-identical copies. The copy within the per-bird directory is used as the canonical path for provenance purposes:

```text
/Volumes/my_own_SSD/updated_AreaX_outputs/USA5347/USA5347.npz
```

---

## Historical Figure 4 BC analysis outputs located

The historical per-bird BC outputs corresponding to the manuscript analysis were located under:

```text
/Volumes/my_own_SSD/updated_AreaX_outputs/
bc_full_contiguous_MAIN_ALL_BIRDS_MIN15_MIN10S_MAJORITY_VOTE_200bin_density20_grid99_title_spacing/
```

This directory contains a separate analysis directory and `*_cluster_bc_summary.csv` for each Figure 4 bird.

The directory name records the major analysis settings associated with this run:

```text
full_contiguous
MIN15
MIN10S
MAJORITY_VOTE
200bin
density20
grid99
```

These are consistent with the analysis settings documented for the manuscript, including:

- full contiguous syllable runs
- minimum 15 runs per period
- minimum 10 seconds of qualifying data per period
- majority-vote/noise handling used by the analysis
- 200-bin smoothing/processing setting
- 20 × 20 BC density grid
- 99% BC grid point coverage

---

## Cluster-level sham and lateral inputs verified

The historical `*_cluster_bc_summary.csv` files were inspected for all sham and lateral-only birds.

Qualifying clusters were identified using the `passes_min_balanced_duration` field.

The number of qualifying clusters matched the previously verified Figure 4C bird-level input exactly.

### Sham

| Bird | Qualifying clusters |
|---|---:|
| USA5271 | 15 |
| USA5283 | 8 |
| USA5494 | 10 |
| USA5506 | 9 |

Total sham qualifying clusters: **42**

### Lateral-only lesion

| Bird | Qualifying clusters |
|---|---:|
| R08 | 8 |
| R09 | 3 |
| R10 | 5 |
| USA5336 | 9 |
| USA5347 | 5 |
| USA5483 | 6 |
| USA5499 | 10 |
| USA5510 | 9 |

Total lateral qualifying clusters: **55**

Total sham + lateral qualifying clusters: **97**

---

## Figure 4C bird-level values reproduced from cluster summaries

For every sham and lateral-only bird, the median Pre and Post BC values calculated from the qualifying historical cluster rows matched the previously verified Figure 4C bird-level input.

### Sham

| Bird | n clusters | Median Pre BC | Median Post BC |
|---|---:|---:|---:|
| USA5271 | 15 | 0.988661152853988 | 0.992450234887740 |
| USA5283 | 8 | 0.985621275292986 | 0.986244945004012 |
| USA5494 | 10 | 0.992708640486135 | 0.988981658262854 |
| USA5506 | 9 | 0.956278541818867 | 0.983308477613885 |

### Lateral-only lesion

| Bird | n clusters | Median Pre BC | Median Post BC |
|---|---:|---:|---:|
| R08 | 8 | 0.979216631632521 | 0.981078599408883 |
| R09 | 3 | 0.893651027816130 | 0.894743162098903 |
| R10 | 5 | 0.916694109991694 | 0.976572147101448 |
| USA5336 | 9 | 0.982033942170812 | 0.980368419836723 |
| USA5347 | 5 | 0.985101865260748 | 0.980561605919849 |
| USA5483 | 6 | 0.979051412668099 | 0.937929349453838 |
| USA5499 | 10 | 0.982714700065382 | 0.944479389187465 |
| USA5510 | 9 | 0.949006306050612 | 0.984428217129088 |

These values match the saved Figure 4C bird-level analysis input.

This verifies the provenance chain:

```text
historical per-cluster BC summaries
        ↓
qualifying cluster filtering
        ↓
within-bird median Pre/Post BC
        ↓
Figure 4C bird-level values
```

---

## BC calculation variant used by Figure 4C

The historical cluster summary files contain several BC variants, including:

```text
bc_pre
bc_post

bc_pre_selected_bins
bc_post_selected_bins

bc_pre_full_contiguous_selected_runs
bc_post_full_contiguous_selected_runs

bc_pre_run_weighted_full_contiguous
bc_post_run_weighted_full_contiguous
```

For the audited sham and lateral birds, `bc_pre` and `bc_post` matched `bc_pre_full_contiguous_selected_runs` and `bc_post_full_contiguous_selected_runs` at the bird-median level.

The run-weighted full-contiguous values differed.

This supports the interpretation that the Figure 4C values correspond to the **full-contiguous selected-run BC analysis**, rather than the run-weighted full-contiguous variant.

---

## Verification status

### Verified

- Raw `.npz` files located for all sham and lateral Figure 4C birds.
- Required NPZ arrays are present.
- Historical manuscript-era BC output directory located.
- Historical analysis directory naming is consistent with the manuscript BC settings.
- Per-bird cluster-level BC summary files located.
- Qualifying cluster counts reproduce the Figure 4C inputs.
- All 97 qualifying sham/lateral clusters are accounted for.
- Within-bird median Pre/Post BC values reproduce the saved Figure 4C bird-level values.
- Figure 4C cluster-level provenance is therefore verified.
- Figure 4D and the bird-level statistical table were verified separately.

### Not yet independently regenerated

A fresh end-to-end rerun from the original `.npz` files through the current BC analysis code has **not yet been performed** as part of this audit.

Therefore, this audit establishes historical analysis provenance:

```text
raw NPZ files located
        ↓
historical BC outputs located
        ↓
historical cluster summaries
        ↓
Figure 4C bird values reproduced
```

but does not yet establish an independent fresh regeneration of each historical cluster-level BC value directly from the NPZ files.

This distinction should be retained when describing the reproducibility status of the analysis.

---

## Summary

The complete sham and lateral cluster-level inputs underlying Figure 4C were located and verified.

The historical analysis outputs contain the expected qualifying clusters and reproduce the saved Figure 4C bird-level values exactly after the same within-bird median aggregation.

The remaining optional reproducibility check is a fresh NPZ-to-BC regeneration using the documented manuscript analysis settings.

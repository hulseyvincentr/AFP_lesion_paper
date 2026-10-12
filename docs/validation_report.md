# Verification performed 2026-10-12

Base repository commit: c9c713e.

## Passed

- Syntax parsing of every included Python source file.
- `--help` execution for all 21 CLI-enabled analysis/figure/helper scripts.
- Dynamic loading of the bundled acoustic export and spectrogram helpers.
- Acoustic wrapper/export-helper keyword-interface compatibility.
- Recalculation of all 14 statistics-table rows with 200,000 bootstrap
  resamples and seed 123, using the four included study CSVs.
- Agreement with manuscript reference values for row order, sample sizes,
  effects, confidence bounds, test statistics, raw p-values and adjusted
  p-values (absolute tolerance 1e-10).
- ZIP integrity and SHA-256 file checksums.
- Statistics-table reproduction after extracting the ZIP into an independent
  temporary folder.
- Scan of bundled text for machine-specific absolute home/SSD paths, and
  manual check for known author/user-name remnants in code and data.

Verification environment: Linux, Python 3.12. Package versions are recorded
in `requirements-review-tested.txt`. The Mac Studio hardware/OS statement is
user-reported research context, not a description of this verification host.

## Not performed

- Full preprocessing or annotation from raw audio.
- Decoder training or model checkpoint validation.
- Regeneration of the original balanced-pair input.
- Per-cluster BC rerun using the actual NPZ/metadata files.
- Visual matching of all manuscript figure panels against regenerated plots.
- Verification of the original Mac software environment.

See `submission_readiness.md` for the inputs and provenance still needed.
Packaging changes repair paths, CLI help and documentation; they do not
alter the primary statistical calculations or the historical figure defaults.

## Supplied-source follow-up

- Added the all-days Figure 3 input generator and the UPDATED_v2 time-course
  script from the supplied source archive; both CLI help commands pass.
- AST comparison confirms that windowed v2 and all-days generators use identical
  balancing and per-pair random-seed functions.
- A synthetic six-bird JSON fixture ran through the generator and the updated
  time-course CLI. Verified inclusion/exclusion at the 10-phrase/two-day
  thresholds, 24 qualifying bird/syllable pairs, balanced CV calculation,
  retention of recordings outside ±30 days, and generation of the time-course
  CSVs and plots. This is an integration check, not actual study reproduction.
- Added a balanced-pair candidate checker. Its comparison accepts exact summary
  agreement and rejects changed values, counts or missing birds.
- Excluded the superseded statistics generator from the ZIP builder.
- The supplied Figure 4 runner uses legacy 20-run/2-second/top-30% settings;
  it is excluded as a primary entry point. The supplied cluster wrapper otherwise
  matches the bundled wrapper apart from portability fixes.

## Actual saved-input verification

- Saved configuration: ±14-day analysis windows, ≥10 phrases and ≥2 days per
  period, 200 balancing draws, seed 123; long table spans days −30 through +30.
- All 63 quantile values and qualifying-syllable counts match the manuscript.
- Retained all 2,070,655 duration rows in a four-column gzip review copy.
- Ran the updated time-course CLI using actual study inputs: 9 medial+lateral,
  8 lateral-only and 4 sham birds; Birds 17 and 21 found; review plots generated.
- Selected 61 unique `all_clusters` acoustic rows rather than double-counting
  their repeated legacy subset export. Their Q75 flags agree with the phrase
  input, and both paired subsets match Figure 4D for all eight birds.
- Removed source-path columns from the review inputs; retained the original
  uploaded tables unchanged.

No raw JSON/NPZ pipeline rerun or visual identity check against the final TIFFs
has been claimed. Full sham/lateral cluster-level BC inputs remain external.

## Annotation-source inclusion

- Included 27 backbone/decoder/UMAP/spectrogram/detector source files and their
  workflow helpers. All parse successfully.
- Static checks confirm final attention readout, 196→128→64→C classifier and
  GELU activations. Training source defaults to an unfrozen backbone.
- Included the two supplied decoder configs (28/30 classes) and pretraining
  config, with pretraining data paths made portable. Freeze flags are absent
  from the saved configs and actual historical training remains unverified.
- Corrected the detector subprocess path/interpreter and removed automatic
  cloning because source is bundled. Algorithms and weights were not changed.
- Annotation dependencies, source snapshots, model-access gaps and missing
  publication-license metadata are documented separately.
- Torch/UMAP runtime execution, actual checkpoints and raw audio were not
  available for annotation inference/training validation in this environment.

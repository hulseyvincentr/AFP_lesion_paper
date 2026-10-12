# AFP lesion manuscript: analysis code for review

This archive contains Python analysis and figure-generation scripts, helper
modules, dependency specifications, and the bird-level inputs needed to
regenerate Table 1. These inputs are actual study data, not synthetic examples.

## Scope and entry point

Start with the statistics-table reproduction command below. It runs with the
four included input CSVs and checks all 14 rows against the manuscript values.
Figure 3E can also be regenerated with `python scripts/reproduce_analysis_examples.py`.
The included compressed duration table retains all 2,070,655 rows and the four
columns required by the plotter. The larger raw-annotation/embedding analyses
require external JSONs, NPZs, lesion metadata and color mappings.

The acoustic example contains 61 unique medial+lateral clusters sufficient
to check both Figure 4D subsets; it does not include the other groups’
cluster-level inputs for a full Figure 4C rerun.

The archive now includes the supplied TweetyBERT/MLP training and inference
source and detector inference source under `code/annotation/`. See
`docs/annotation_workflow.md` for their provenance, additional dependencies
and required external artifacts. Raw audio and model weights are not included.
The Figure 3 JSON input generator and the updated daily time-course script
are included. See `docs/submission_readiness.md` for outstanding provenance checks before
finalizing the complete code submission. This archive has not been validated
as an end-to-end reproduction from raw recordings.

## Installation

Run commands from this folder in a dedicated Python environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python scripts/reproduce_statistics_table.py
```

`requirements-review-tested.txt` records the Python-package versions used for
verification in Linux/Python 3.12. It is not the original Mac environment. `requirements-annotation.txt` separately
lists packages identified from annotation source; that environment has not been
runtime-validated here.
The manuscript reports an Apple Mac Studio, Apple M4 Max, macOS 26.6.2 for
statistical analyses and table generation. Training/inference hardware and
the original software versions need separate documentation if applicable.

## Statistics outputs and interpretation

Outputs appear in `outputs/statistics_table_check/`:

- `eNeuro_statistics_table.docx`: one combined statistics table plus its legend.
- `statistics_full_precision.csv`: unrounded effects, intervals and tests.
- `statistics_row_references.csv`: a–n manuscript cross-references.

Rows a–c cover Q75, d–f Q60, g–i Q90, j–l Figure 4C, and m–n Figure 4D.
Bootstrap intervals use 200,000 resamples, seed 123 and birds as independent
resampling units. Phrase-duration effects are between-group differences in
means of bird-level quantiles; acoustic effects are medians of paired bird
changes. The intervals are pointwise and are not corrected for multiplicity
or inversions of the hypothesis tests. Holm correction applies only to the
specified p-value families. Small samples limit interval accuracy.

## Other analyses

See `docs/analysis_workflow.md` for the manuscript-to-script map, explicit
parameters and external input requirements. Use `python SCRIPT --help` to
inspect a script's arguments. Older robustness scripts are retained as
development context and are not substitutes for the primary Q75 analyses.
Historical filenames/output filenames may still contain `suppfig` or
`Supplemental`; the manuscript uses the Extended Data mapping described in
the workflow document.

## Archive contents

The ZIP excludes Git history, virtual environments, caches, macOS metadata,
raw recordings, large embedding files, generated figures and the public
README's author/preprint information. `MANIFEST_SHA256.json` records file
checksums. Rebuild with `python scripts/build_eneuro_code_zip.py`.

Third-party packages and externally supplied data retain their original
terms. No new software license is granted by this packaging step.

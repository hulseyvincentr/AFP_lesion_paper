# Code-submission readiness

## Prepared and checked

- The combined statistics generator matches the manuscript's 14-row table.
- Four real bird-level input CSVs and reference results are included.
- A reproduction command verifies effects, CIs, test statistics and p-values.
- Python CLI help-formatting errors were corrected.
- The BC wrapper now finds its bundled export helper by repository-relative path.
- Personal-name comments and executable SSD example paths were removed.
- The review README excludes public author/preprint information.
- The archive builder excludes Git history, caches, environments and raw data.
- Dependency versions used for the verification environment are distinguished
  from the original research environment.

## Confirm before calling the complete manuscript code package final

1. The supplied input generator has now been inspected and included as
   `code/analysis/generate_figure3_inputs_from_json.py`. Its balancing and
   per-pair RNG functions are identical to the supplied windowed v2 generator.
   It implements 10 phrases/two days per period, 200 draws and ±14-day windows.
   The supplied saved balanced-pair CSV matches all 63 bird quantiles and
   syllable counts. Its configuration confirms the stated settings. Regeneration
   from the original decoded JSONs remains a separate provenance check.
2. The supplied updated Figure 3E script is included as
   `code/figure_generation/figure3_timecourse.py`. It implements the stated
   10-phrase daily minimum, 3-bird group minimum, Q75 and 7-day centered
   smoothing separately before/after lesion. It displays days −28 through +28.
   It successfully regenerates plots with the actual supplied occurrence data
   (21 birds; both example birds present). Compare with the final TIFF panel
   for visual provenance; raw-annotation reproduction is separate.
3. The supplied TweetyBERT/MLP training/inference and detector inference sources
   are now bundled and statically checked. Original training commits/flags,
   model weights, remaining bird configs, sampling commands and original
   annotation hardware/software need their actual run records. Two supplied
   decoder configs do not record backbone freezing. Source matching the
   architecture is not evidence that the original training run used its default.
4. Analysis-stage Figure 3 duration data and paired/cluster examples are now
   included. Make the remaining raw-annotation/embedding metadata accessible and
   test at least one bird's analysis with those inputs. The complete audio
   archive need not be copied into this small code ZIP.
5. Confirm the final per-cluster BC input and original run settings. The
   supplied `run_figure4_bc_from_raw.py` is a legacy runner (20 runs, 2 s and
   top-30% selection); it is not included as a current primary entry point. The
   manuscript specifies full contiguous runs, ≥15 runs/period, ≥10 s/period,
   noise filling, 200-bin smoothing, 20×20 bins and 99% grid coverage. Historical
   defaults differ. The included bird-level CSVs reproduce the table; they
   do not prove the complete upstream command has been reproduced.
6. Record the original Python/package versions and any additional training
   hardware/OS. The tested dependency file here describes a verification
   environment rather than the original one.

## Submission instructions checked on 2026-10-12

The eNeuro Preparing a Manuscript page describes a single code ZIP uploaded
as Multimedia/Extended Data, a Code Accessibility subsection in Methods,
computer/OS details and a legend labeled Extended Data 1 at the manuscript's
end. The Information for Authors page instead names Online Code for Review
Only as the upload type. Use the dedicated code category if it is offered by
the current transfer portal; otherwise use Multimedia/Extended Data.

Sources:
- https://www.eneuro.org/content/preparing-manuscript
- https://www.eneuro.org/content/information-authors
- https://www.eneuro.org/content/general-information

Code is labeled Extended Data 1, distinct from the figure-supporting
Figure 2-1, Figure 3-1, Table 3-1 and Table 3-2 files. Add the corresponding
manuscript citation and legend after the final archive scope is settled.

Suggested legend for the analysis archive only:

Extended Data 1. Analysis and figure-generation code for the AFP lesion study.
The archive includes Python scripts, supporting helper modules, installation
instructions, a manuscript-to-script map, and bird-level input data and a
verification command for reproducing the statistics table. Larger annotation,
embedding and metadata inputs, and model checkpoints are described
in the code and data accessibility statements. Annotation source snapshots
and example model configurations are included, with their verification limits
documented in the README.

Do not claim raw-data or model-checkpoint reproduction: the annotation sources
have received static checks, whereas the statistics/figure examples were
executed with the included analysis-stage study data.

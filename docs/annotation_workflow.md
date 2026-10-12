# Annotation source and model access

## Included source

`code/annotation/tweety_bert/` contains the supplied TweetyBERT backbone,
decoder training, inference, spectrogram preparation, UMAP/clustering and
necessary workflow helpers. The separately cloned song detector is bundled
under `song_detector/src/` so review does not require an automatic Git clone.

Source snapshots:

- TweetyBERT local source commit: `9ffed98fa5d5da0f5007865bddb354e008b1d70a`.
- Song-detector source commit: `274ce3175c8d88ce4b3301b0bc38eb8923af232c`.

These identify the provided source snapshots. They are not proven to be the
exact historical commits that produced all manuscript annotations. The current
snapshot includes fine-tuning code committed after earlier versions that used
frozen probes, so original run provenance still matters.

The decoder reads the final transformer block's 196-dimensional attention
output and applies 196→128→64→C with GELU activations. Training defaults to an
unfrozen backbone; `--freeze_backbone` opts into freezing. The saved decoder
configs do not record this flag. Inference freezes the network for prediction;
that does not establish whether its weights were frozen during training.

## Configurations included for inspection

`examples/model_configs/` contains two provided decoder configs:

- USA5288: 28 output classes.
- USA5337: 30 output classes.

Both point to the same pretrained backbone. Its example config specifies
196 dimensions, 4 transformer layers, 4 attention heads, 1,000-bin context,
batch size 42, learning rate 0.0003 and up to 100,000 pretraining steps.
Pretraining data paths in the review copy are relative placeholders.

These are source/config examples, not confirmation that the current model
files generated the manuscript annotations. Configurations for the other 19
AFP birds, the actual model weights and original run logs were not provided.

## Installation and entry points

Use a separate annotation environment. `requirements-annotation.txt` lists
identified packages without claiming historical versions. The analysis-table
verification environment is distinct. PyTorch/UMAP training and inference
have not been run in the preparation environment.

From the archive root:

```bash
python scripts/check_annotation_source.py
```

To inspect the operational CLI in an environment with annotation dependencies:

```bash
cd code/annotation/tweety_bert
python detect_song.py --help
python decoding.py --help
python run_inference.py --help
python src/decoder.py --help
python song_detector/src/inference.py --help
```

`detect_song.py` invokes the bundled detector and merges song-boundary JSONs.
`decoding.py` orchestrates spectrogram preparation, UMAP/HDBSCAN pseudolabels,
and decoder training. `run_inference.py` invokes the trained per-bird decoder
to produce syllable annotations. Paths and sampling settings must be supplied
for the intended recordings; the default sampling settings are not asserted
to be the exact pre/post-balanced manuscript command.

## Required external model/data artifacts

Before executing annotation, provide:

- The original pretrained experiment directory: `config.json` and the
  checkpoint files expected by `src/utils.py`.
- Per-bird decoder directories with `decoder_state/decoder_config.json` and
  `decoder_state/decoder_weights.pth`.
- Detector model directory containing `config.json` and `weights.pth`.
- The intended audio, detection inputs and original train/test sampling records.

The standard source uses `experiments/` and `files/` relative to the annotation
project root. Example configs can be copied to those locations after the
matching weights are obtained. They are not runnable checkpoints by themselves.
The authors must document review access and the publication repository for
these artifacts. No accession number or checkpoint download has been invented.

Training entry points reuse/delete some output directories in their original
implementation. Run them in a fresh working copy with disposable output
locations, keeping the original experiment directories intact.

## Packaging changes and attribution

Source algorithms were preserved. The inference subprocess now uses the active
Python interpreter and the bundled detector path. `detect_song.py` expects the
bundled source instead of automatically cloning a remote repository. Original
machine paths were excluded with obsolete shell examples. The source credits
and third-party reference links embedded in the included code are retained.

No LICENSE file was present in the provided TweetyBERT snapshot or at the
checked detector LICENSE path. This packaging step grants no new software
license. The source is included for review; publication licensing should be
settled with the code's authors and existing third-party terms preserved.

#!/usr/bin/env python3
"""Statically check bundled annotation source without loading model weights."""
import ast
from pathlib import Path


def main():
    root = Path(__file__).resolve().parents[1]
    source = root / "code/annotation/tweety_bert"
    files = sorted(source.rglob("*.py"))
    for path in files:
        ast.parse(path.read_text(), filename=str(path))
    decoder = (source / "src/decoder.py").read_text()
    classifier = (source / "src/linear_probe.py").read_text()
    assert 'layer_id="attention_output"' in decoder
    assert "TweetyBERT_readout_dims=196" in decoder
    assert "freeze_layers=False" in decoder
    for expression in ["nn.Linear(TweetyBERT_readout_dims, 128)", "nn.Linear(128, 64)", "nn.Linear(64, self.logits_dim)"]:
        assert expression in classifier, expression
    assert classifier.count("nn.GELU()") >= 2
    assert (source / "song_detector/src/inference.py").is_file()
    assert (source / "scripts/copy_files_from_wavdir_to_multiple_event_dirs.py").is_file()
    assert (source / "scripts/merge_output_label_jsons.py").is_file()
    print(f"PASS: {len(files)} annotation sources parse; decoder architecture/readout and bundled helper paths checked.")
    print("This is a static source check; it does not execute training, inference or model checkpoints.")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Build a review ZIP containing code, neutral documentation and statistics inputs."""
import argparse
import ast
import gzip
import hashlib
import json
from pathlib import Path
import re
import zipfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("outputs/ExtendedData1_AFP_code_review.zip"))
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    sources = {}
    for directory in ["code", "scripts"]:
        for path in sorted((root / directory).rglob("*.py")):
            if path.name == "make_eneuro_statistics_table.py":
                continue  # Superseded generator retained locally, excluded from review ZIP.
            sources[path.relative_to(root).as_posix()] = path.read_bytes()
    for directory in ["docs", "examples"]:
        for path in sorted((root / directory).rglob("*")):
            if path.is_file() and path.suffix in {".md", ".csv", ".txt", ".json", ".gz"}:
                sources[path.relative_to(root).as_posix()] = path.read_bytes()
    for name in ["requirements.txt", "requirements-review-tested.txt", "requirements-annotation.txt"]:
        sources[name] = (root / name).read_bytes()
    # The public repository README contains preprint/author information.
    sources["README.md"] = (root / "docs/code_review_README.md").read_bytes()
    for name, data in sources.items():
        text = (gzip.decompress(data) if name.endswith(".gz") else data).decode("utf-8")
        if name.endswith(".py"):
            ast.parse(text, filename=name)
        if re.search(r"/(?:Users|Volumes|home|media)/", text):
            raise RuntimeError(f"Machine-specific absolute path found in {name}")
    manifest = {name: hashlib.sha256(data).hexdigest() for name, data in sorted(sources.items())}
    sources["MANIFEST_SHA256.json"] = (json.dumps(manifest, indent=2) + "\n").encode()
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(sources.items()):
            info = zipfile.ZipInfo("AFP_code/" + name, date_time=(2026, 10, 12, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
    if output.stat().st_size > 20_000_000:
        raise RuntimeError("ZIP exceeds the 20 MB Extended Data limit.")
    with zipfile.ZipFile(output) as archive:
        if archive.testzip() is not None:
            raise RuntimeError("ZIP integrity check failed.")
    print(f"Created {output} ({output.stat().st_size:,} bytes; {len(sources)} files).")
    print("Check docs/submission_readiness.md before uploading; ZIP integrity is not full pipeline validation.")


if __name__ == "__main__":
    main()

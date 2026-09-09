#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Build Illustrator-ready Supplemental Figure 2 QC panels for AFP lesion birds.

For each bird, this script generates ONLY three PNGs:
    1) <bird>_phrase_duration_violins.png
    2) <bird>_pre_post_umap.png
    3) <bird>_cluster_centroids.png

The figure files are deliberately clean for assembly in Illustrator:
    - no plot titles
    - UMAPs have no x/y labels, ticks, or tick labels
    - each UMAP panel is square
    - the two UMAP panels together have the same physical height as the
      phrase-duration violin plot
    - the phrase-duration plot has no legend and no x tick labels
    - violin bodies are made prominent, with smaller/fainter raw points
    - whitespace is minimized without bbox_inches='tight', so the UMAP
      canvases remain identical in pixel dimensions across birds

A single shared phrase-period legend is written once to:
    <output-root>/phrase_duration_period_legend.png

Output organization:
    SuppFig2_QC_violins/
        M+L/
            pngs/
            csvs/
        L-only/
            pngs/
            csvs/
        sham saline/
            pngs/
            csvs/
        phrase_duration_period_legend.png
        suppfig2_qc_run_summary.csv

Data inputs:
    - bird-level <bird>.npz files under updated_AreaX_outputs/<bird>/
    - <bird>_decoded_database.json
    - <bird>_song_detection.json
    - fixed_label_colors_50.json
    - AFP_lesion_bird_metadata.json

The phrase-duration extraction uses the existing
merge_annotations_from_split_songs.build_decoded_with_split_labels helper,
so run this script from the syntax_analysis environment/repository where that
module is available.
"""

from __future__ import annotations

from pathlib import Path
import sys

_HELPERS_DIR = Path(__file__).resolve().parents[1] / "helpers"
if str(_HELPERS_DIR) not in sys.path:
    sys.path.insert(0, str(_HELPERS_DIR))
import argparse
import ast
import gc
import json
import math
import re
import traceback
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import colors as mcolors
from matplotlib.lines import Line2D
from matplotlib.ticker import FuncFormatter

try:
    from merge_annotations_from_split_songs import build_decoded_with_split_labels
except Exception as exc:
    build_decoded_with_split_labels = None
    _MERGE_IMPORT_ERROR = exc


# -----------------------------------------------------------------------------
# Defaults
# -----------------------------------------------------------------------------
DEFAULT_ROOT = None
DEFAULT_METADATA = None
DEFAULT_COLORS = None
DEFAULT_OUTPUT = Path("outputs") / "suppfig2_qc"

# All three bird-level figures share this physical height.
PANEL_HEIGHT_IN = 5.0
UMAP_DPI = 600
VIOLIN_DPI = 600

POINT_SIZE = 2.0
POINT_ALPHA = 0.55
ROBUST_CROP_PERCENT = 99.0
NOISE_LABEL = -1
SHOW_NOISE = True

MIN_PRE_POINTS_FOR_CENTROID = 20
MIN_POST_POINTS_FOR_CENTROID = 20

# Violin appearance. These are intentionally more visible than the earlier plot.
VIOLIN_ALPHA = 0.78
VIOLIN_WIDTH = 0.19
RAW_POINT_ALPHA = 0.18
RAW_POINT_SIZE = 3.0
TAIL_PERCENTILE = 95.0
TAIL_POINT_ALPHA = 0.62
TAIL_POINT_SIZE = 7.0
MEDIAN_MARKER_SIZE = 38

PERIOD_ORDER = ["early pre-lesion", "late pre-lesion", "post-lesion"]
PERIOD_MARKERS = {
    "early pre-lesion": "o",
    "late pre-lesion": "s",
    "post-lesion": "X",
}
PERIOD_OFFSETS = {
    "early pre-lesion": -0.23,
    "late pre-lesion": 0.00,
    "post-lesion": 0.23,
}

_SERIAL_RE = re.compile(r"_(\d{5}(?:\.\d+)?)_")
_BIRD_RE = re.compile(r"(?:USA\d+|R\d+)", re.IGNORECASE)


# -----------------------------------------------------------------------------
# General helpers
# -----------------------------------------------------------------------------
def seconds_formatter(x, _pos):
    val = x / 1000.0
    if abs(val - round(val)) < 1e-9:
        return str(int(round(val)))
    return f"{val:g}"


def safe_text(v) -> str:
    if v is None:
        return ""
    return str(v).strip()


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def classify_lesion_group(info: dict) -> Optional[str]:
    """Map the metadata JSON onto the three requested Supplemental Fig. groups."""
    if not isinstance(info, dict):
        return None

    text_fields = [
        safe_text(info.get("lesion_group")),
        safe_text(info.get("lesion_group_detailed")),
        safe_text(info.get("lesion_extent_class")),
        safe_text(info.get("lesion_hit_type")),
    ]
    text = " | ".join(text_fields).lower()

    if "sham" in text:
        return "sham saline"

    ml_tokens = (
        "medial+lateral",
        "medial + lateral",
        "medial and lateral",
        "medial/lateral",
        "m+l",
    )
    if any(tok in text for tok in ml_tokens):
        return "M+L"

    medial = safe_text(info.get("medial_area_x_hit_type")).lower()
    lateral = safe_text(info.get("lateral_area_x_hit_type")).lower()

    # In this metadata, "bilateral" means that region was hit, while "miss"
    # means it was spared. This explicitly fixes the lateral-only issue from
    # the earlier text-search classifier.
    medial_hit = any(tok in medial for tok in ("bilateral", "hit", "partial", "complete"))
    lateral_hit = any(tok in lateral for tok in ("bilateral", "unilateral", "hit", "partial", "complete"))
    medial_miss = any(tok in medial for tok in ("miss", "absent", "none"))

    if medial_hit and lateral_hit:
        return "M+L"
    if medial_miss and lateral_hit:
        return "L-only"

    # Explicit lateral-only text labels, if present.
    if any(tok in text for tok in (
        "lateral only",
        "lateral-only",
        "lateral_only",
        "lateral lesion only",
    )):
        return "L-only"

    return None


def lesion_date(info: dict) -> pd.Timestamp:
    raw = info.get("lesion_surgery_date")
    dt = pd.to_datetime(raw, errors="coerce")
    if pd.isna(dt):
        raise ValueError(f"Invalid/missing lesion_surgery_date: {raw!r}")
    return pd.Timestamp(dt).normalize()


def discover_birds(root: Path) -> Dict[str, Path]:
    found: Dict[str, Path] = {}
    if not root.exists():
        raise FileNotFoundError(f"Input root not found: {root}")

    for folder in sorted(root.iterdir()):
        if not folder.is_dir():
            continue
        bird = folder.name
        if not _BIRD_RE.fullmatch(bird):
            continue
        preferred = folder / f"{bird}.npz"
        if preferred.exists():
            found[bird] = preferred
            continue
        direct = sorted(p for p in folder.glob("*.npz") if not p.name.startswith("._"))
        if len(direct) == 1:
            found[bird] = direct[0]
    return found


def find_one(root: Path, pattern: str) -> Optional[Path]:
    candidates = [p for p in root.rglob(pattern) if p.is_file() and not p.name.startswith("._")]
    return sorted(candidates)[0] if candidates else None


# -----------------------------------------------------------------------------
# UMAP helpers
# -----------------------------------------------------------------------------
def unpack_file_map_value(mapped_value) -> str:
    if isinstance(mapped_value, str):
        return mapped_value
    if isinstance(mapped_value, np.ndarray):
        if mapped_value.size == 0:
            raise ValueError("Empty file_map array value")
        return str(mapped_value.flat[0])
    if isinstance(mapped_value, (tuple, list)):
        if not mapped_value:
            raise ValueError("Empty file_map sequence value")
        return str(mapped_value[0])
    return str(mapped_value)


def serial_date_from_filename(filename: str) -> pd.Timestamp:
    name = Path(filename).name
    m = _SERIAL_RE.search(name)
    if m is None:
        raise ValueError(f"Could not extract serial date from filename: {name}")
    serial = float(m.group(1))
    return (pd.Timestamp("1899-12-30") + pd.to_timedelta(serial, unit="D")).normalize()


def build_point_dates(file_indices, file_map) -> pd.DatetimeIndex:
    date_by_idx = {}
    for idx, value in file_map.items():
        date_by_idx[int(idx)] = serial_date_from_filename(unpack_file_map_value(value))
    return pd.DatetimeIndex(pd.to_datetime([date_by_idx[int(i)] for i in file_indices]))


def load_fixed_colors(path: Path) -> Dict[str, str]:
    raw = load_json(path)
    if not isinstance(raw, dict):
        raise ValueError(f"Color JSON must contain a dictionary: {path}")
    return {str(k): str(v) for k, v in raw.items()}


def build_color_map(labels, fixed_colors: Dict[str, str]) -> Dict[int, str]:
    out: Dict[int, str] = {}
    for label in np.sort(np.unique(labels)):
        label = int(label)
        if label == NOISE_LABEL:
            out[label] = "0.75"
        else:
            key = str(label)
            if key not in fixed_colors:
                raise KeyError(f"Label {label} missing from fixed color JSON")
            out[label] = fixed_colors[key]
    return out


def robust_axis_limits(coords: np.ndarray, percent: float = ROBUST_CROP_PERCENT):
    tail = (100.0 - percent) / 2.0
    xlo, xhi = np.percentile(coords[:, 0], [tail, 100.0 - tail])
    ylo, yhi = np.percentile(coords[:, 1], [tail, 100.0 - tail])
    xspan = max(float(xhi - xlo), 1e-9)
    yspan = max(float(yhi - ylo), 1e-9)
    return (
        (float(xlo - 0.04 * xspan), float(xhi + 0.04 * xspan)),
        (float(ylo - 0.04 * yspan), float(yhi + 0.04 * yspan)),
    )


def square_limits(xlim, ylim):
    xc = 0.5 * (xlim[0] + xlim[1])
    yc = 0.5 * (ylim[0] + ylim[1])
    span = max(xlim[1] - xlim[0], ylim[1] - ylim[0])
    return (xc - span / 2.0, xc + span / 2.0), (yc - span / 2.0, yc + span / 2.0)


def clean_umap_axis(ax, xlim, ylim):
    xlim, ylim = square_limits(xlim, ylim)
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    ax.set_aspect("equal", adjustable="box")
    ax.set_box_aspect(1)
    ax.set_xlabel("")
    ax.set_ylabel("")
    ax.set_xticks([])
    ax.set_yticks([])
    ax.tick_params(left=False, bottom=False, labelleft=False, labelbottom=False)
    for spine in ax.spines.values():
        spine.set_visible(False)


def draw_colored_points(ax, coords, labels, mask, color_map, alpha=POINT_ALPHA):
    xy = coords[mask]
    labs = labels[mask]
    for label in np.unique(labs):
        label = int(label)
        if label == NOISE_LABEL and not SHOW_NOISE:
            continue
        this = labs == label
        a = 0.12 if label == NOISE_LABEL else alpha
        ax.scatter(
            xy[this, 0], xy[this, 1],
            s=POINT_SIZE,
            c=[color_map[label]],
            alpha=a,
            linewidths=0,
            rasterized=True,
        )


def cluster_shift_summary(coords, labels, pre_mask, post_mask) -> pd.DataFrame:
    rows = []
    for label in np.sort(np.unique(labels)):
        label = int(label)
        if label == NOISE_LABEL:
            continue
        pre_xy = coords[pre_mask & (labels == label)]
        post_xy = coords[post_mask & (labels == label)]
        if len(pre_xy) == 0 or len(post_xy) == 0:
            continue
        pre_cent = pre_xy.mean(axis=0)
        post_cent = post_xy.mean(axis=0)
        pre_radius = np.mean(np.linalg.norm(pre_xy - pre_cent, axis=1))
        post_radius = np.mean(np.linalg.norm(post_xy - post_cent, axis=1))
        rows.append({
            "cluster": label,
            "n_pre": len(pre_xy),
            "n_post": len(post_xy),
            "pre_centroid_x": pre_cent[0],
            "pre_centroid_y": pre_cent[1],
            "post_centroid_x": post_cent[0],
            "post_centroid_y": post_cent[1],
            "centroid_displacement": float(np.linalg.norm(post_cent - pre_cent)),
            "pre_mean_radius": float(pre_radius),
            "post_mean_radius": float(post_radius),
            "spread_ratio_post_over_pre": float(post_radius / pre_radius) if pre_radius > 0 else np.nan,
        })
    return pd.DataFrame(rows)


def save_pre_post_umap(
    bird: str,
    png_path: Path,
    coords,
    labels,
    pre_mask,
    post_mask,
    color_map,
    xlim,
    ylim,
):
    # Exactly 2 square UMAP panels wide by 1 panel high.
    fig, axes = plt.subplots(
        1, 2,
        figsize=(2 * PANEL_HEIGHT_IN, PANEL_HEIGHT_IN)
    )

    draw_colored_points(axes[0], coords, labels, pre_mask, color_map)
    draw_colored_points(axes[1], coords, labels, post_mask, color_map)

    for ax in axes:
        clean_umap_axis(ax, xlim, ylim)

    # Minimal whitespace, but leave just enough room so the divider renders cleanly.
    fig.subplots_adjust(
        left=0.002,
        right=0.998,
        bottom=0.002,
        top=0.998,
        wspace=0.012,
    )

    # Add a black divider line between pre and post panels.
    pos0 = axes[0].get_position()
    pos1 = axes[1].get_position()
    x_sep = 0.5 * (pos0.x1 + pos1.x0)
    y0 = min(pos0.y0, pos1.y0)
    y1 = max(pos0.y1, pos1.y1)

    fig.add_artist(
        Line2D(
            [x_sep, x_sep],
            [y0, y1],
            transform=fig.transFigure,
            color="black",
            linewidth=0.8,
        )
    )

    fig.savefig(
        png_path,
        dpi=UMAP_DPI,
        facecolor="white",
        bbox_inches=None,
        pad_inches=0,
    )
    plt.close(fig)

def save_centroid_umap(
    png_path: Path,
    coords,
    color_map,
    summary: pd.DataFrame,
    xlim,
    ylim,
):
    fig, ax = plt.subplots(figsize=(PANEL_HEIGHT_IN, PANEL_HEIGHT_IN))

    ax.scatter(
        coords[:, 0], coords[:, 1],
        s=1.0, c="0.87", alpha=0.10,
        linewidths=0, rasterized=True, zorder=1,
    )

    for _, row in summary.iterrows():
        if row["n_pre"] < MIN_PRE_POINTS_FOR_CENTROID or row["n_post"] < MIN_POST_POINTS_FOR_CENTROID:
            continue
        label = int(row["cluster"])
        color = color_map[label]
        ax.scatter(
            row["pre_centroid_x"], row["pre_centroid_y"],
            s=78, marker="o", facecolors="white", edgecolors=[color],
            linewidths=1.6, zorder=5,
        )
        ax.scatter(
            row["post_centroid_x"], row["post_centroid_y"],
            s=34, marker="s", c=[color], edgecolors="black",
            linewidths=0.45, zorder=6,
        )

    clean_umap_axis(ax, xlim, ylim)

    # Keep the centroid key INSIDE the axes so it does not create exterior whitespace.
    handles = [
        Line2D([0], [0], marker="o", linestyle="None", markerfacecolor="white",
               markeredgecolor="0.25", markeredgewidth=1.5, markersize=7,
               label="pre-lesion centroid"),
        Line2D([0], [0], marker="s", linestyle="None", markerfacecolor="0.25",
               markeredgecolor="black", markeredgewidth=0.5, markersize=5,
               label="post-lesion centroid"),
    ]
    ax.legend(handles=handles, frameon=False, loc="upper right", fontsize=8,
              handletextpad=0.4, borderaxespad=0.2)

    fig.subplots_adjust(left=0.002, right=0.998, bottom=0.002, top=0.998)
    fig.savefig(png_path, dpi=UMAP_DPI, facecolor="white", bbox_inches=None, pad_inches=0)
    plt.close(fig)


# -----------------------------------------------------------------------------
# Phrase-duration helpers
# -----------------------------------------------------------------------------
def maybe_parse_dict(obj):
    if isinstance(obj, dict):
        return obj
    if isinstance(obj, str):
        for parser in (json.loads, ast.literal_eval):
            try:
                v = parser(obj)
                if isinstance(v, dict):
                    return v
            except Exception:
                pass
    return None


def choose_datetime_series(df: pd.DataFrame) -> pd.Series:
    dt = df.get("Recording DateTime", pd.Series([pd.NaT] * len(df), index=df.index)).copy()
    for cand in ("recording_datetime", "creation_date"):
        if cand in df.columns:
            need = dt.isna()
            if need.any():
                dt.loc[need] = pd.to_datetime(df.loc[need, cand], errors="coerce")
    if "Date" in df.columns and "Time" in df.columns:
        need = dt.isna()
        if need.any():
            combo = pd.to_datetime(
                df.loc[need, "Date"].astype(str).str.replace(".", "-", regex=False)
                + " " + df.loc[need, "Time"].astype(str),
                errors="coerce",
            )
            dt.loc[need] = combo
    return pd.to_datetime(dt, errors="coerce")


def row_ms_per_bin(row: pd.Series) -> Optional[float]:
    for k in ("time_bin_ms", "timebin_ms", "bin_ms", "ms_per_bin"):
        if k in row and pd.notna(row[k]):
            try:
                return float(row[k])
            except Exception:
                pass
    return None


def is_timebin_col(name: str) -> bool:
    c = (name or "").lower()
    return "timebin" in c or c.endswith("_bins") or "bin" in c


def extract_durations_from_spans(spans, *, ms_per_bin: Optional[float], treat_as_bins: bool) -> List[float]:
    out: List[float] = []
    if spans is None:
        return out
    if isinstance(spans, (list, tuple)) and len(spans) == 2 and all(isinstance(x, (int, float)) for x in spans):
        spans = [spans]
    if isinstance(spans, dict):
        spans = [spans]
    if not isinstance(spans, (list, tuple)):
        return out

    for item in spans:
        on = off = None
        using_bins = False
        if isinstance(item, dict):
            if "onset_ms" in item or "on" in item:
                on = item.get("onset_ms", item.get("on"))
                off = item.get("offset_ms", item.get("off"))
            elif "onset_bin" in item or "on_bin" in item:
                on = item.get("onset_bin", item.get("on_bin"))
                off = item.get("offset_bin", item.get("off_bin"))
                using_bins = True
        elif isinstance(item, (list, tuple)) and len(item) >= 2:
            on, off = item[:2]

        try:
            dur = float(off) - float(on)
            if dur < 0:
                continue
            if treat_as_bins or using_bins:
                if ms_per_bin is None:
                    continue
                dur *= float(ms_per_bin)
            out.append(float(dur))
        except Exception:
            continue
    return out


def find_best_spans_column(df: pd.DataFrame) -> Optional[str]:
    for c in ("syllable_onsets_offsets_ms_dict", "syllable_onsets_offsets_ms", "onsets_offsets_ms_dict"):
        if c in df.columns:
            return c
    for c in ("syllable_onsets_offsets_timebins", "syllable_onsets_offsets_timebins_dict"):
        if c in df.columns:
            return c
    for c in df.columns:
        if c.lower().endswith("_dict") and df[c].notna().any():
            return c
    return None


def collect_unique_labels(df: pd.DataFrame, dict_col: str) -> List[str]:
    labels: List[str] = []
    for raw in df[dict_col].dropna():
        d = raw if isinstance(raw, dict) else maybe_parse_dict(raw)
        if isinstance(d, dict):
            labels.extend(str(k) for k in d.keys())
    labels = list(dict.fromkeys(labels))
    try:
        return sorted(labels, key=lambda x: int(x))
    except Exception:
        return sorted(labels)


def collect_phrase_durations(row: pd.Series, spans_col: str) -> Dict[str, List[float]]:
    raw = row.get(spans_col)
    d = raw if isinstance(raw, dict) else maybe_parse_dict(raw)
    if not isinstance(d, dict):
        return {}
    mpb = row_ms_per_bin(row)
    use_bins = is_timebin_col(spans_col)
    out = {}
    for label, spans in d.items():
        vals = extract_durations_from_spans(spans, ms_per_bin=mpb, treat_as_bins=use_bins)
        if vals:
            out[str(label)] = vals
    return out


def prepare_phrase_duration_data(decoded: Path, detect: Path, split_date: pd.Timestamp):
    if build_decoded_with_split_labels is None:
        raise ImportError(
            "Could not import merge_annotations_from_split_songs.build_decoded_with_split_labels. "
            f"Original error: {_MERGE_IMPORT_ERROR}"
        )

    ann = build_decoded_with_split_labels(
        decoded_database_json=decoded,
        song_detection_json=detect,
        only_song_present=True,
        compute_durations=True,
        add_recording_datetime=True,
        songs_only=True,
        flatten_spec_params=True,
        max_gap_between_song_segments=500,
        segment_index_offset=0,
        merge_repeated_syllables=True,
        repeat_gap_ms=10.0,
        repeat_gap_inclusive=False,
    )

    df = ann.annotations_appended_df.copy()
    dt = choose_datetime_series(df)
    df = df.assign(_dt=dt).dropna(subset=["_dt"]).sort_values("_dt").reset_index(drop=True)

    spans_col = find_best_spans_column(df)
    if spans_col is None:
        raise ValueError("Could not locate syllable onset/offset spans in merged annotations")

    labels = collect_unique_labels(df, spans_col)
    per_song = df.apply(lambda row: collect_phrase_durations(row, spans_col), axis=1)
    for label in labels:
        df[f"syllable_{label}_durations"] = per_song.apply(lambda d: d.get(str(label), []))

    # Exclude the lesion/sham treatment calendar day, matching the UMAP split.
    day = df["_dt"].dt.normalize()
    pre = df[day < split_date].copy()
    post = df[day > split_date].copy()
    return df, labels, pre, post


def choose_phrase_periods(pre: pd.DataFrame, post: pd.DataFrame, split_date: pd.Timestamp, mode: str):
    if mode == "study_windows":
        pre_day = pre["_dt"].dt.normalize()
        post_day = post["_dt"].dt.normalize()
        early_pre = pre[(pre_day >= split_date - pd.Timedelta(days=28)) &
                        (pre_day <= split_date - pd.Timedelta(days=15))].copy()
        late_pre = pre[(pre_day >= split_date - pd.Timedelta(days=14)) &
                       (pre_day <= split_date - pd.Timedelta(days=1))].copy()
        post_g = post[post_day >= split_date + pd.Timedelta(days=1)].copy()
        return early_pre, late_pre, post_g

    # auto_balance preserves the behavior of the earlier phrase-duration
    # plotting workflow: equal numbers of merged recording rows are used in
    # early pre, late pre, and post.
    n = min(len(pre) // 2, len(post))
    if n <= 0:
        return pre.iloc[0:0].copy(), pre.iloc[0:0].copy(), post.iloc[0:0].copy()
    late_pre = pre.tail(n).copy()
    early_pre = pre.iloc[len(pre) - 2 * n: len(pre) - n].copy()
    post_g = post.head(n).copy()
    return early_pre, late_pre, post_g


def values_long(period_df: pd.DataFrame, labels: Sequence[str], period: str) -> pd.DataFrame:
    parts = []
    for label in labels:
        col = f"syllable_{label}_durations"
        if col not in period_df.columns:
            continue
        vals = period_df[col].explode()
        vals = pd.to_numeric(vals, errors="coerce").dropna()
        if vals.empty:
            continue
        parts.append(pd.DataFrame({
            "period": period,
            "syllable": str(label),
            "phrase_duration_ms": vals.to_numpy(dtype=float),
        }))
    if not parts:
        return pd.DataFrame(columns=["period", "syllable", "phrase_duration_ms"])
    return pd.concat(parts, ignore_index=True)



# Only these bird/syllable combinations receive a darker violin color.
# This affects the phrase-duration violin only, NOT the UMAP plots.
VIOLIN_COLOR_OVERRIDES = {
    "USA5288": {
        "4": 0.68,
        "22": 0.68,
    },
}


def darken_color(color: str, factor: float) -> str:
    """Darken a matplotlib-compatible color while preserving its hue."""
    try:
        rgb = np.asarray(mcolors.to_rgb(color), dtype=float)
        rgb = np.clip(rgb * float(factor), 0.0, 1.0)
        return mcolors.to_hex(rgb)
    except Exception:
        return color


def phrase_violin_color(
    bird: str,
    label: str,
    base_color: str,
):
    """Return violin-specific color and whether this label is highlighted."""
    factor = VIOLIN_COLOR_OVERRIDES.get(
        str(bird), {}
    ).get(str(label))

    if factor is None:
        return base_color, False

    return darken_color(base_color, factor), True


def save_phrase_legend(path: Path):
    handles = [
        Line2D([0], [0], marker=PERIOD_MARKERS[p], linestyle="None",
               markerfacecolor="white", markeredgecolor="black",
               markeredgewidth=0.8, markersize=8, label=p)
        for p in PERIOD_ORDER
    ]
    fig, ax = plt.subplots(figsize=(3.2, 1.25))
    ax.axis("off")
    ax.legend(handles=handles, loc="center", frameon=False, fontsize=10,
              handletextpad=0.6, borderaxespad=0)
    fig.subplots_adjust(left=0.001, right=0.999, bottom=0.001, top=0.999)
    fig.savefig(path, dpi=300, transparent=True, bbox_inches="tight", pad_inches=0.01)
    plt.close(fig)


def save_phrase_violin(
    bird: str,
    png_path: Path,
    csv_path: Path,
    labels: Sequence[str],
    early_pre: pd.DataFrame,
    late_pre: pd.DataFrame,
    post: pd.DataFrame,
    color_map: Dict[int, str],
    y_max_s: Optional[float],
):
    period_dfs = {
        "early pre-lesion": early_pre,
        "late pre-lesion": late_pre,
        "post-lesion": post,
    }
    long_parts = [values_long(df, labels, p) for p, df in period_dfs.items()]
    long_df = pd.concat(long_parts, ignore_index=True)
    long_df.to_csv(csv_path, index=False)

    n_labels = max(len(labels), 1)
    # Keep the same 5-inch height as each UMAP panel. Width scales with repertoire.
    fig_w = max(10.0, 0.43 * n_labels + 2.0)
    fig, ax = plt.subplots(figsize=(fig_w, PANEL_HEIGHT_IN))
    rng = np.random.default_rng(0)

    for i, label in enumerate(labels):
        try:
            label_int = int(label)
            base_color = color_map.get(label_int, "#7f7f7f")
        except Exception:
            base_color = "#7f7f7f"

        color, is_highlighted = phrase_violin_color(
            bird,
            str(label),
            base_color,
        )

        # Keep ordinary syllable outlines unchanged.
        # Highlighted USA5288 syllables get a subtly darker,
        # slightly stronger outline.
        if is_highlighted:
            violin_edge_color = darken_color(color, 0.78)
            violin_linewidth = 1.15
        else:
            violin_edge_color = darken_color(color, 0.78)
            violin_linewidth = 0.85

        for period in PERIOD_ORDER:
            vals = long_df.loc[
                (long_df["period"] == period) & (long_df["syllable"].astype(str) == str(label)),
                "phrase_duration_ms",
            ].to_numpy(dtype=float)
            vals = vals[np.isfinite(vals)]
            if vals.size == 0:
                continue

            x = i + PERIOD_OFFSETS[period]

            # Actual violin body: narrower per period but substantially more visible
            # than the previous point-cloud-only compact figure.
            if vals.size >= 2 and np.nanstd(vals) > 0:
                vp = ax.violinplot(
                    [vals], positions=[x], widths=VIOLIN_WIDTH,
                    showmeans=False, showmedians=False, showextrema=False,
                    bw_method="scott",
                )
                for body in vp["bodies"]:
                    body.set_facecolor(color)
                    body.set_edgecolor(violin_edge_color)
                    body.set_alpha(VIOLIN_ALPHA)
                    body.set_linewidth(violin_linewidth)
                    body.set_zorder(1)

            # Preserve the original x spacing. Ordinary observations
            # remain faint, while the actual upper-tail observations
            # are slightly larger/more opaque. No range/error bars are
            # added, so every tail mark remains an observed datapoint.
            jitter = rng.uniform(
                -0.028,
                0.028,
                size=vals.size,
            )
            xvals = np.full(vals.size, x) + jitter

            if vals.size >= 5:
                tail_cutoff = float(
                    np.nanpercentile(
                        vals,
                        TAIL_PERCENTILE,
                    )
                )
                tail_mask = vals >= tail_cutoff
            else:
                tail_mask = np.zeros(
                    vals.size,
                    dtype=bool,
                )

            body_mask = ~tail_mask

            if np.any(body_mask):
                ax.scatter(
                    xvals[body_mask],
                    vals[body_mask],
                    s=RAW_POINT_SIZE,
                    marker=PERIOD_MARKERS[period],
                    c=color,
                    alpha=RAW_POINT_ALPHA,
                    linewidths=0,
                    rasterized=True,
                    zorder=2,
                )

            if np.any(tail_mask):
                ax.scatter(
                    xvals[tail_mask],
                    vals[tail_mask],
                    s=TAIL_POINT_SIZE,
                    marker=PERIOD_MARKERS[period],
                    c=color,
                    alpha=TAIL_POINT_ALPHA,
                    linewidths=0,
                    rasterized=True,
                    zorder=3,
                )

            # Median marker identifies period and remains readable at figure scale.
            med = float(np.nanmedian(vals))
            ax.scatter(
                [x], [med],
                s=MEDIAN_MARKER_SIZE,
                marker=PERIOD_MARKERS[period],
                c=color,
                edgecolors="black",
                linewidths=0.55,
                zorder=4,
            )

    ax.set_xlim(-0.55, len(labels) - 0.45)
    ax.set_xticks([])
    ax.set_xlabel("")
    ax.set_ylabel("Phrase Duration (s)", fontsize=12, labelpad=4)
    ax.yaxis.set_major_formatter(FuncFormatter(seconds_formatter))
    ax.tick_params(axis="y", labelsize=10, length=3, width=0.7, pad=2)
    ax.tick_params(axis="x", bottom=False)

    if y_max_s is not None:
        ax.set_ylim(0, float(y_max_s) * 1000.0 * 1.03)
    elif not long_df.empty:
        ymax = float(np.nanmax(long_df["phrase_duration_ms"]))
        ax.set_ylim(0, max(1.0, ymax * 1.02))

    ax.set_title("")
    ax.grid(False)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_linewidth(0.8)
    ax.spines["bottom"].set_linewidth(0.8)

    # No legend in the bird-level plot. The shared key is written separately.
    leg = ax.get_legend()
    if leg is not None:
        leg.remove()

    # Minimal whitespace while keeping a stable 5-inch canvas height.
    fig.subplots_adjust(left=0.065, right=0.998, bottom=0.040, top=0.975)
    fig.savefig(png_path, dpi=VIOLIN_DPI, facecolor="white", bbox_inches=None, pad_inches=0)
    plt.close(fig)


# -----------------------------------------------------------------------------
# Per-bird runner
# -----------------------------------------------------------------------------
def process_bird(
    bird: str,
    npz_path: Path,
    info: dict,
    fixed_colors: Dict[str, str],
    output_root: Path,
    phrase_period_mode: str,
    y_max_s: Optional[float],
):
    group = classify_lesion_group(info)
    if group is None:
        raise ValueError("Could not classify lesion group from metadata")

    split_date = lesion_date(info)
    group_dir = output_root / group
    png_dir = group_dir / "pngs"
    csv_dir = group_dir / "csvs"
    png_dir.mkdir(parents=True, exist_ok=True)
    csv_dir.mkdir(parents=True, exist_ok=True)

    print("\n" + "=" * 72)
    print(f"{bird}  ->  {group}")
    print("=" * 72)

    # ----- UMAP -----
    with np.load(npz_path, allow_pickle=True) as z:
        required = {"embedding_outputs", "hdbscan_labels", "file_indices", "file_map"}
        missing = required - set(z.files)
        if missing:
            raise KeyError(f"NPZ missing required arrays: {sorted(missing)}")

        coords = np.asarray(z["embedding_outputs"])
        labels = np.asarray(z["hdbscan_labels"]).astype(int)
        file_indices = np.asarray(z["file_indices"])
        file_map_raw = z["file_map"]
        file_map = file_map_raw.item() if isinstance(file_map_raw, np.ndarray) and file_map_raw.shape == () else file_map_raw
        if not isinstance(file_map, dict):
            try:
                file_map = dict(file_map)
            except Exception as exc:
                raise ValueError("Could not convert NPZ file_map to dict") from exc

    valid = np.all(np.isfinite(coords), axis=1)
    point_dates = build_point_dates(file_indices, file_map)
    pre_mask = np.asarray(point_dates < split_date) & valid
    post_mask = np.asarray(point_dates > split_date) & valid
    split_mask = np.asarray(point_dates == split_date) & valid

    if pre_mask.sum() == 0 or post_mask.sum() == 0:
        raise ValueError(f"Need both pre and post UMAP points; got pre={pre_mask.sum()}, post={post_mask.sum()}")

    cmap = build_color_map(labels, fixed_colors)
    analysis = pre_mask | post_mask
    xlim, ylim = robust_axis_limits(coords[analysis])

    summary = cluster_shift_summary(coords, labels, pre_mask, post_mask)
    summary.to_csv(csv_dir / f"{bird}_cluster_shift_summary.csv", index=False)

    date_summary = (
        pd.DataFrame({
            "date": point_dates,
            "period": np.where(point_dates < split_date, "pre",
                               np.where(point_dates > split_date, "post", "split_day")),
        })
        .groupby(["date", "period"])
        .size()
        .reset_index(name="n_points")
        .sort_values("date")
    )
    date_summary.to_csv(csv_dir / f"{bird}_recording_date_summary.csv", index=False)

    save_pre_post_umap(
        bird,
        png_dir / f"{bird}_pre_post_umap.png",
        coords, labels, pre_mask, post_mask, cmap, xlim, ylim,
    )
    save_centroid_umap(
        png_dir / f"{bird}_cluster_centroids.png",
        coords, cmap, summary, xlim, ylim,
    )

    # ----- Phrase durations -----
    bird_dir = npz_path.parent
    decoded = find_one(bird_dir, f"*{bird}*decoded_database.json")
    detect = find_one(bird_dir, f"*{bird}*song_detection.json")
    if decoded is None or detect is None:
        raise FileNotFoundError(
            f"Could not find decoded/database JSON pair for {bird}: decoded={decoded}, detect={detect}"
        )

    _, phrase_labels, pre_df, post_df = prepare_phrase_duration_data(decoded, detect, split_date)
    early_pre, late_pre, post_g = choose_phrase_periods(pre_df, post_df, split_date, phrase_period_mode)

    save_phrase_violin(
        bird,
        png_dir / f"{bird}_phrase_duration_violins.png",
        csv_dir / f"{bird}_phrase_duration_values.csv",
        phrase_labels,
        early_pre,
        late_pre,
        post_g,
        cmap,
        y_max_s,
    )

    print(f"Saved 3 PNGs to: {png_dir}")
    print(f"Saved CSVs to:   {csv_dir}")

    return {
        "bird": bird,
        "group": group,
        "split_date": split_date.date().isoformat(),
        "npz": str(npz_path),
        "n_umap_pre": int(pre_mask.sum()),
        "n_umap_split_day_excluded": int(split_mask.sum()),
        "n_umap_post": int(post_mask.sum()),
        "n_clusters_with_centroids": int(len(summary)),
        "n_phrase_labels": int(len(phrase_labels)),
        "phrase_period_mode": phrase_period_mode,
        "status": "ok",
        "error": "",
    }


# -----------------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------------
def parse_args():
    p = argparse.ArgumentParser(
        description="Generate the three Illustrator-ready Supplemental Fig. 2 QC plots per bird and sort them by lesion group."
    )
    p.add_argument("--root", type=Path, required=True,
                   help="Root directory containing per-bird analysis outputs.")
    p.add_argument("--metadata", type=Path, required=True,
                   help="AFP lesion metadata JSON.")
    p.add_argument("--colors", type=Path, required=True,
                   help="Fixed syllable-label color JSON.")
    p.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT,
                   help=f"Output folder (default: {DEFAULT_OUTPUT})")
    p.add_argument("--birds", nargs="+", default=None,
                   help="Optional subset, e.g. --birds USA5288 USA5443")
    p.add_argument(
        "--phrase-periods",
        choices=["auto_balance", "study_windows"],
        default="auto_balance",
        help=(
            "How to define early-pre/late-pre/post for the descriptive phrase-duration plot. "
            "auto_balance matches the earlier grouped plotting workflow; study_windows uses "
            "early pre=-28..-15 d, late pre=-14..-1 d, post=+1 d onward."
        ),
    )
    p.add_argument("--y-max-s", type=float, default=25.0,
                   help="Phrase-duration y-axis maximum in seconds (default: 25). Use 0 for automatic.")
    p.add_argument("--overwrite", action="store_true",
                   help="Reuse the output folder. Without this flag, existing files are still replaced by same-named outputs; no source data are modified.")
    return p.parse_args()


def main():
    args = parse_args()
    y_max_s = None if args.y_max_s is not None and args.y_max_s <= 0 else args.y_max_s

    metadata = load_json(args.metadata)
    if not isinstance(metadata, dict):
        raise ValueError("Metadata JSON must map bird IDs to dictionaries")
    fixed_colors = load_fixed_colors(args.colors)
    discovered = discover_birds(args.root)

    selected = discovered
    if args.birds:
        requested = {b.upper() for b in args.birds}
        selected = {b: p for b, p in discovered.items() if b.upper() in requested}
        missing = sorted(requested - {b.upper() for b in discovered})
        if missing:
            print("WARNING: requested birds not discovered: " + ", ".join(missing))

    args.output_root.mkdir(parents=True, exist_ok=True)
    for group in ("M+L", "L-only", "sham saline"):
        (args.output_root / group / "pngs").mkdir(parents=True, exist_ok=True)
        (args.output_root / group / "csvs").mkdir(parents=True, exist_ok=True)

    save_phrase_legend(args.output_root / "phrase_duration_period_legend.png")

    rows = []
    for i, (bird, npz_path) in enumerate(sorted(selected.items()), start=1):
        print(f"\nProcessing {i}/{len(selected)}: {bird}")
        if bird not in metadata:
            msg = "Bird missing from metadata JSON"
            print("SKIP: " + msg)
            rows.append({"bird": bird, "group": "", "status": "skipped", "error": msg})
            continue
        try:
            row = process_bird(
                bird=bird,
                npz_path=npz_path,
                info=metadata[bird],
                fixed_colors=fixed_colors,
                output_root=args.output_root,
                phrase_period_mode=args.phrase_periods,
                y_max_s=y_max_s,
            )
        except Exception as exc:
            print(f"ERROR for {bird}: {type(exc).__name__}: {exc}")
            traceback.print_exc()
            row = {
                "bird": bird,
                "group": classify_lesion_group(metadata.get(bird, {})) or "",
                "status": "error",
                "error": f"{type(exc).__name__}: {exc}",
            }
        rows.append(row)
        gc.collect()

    run_df = pd.DataFrame(rows)
    run_path = args.output_root / "suppfig2_qc_run_summary.csv"
    run_df.to_csv(run_path, index=False)

    print("\n" + "=" * 72)
    print("DONE")
    print("=" * 72)
    print(f"Output: {args.output_root}")
    print(f"Run summary: {run_path}")
    if not run_df.empty and "status" in run_df.columns:
        print(run_df.groupby(["group", "status"], dropna=False).size().to_string())


if __name__ == "__main__":
    main()

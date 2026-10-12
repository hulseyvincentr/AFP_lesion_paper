#!/usr/bin/env python3
"""
make_fig3E_and_timecourse_supp_from_raw.py

Create revised AFP lesion time-course figures directly from the same
pair-metrics and long phrase-duration inputs used for the Q75 analysis.

Outputs
-------
1) Fig. 3E
   - M+L group median + IQR (purple)
   - Sham group median + IQR (teal)
   - Bird 17 / USA5509 and Bird 21 / USA5443 as light example traces
   - no panel letter (add later in Illustrator)

2) Supplemental figure: all M+L trajectories
   - all M+L individual trajectories, light and unlabeled
   - M+L group median
   - Sham group median + IQR
   - no panel letter

3) Supplemental figure: all sham trajectories
   - all sham individual trajectories, light and unlabeled
   - Sham group median + IQR
   - no panel letter

Analysis workflow
-----------------
1. Compute each bird's Q75 threshold from syllable-level delta_cv.
2. Keep syllables with delta_cv >= that bird-specific Q75 threshold.
3. For each selected syllable/day, calculate phrase-duration CV if at least
   MIN_DAILY_PHRASES phrase occurrences are present.
4. Take the median across selected syllables to get one CV per bird/day.
5. Baseline-subtract each bird using its median late-pre CV, days -14 to -1.
6. Apply a centered 7-calendar-day rolling median separately on pre- and
   post-lesion days, so smoothing never crosses lesion day.
7. Calculate equal-bird group median and IQR by day.
8. Plot group summaries only when at least MIN_BIRDS_FOR_SUMMARY birds contribute.

Expected pair-metrics CSV columns
---------------------------------
animal_id
syllable
lesion_group_detailed
pre_cv
post_cv
delta_cv

Expected long CSV columns
-------------------------
bird identifier: animal_id / bird / bird_id / Animal ID
syllable:        syllable / syllable_id / cluster / label
lesion day:      relative_day / day / rel_day
phrase duration: phrase_duration_s / duration_s / phrase_duration / duration
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch


# ---------------------------------------------------------------------
# GROUP NAMES / PALETTE
# ---------------------------------------------------------------------
SHAM = "sham saline injection"
LATERAL = "Lateral lesion only"
PARTIAL = "Partial Medial and Lateral lesion"
COMPLETE = "Complete Medial and Lateral lesion"
POOLED_ML = "Complete and partial medial and lateral lesion"

PURPLE = "#7A4FB7"
LIGHT_PURPLE = "#BDA7E3"
EXAMPLE_17 = "#986BD0"
EXAMPLE_21 = EXAMPLE_17

TEAL = "#1B9E77"
LIGHT_TEAL = "#A8DED1"

RED = "#D62728"
GRAY = "#777777"

LEGEND_FONTSIZE = 11.5
EXAMPLE_LABEL_FONTSIZE = LEGEND_FONTSIZE

# Supplemental Table 1 display IDs for the two example birds
EXAMPLE_BIRDS = {
    "USA5509": "Bird 17",
    "USA5443": "Bird 21",
}


# ---------------------------------------------------------------------
# DEFAULT ANALYSIS SETTINGS
# ---------------------------------------------------------------------
Q = 0.75
LATE_PRE_START = -14
LATE_PRE_END = -1
X_MIN = -28
X_MAX = 28
ROLLING_WINDOW_DAYS = 7
MIN_DAILY_PHRASES = 10
MIN_BIRDS_FOR_SUMMARY = 3

# Fixed y-range so all figures are directly comparable
Y_MIN = -0.22
Y_MAX = 0.86


def choose_first_existing(df: pd.DataFrame, candidates: list[str]) -> str:
    for c in candidates:
        if c in df.columns:
            return c
    raise ValueError(
        "Could not find any of the expected columns:\n"
        + "\n".join(f"  - {x}" for x in candidates)
    )


def canonical_detail_group(value: object) -> str:
    s = " ".join(str(value).strip().split()).lower().replace("_", " ")

    if s in {"sham saline injection", "sham", "sham saline", "saline"}:
        return SHAM

    if s in {
        "lateral lesion only",
        "lateral only",
        "lateral-only",
        "lateral hit only",
    }:
        return LATERAL

    if "partial" in s and "medial" in s and "lateral" in s:
        return PARTIAL

    if "complete" in s and "medial" in s and "lateral" in s:
        return COMPLETE

    raise ValueError(f"Unrecognized lesion group: {value!r}")


def pooled_group(detail_group: str) -> str:
    if detail_group in {PARTIAL, COMPLETE}:
        return POOLED_ML
    return detail_group


def load_pair_metrics(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)

    required = {
        "animal_id",
        "syllable",
        "lesion_group_detailed",
        "pre_cv",
        "post_cv",
        "delta_cv",
    }
    missing = required - set(df.columns)
    if missing:
        raise ValueError(
            f"Missing required columns from pair-metrics CSV: {sorted(missing)}"
        )

    df = df.copy()
    df["animal_id"] = df["animal_id"].astype(str).str.strip()
    df["syllable"] = df["syllable"].astype(str).str.strip()
    df["detail_group"] = df["lesion_group_detailed"].map(canonical_detail_group)
    df["group"] = df["detail_group"].map(pooled_group)

    for col in ["pre_cv", "post_cv", "delta_cv"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    keep = (
        np.isfinite(df["pre_cv"])
        & np.isfinite(df["post_cv"])
        & np.isfinite(df["delta_cv"])
    )
    return df.loc[keep].copy()


def select_q75_syllables(pair_df: pd.DataFrame) -> pd.DataFrame:
    rows = []

    for bird, sub in pair_df.groupby("animal_id", sort=True):
        threshold = float(np.quantile(sub["delta_cv"].to_numpy(float), Q))
        tmp = sub.loc[sub["delta_cv"] >= threshold].copy()
        tmp["q75_threshold"] = threshold
        rows.append(tmp)

    selected = pd.concat(rows, ignore_index=True)

    return (
        selected[
            [
                "animal_id",
                "syllable",
                "group",
                "detail_group",
                "delta_cv",
                "q75_threshold",
            ]
        ]
        .drop_duplicates()
        .copy()
    )


def load_long_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)

    animal_col = choose_first_existing(
        df, ["animal_id", "bird", "bird_id", "Animal ID"]
    )
    syll_col = choose_first_existing(
        df, ["syllable", "syllable_id", "cluster", "label"]
    )
    day_col = choose_first_existing(
        df, ["relative_day", "day", "rel_day"]
    )
    dur_col = choose_first_existing(
        df,
        ["phrase_duration_s", "duration_s", "phrase_duration", "duration"],
    )

    out = df.copy().rename(
        columns={
            animal_col: "animal_id",
            syll_col: "syllable",
            day_col: "relative_day",
            dur_col: "phrase_duration_s",
        }
    )

    out["animal_id"] = out["animal_id"].astype(str).str.strip()
    out["syllable"] = out["syllable"].astype(str).str.strip()
    out["relative_day"] = pd.to_numeric(out["relative_day"], errors="coerce")
    out["phrase_duration_s"] = pd.to_numeric(out["phrase_duration_s"], errors="coerce")

    keep = (
        np.isfinite(out["relative_day"])
        & np.isfinite(out["phrase_duration_s"])
    )
    return out.loc[keep].copy()


def build_daily_bird_cv(
    long_df: pd.DataFrame,
    selected_pairs: pd.DataFrame,
    min_daily_phrases: int,
) -> pd.DataFrame:
    """
    Compute daily CV per selected syllable, require >= min_daily_phrases,
    then take the median across Q75 syllables to get one bird/day value.
    """
    keep = (
        selected_pairs[["animal_id", "syllable", "group"]]
        .drop_duplicates()
        .copy()
    )

    merged = long_df.merge(
        keep,
        on=["animal_id", "syllable"],
        how="inner",
    )

    daily_syll = (
        merged.groupby(
            ["group", "animal_id", "relative_day", "syllable"]
        )["phrase_duration_s"]
        .agg(["count", "mean", "std"])
        .reset_index()
    )

    daily_syll = daily_syll.loc[daily_syll["count"] >= min_daily_phrases].copy()
    daily_syll["cv"] = daily_syll["std"] / daily_syll["mean"]
    daily_syll = daily_syll.loc[np.isfinite(daily_syll["cv"])].copy()

    bird_day = (
        daily_syll.groupby(
            ["group", "animal_id", "relative_day"]
        )["cv"]
        .median()
        .reset_index()
        .rename(columns={"cv": "bird_day_cv"})
    )

    return bird_day


def normalize_to_late_pre(
    bird_day: pd.DataFrame,
    late_pre_start: int,
    late_pre_end: int,
) -> pd.DataFrame:
    baseline = (
        bird_day.loc[
            (bird_day["relative_day"] >= late_pre_start)
            & (bird_day["relative_day"] <= late_pre_end)
        ]
        .groupby("animal_id")["bird_day_cv"]
        .median()
        .rename("late_pre_baseline")
        .reset_index()
    )

    out = bird_day.merge(
        baseline,
        on="animal_id",
        how="left",
    )
    out = out.loc[np.isfinite(out["late_pre_baseline"])].copy()
    out["cv_norm"] = out["bird_day_cv"] - out["late_pre_baseline"]

    return out


def smooth_one_side(
    sub: pd.DataFrame,
    all_days: np.ndarray,
    allowed_days: np.ndarray,
    rolling_window_days: int,
) -> pd.DataFrame:
    """
    Reindex to calendar days so a 7-row centered rolling window really is
    a 7-calendar-day window. Restrict to pre or post days before smoothing
    so the rolling window cannot cross lesion day.
    """
    tmp = (
        sub[["relative_day", "cv_norm"]]
        .drop_duplicates(subset=["relative_day"])
        .set_index("relative_day")
        .sort_index()
    )

    tmp = tmp.reindex(all_days)
    tmp = tmp.loc[allowed_days].copy()

    tmp["cv_norm_smooth"] = (
        tmp["cv_norm"]
        .rolling(
            window=rolling_window_days,
            center=True,
            min_periods=1,
        )
        .median()
    )

    tmp.index.name = "relative_day"
    return tmp.reset_index()


def smooth_equal_bird(
    norm_df: pd.DataFrame,
    x_min: int,
    x_max: int,
    rolling_window_days: int,
) -> pd.DataFrame:
    all_days = np.arange(x_min, x_max + 1)
    pre_days = all_days[all_days < 0]
    post_days = all_days[all_days > 0]

    pieces = []

    for (group, bird), sub in norm_df.groupby(["group", "animal_id"], sort=True):
        pre = smooth_one_side(
            sub,
            all_days=all_days,
            allowed_days=pre_days,
            rolling_window_days=rolling_window_days,
        )
        post = smooth_one_side(
            sub,
            all_days=all_days,
            allowed_days=post_days,
            rolling_window_days=rolling_window_days,
        )

        tmp = pd.concat([pre, post], ignore_index=True)
        tmp["group"] = group
        tmp["animal_id"] = bird
        pieces.append(tmp)

    return pd.concat(pieces, ignore_index=True)


def summarize_group_timecourse(
    smoothed_df: pd.DataFrame,
    min_birds_for_summary: int,
) -> pd.DataFrame:
    summary = (
        smoothed_df.groupby(
            ["group", "relative_day"]
        )["cv_norm_smooth"]
        .agg(
            n_birds=lambda x: x.notna().sum(),
            median="median",
            q25=lambda x: x.quantile(0.25),
            q75=lambda x: x.quantile(0.75),
        )
        .reset_index()
    )

    return summary.loc[summary["n_birds"] >= min_birds_for_summary].copy()


def subset_summary(summary: pd.DataFrame, group: str) -> pd.DataFrame:
    return (
        summary.loc[summary["group"] == group]
        .sort_values("relative_day")
        .copy()
    )


def apply_axes(ax: plt.Axes, panel_label: str | None = None) -> None:
    ax.axvline(
        0,
        color=RED,
        linestyle="--",
        linewidth=1.1,
        zorder=0,
    )
    ax.axhline(
        0,
        color=GRAY,
        linestyle="--",
        linewidth=1.0,
        zorder=0,
    )

    ax.set_xlim(X_MIN, X_MAX)
    ax.set_ylim(Y_MIN, Y_MAX)
    ax.set_xticks([-20, -10, 0, 10, 20])

    ax.set_xlabel("Days relative to lesion", fontsize=13)
    ax.set_ylabel(
        "Baseline-subtracted phrase-duration CV\n(7-day rolling median)",
        fontsize=13,
    )

    ax.tick_params(axis="both", labelsize=11, width=1.1, length=5)

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_linewidth(1.1)
    ax.spines["bottom"].set_linewidth(1.1)

    if panel_label:
        ax.text(
            -0.12,
            1.02,
            panel_label,
            transform=ax.transAxes,
            fontsize=24,
            fontweight="bold",
            ha="left",
            va="bottom",
        )


def plot_summary(
    ax: plt.Axes,
    sub: pd.DataFrame,
    line_color: str,
    fill_color: str,
    linewidth: float,
    alpha: float,
    zorder: int,
) -> None:
    if sub.empty:
        return

    x = sub["relative_day"].to_numpy(float)
    med = sub["median"].to_numpy(float)
    q25 = sub["q25"].to_numpy(float)
    q75 = sub["q75"].to_numpy(float)

    ax.fill_between(
        x,
        q25,
        q75,
        color=fill_color,
        alpha=alpha,
        linewidth=0,
        zorder=zorder - 1,
    )
    ax.plot(
        x,
        med,
        color=line_color,
        linewidth=linewidth,
        solid_capstyle="round",
        zorder=zorder,
    )


def get_example_trace(smoothed: pd.DataFrame, animal_id: str) -> pd.DataFrame:
    return (
        smoothed.loc[
            (smoothed["animal_id"] == animal_id)
            & np.isfinite(smoothed["cv_norm_smooth"])
        ]
        .sort_values("relative_day")
        .copy()
    )


def draw_example(
    ax: plt.Axes,
    trace: pd.DataFrame,
    display_label: str,
    color: str,
) -> None:
    if trace.empty:
        print(f"WARNING: no smoothed trajectory found for {display_label}.")
        return

    ax.plot(
        trace["relative_day"],
        trace["cv_norm_smooth"],
        color=color,
        linewidth=1.6,
        alpha=0.95,
        zorder=5,
    )

    last = trace.iloc[-1]
    ax.annotate(
        display_label,
        xy=(float(last["relative_day"]), float(last["cv_norm_smooth"])),
        xytext=(5, 0),
        textcoords="offset points",
        color=color,
        fontsize=EXAMPLE_LABEL_FONTSIZE,
        ha="left",
        va="center",
        clip_on=False,
    )


def save_figure(fig: plt.Figure, out_stem: Path, dpi: int) -> None:
    png = out_stem.with_suffix(".png")
    svg = out_stem.with_suffix(".svg")
    fig.savefig(png, dpi=dpi, bbox_inches="tight")
    fig.savefig(svg, bbox_inches="tight")


def make_fig3e(
    smoothed: pd.DataFrame,
    summary: pd.DataFrame,
    out_dir: Path,
    dpi: int,
) -> None:
    ml = subset_summary(summary, POOLED_ML)
    sham = subset_summary(summary, SHAM)

    fig, ax = plt.subplots(figsize=(8.2, 5.1))

    plot_summary(
        ax, ml,
        line_color=PURPLE,
        fill_color=LIGHT_PURPLE,
        linewidth=3.2,
        alpha=0.28,
        zorder=4,
    )
    plot_summary(
        ax, sham,
        line_color=TEAL,
        fill_color=LIGHT_TEAL,
        linewidth=2.6,
        alpha=0.32,
        zorder=3,
    )

    draw_example(
        ax,
        get_example_trace(smoothed, "USA5509"),
        EXAMPLE_BIRDS["USA5509"],
        EXAMPLE_17,
    )
    draw_example(
        ax,
        get_example_trace(smoothed, "USA5443"),
        EXAMPLE_BIRDS["USA5443"],
        EXAMPLE_21,
    )

    apply_axes(ax, panel_label=None)

    handles = [
        Line2D([0], [0], color=PURPLE, lw=3.2, label="M+L median"),
        Patch(facecolor=LIGHT_PURPLE, alpha=0.28, edgecolor="none", label="M+L IQR"),
        Line2D([0], [0], color=TEAL, lw=2.6, label="Sham median"),
        Patch(facecolor=LIGHT_TEAL, alpha=0.32, edgecolor="none", label="Sham IQR"),
    ]
    ax.legend(
        handles=handles,
        loc="upper left",
        frameon=False,
        fontsize=LEGEND_FONTSIZE,
        handlelength=2.7,
        labelspacing=0.45,
    )

    fig.tight_layout()
    save_figure(fig, out_dir / "Fig3E_Q75_timecourse_revised", dpi=dpi)
    plt.close(fig)


def make_supplement_ml(
    smoothed: pd.DataFrame,
    summary: pd.DataFrame,
    out_dir: Path,
    dpi: int,
) -> None:
    ml_summary = subset_summary(summary, POOLED_ML)
    sham_summary = subset_summary(summary, SHAM)

    fig, ax = plt.subplots(figsize=(8.2, 5.1))

    ml_individual = smoothed.loc[
        (smoothed["group"] == POOLED_ML)
        & np.isfinite(smoothed["cv_norm_smooth"])
    ].copy()

    for _, trace in ml_individual.groupby("animal_id"):
        trace = trace.sort_values("relative_day")
        ax.plot(
            trace["relative_day"],
            trace["cv_norm_smooth"],
            color=LIGHT_PURPLE,
            linewidth=1.1,
            alpha=0.55,
            zorder=1,
        )

    if not ml_summary.empty:
        ax.plot(
            ml_summary["relative_day"],
            ml_summary["median"],
            color=PURPLE,
            linewidth=3.2,
            solid_capstyle="round",
            zorder=4,
        )

    if not sham_summary.empty:
        x = sham_summary["relative_day"].to_numpy(float)
        ax.fill_between(
            x,
            sham_summary["q25"].to_numpy(float),
            sham_summary["q75"].to_numpy(float),
            color=LIGHT_TEAL,
            alpha=0.32,
            linewidth=0,
            zorder=2,
        )
        ax.plot(
            x,
            sham_summary["median"],
            color=TEAL,
            linewidth=2.6,
            solid_capstyle="round",
            zorder=3,
        )

    apply_axes(ax, panel_label=None)

    handles = [
        Line2D(
            [0], [0],
            color=LIGHT_PURPLE,
            lw=1.3,
            alpha=0.70,
            label="Individual M+L birds (n = 9)",
        ),
        Line2D(
            [0], [0],
            color=PURPLE,
            lw=3.2,
            label="M+L group median\n(across available birds)",
        ),
        Line2D(
            [0], [0],
            color=TEAL,
            lw=2.6,
            label="Sham median",
        ),
        Patch(
            facecolor=LIGHT_TEAL,
            alpha=0.32,
            edgecolor="none",
            label="Sham IQR",
        ),
    ]

    ax.legend(
        handles=handles,
        loc="upper left",
        frameon=False,
        fontsize=LEGEND_FONTSIZE,
        handlelength=2.7,
        labelspacing=0.55,
    )

    fig.tight_layout()
    save_figure(fig, out_dir / "Supp_Q75_all_ML_trajectories_plus_sham", dpi=dpi)
    plt.close(fig)


def make_supplement_sham(
    smoothed: pd.DataFrame,
    summary: pd.DataFrame,
    out_dir: Path,
    dpi: int,
) -> None:
    sham_summary = subset_summary(summary, SHAM)

    fig, ax = plt.subplots(figsize=(8.2, 5.1))

    sham_individual = smoothed.loc[
        (smoothed["group"] == SHAM)
        & np.isfinite(smoothed["cv_norm_smooth"])
    ].copy()

    for _, trace in sham_individual.groupby("animal_id"):
        trace = trace.sort_values("relative_day")
        ax.plot(
            trace["relative_day"],
            trace["cv_norm_smooth"],
            color=LIGHT_TEAL,
            linewidth=1.1,
            alpha=0.75,
            zorder=1,
        )

    plot_summary(
        ax, sham_summary,
        line_color=TEAL,
        fill_color=LIGHT_TEAL,
        linewidth=2.8,
        alpha=0.32,
        zorder=3,
    )

    apply_axes(ax, panel_label=None)

    handles = [
        Line2D(
            [0], [0],
            color=LIGHT_TEAL,
            lw=1.3,
            alpha=0.80,
            label="Individual sham birds (n = 4)",
        ),
        Line2D(
            [0], [0],
            color=TEAL,
            lw=2.8,
            label="Sham group median\n(across available birds)",
        ),
        Patch(
            facecolor=LIGHT_TEAL,
            alpha=0.32,
            edgecolor="none",
            label="Sham IQR",
        ),
    ]

    ax.legend(
        handles=handles,
        loc="upper left",
        frameon=False,
        fontsize=LEGEND_FONTSIZE,
        handlelength=2.7,
        labelspacing=0.55,
    )

    fig.tight_layout()
    save_figure(fig, out_dir / "Supp_Q75_all_sham_trajectories", dpi=dpi)
    plt.close(fig)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()

    p.add_argument(
        "--pair-metrics",
        type=Path,
        required=True,
        help=(
            "Balanced pair-metrics CSV: "
            "/path/to/"
            "figure3_balanced_pair_metrics.csv"
        ),
    )
    p.add_argument(
        "--duration-long-csv",
        type=Path,
        required=True,
        help=(
            "Long phrase-duration CSV: "
            "/path/to/"
            "figure3_phrase_duration_long.csv"
        ),
    )
    p.add_argument(
        "--output",
        type=Path,
        default=Path("outputs/figure3_timecourse"),
        help="Output folder (default: outputs/figure3_timecourse)",
    )
    p.add_argument("--dpi", type=int, default=600)
    p.add_argument(
        "--min-daily-phrases",
        type=int,
        default=MIN_DAILY_PHRASES,
    )
    p.add_argument(
        "--min-birds-for-summary",
        type=int,
        default=MIN_BIRDS_FOR_SUMMARY,
    )

    return p.parse_args()


def main() -> None:
    args = parse_args()

    pair_path = args.pair_metrics.expanduser().resolve()
    long_path = args.duration_long_csv.expanduser().resolve()
    out_dir = args.output.expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    if not pair_path.exists():
        raise FileNotFoundError(
            f"\nPair-metrics CSV not found:\n  {pair_path}\n"
            "\nUse --pair-metrics to point to the correct file."
        )

    if not long_path.exists():
        raise FileNotFoundError(
            f"\nLong phrase-duration CSV not found:\n  {long_path}\n"
            "\nUse --duration-long-csv to point to the correct file."
        )

    print(f"Pair metrics: {pair_path}")
    print(f"Duration data: {long_path}")
    print(f"Output:        {out_dir}")
    print()

    pair_df = load_pair_metrics(pair_path)
    selected = select_q75_syllables(pair_df)
    long_df = load_long_csv(long_path)

    bird_day = build_daily_bird_cv(
        long_df,
        selected,
        min_daily_phrases=args.min_daily_phrases,
    )

    normalized = normalize_to_late_pre(
        bird_day,
        late_pre_start=LATE_PRE_START,
        late_pre_end=LATE_PRE_END,
    )

    smoothed = smooth_equal_bird(
        normalized,
        x_min=X_MIN,
        x_max=X_MAX,
        rolling_window_days=ROLLING_WINDOW_DAYS,
    )

    summary = summarize_group_timecourse(
        smoothed,
        min_birds_for_summary=args.min_birds_for_summary,
    )

    # Save audit / intermediate CSVs
    selected.to_csv(out_dir / "Q75_selected_syllables.csv", index=False)
    bird_day.to_csv(out_dir / "Q75_daily_bird_CV.csv", index=False)
    normalized.to_csv(out_dir / "Q75_daily_bird_CV_baseline_subtracted.csv", index=False)
    smoothed.to_csv(out_dir / "Q75_daily_bird_CV_7day_rolling_median.csv", index=False)
    summary.to_csv(out_dir / "Q75_group_timecourse_median_IQR.csv", index=False)

    print("Bird counts found:")
    print(
        selected[["animal_id", "group"]]
        .drop_duplicates()
        .groupby("group")["animal_id"]
        .nunique()
    )
    print()

    for raw, display in EXAMPLE_BIRDS.items():
        found = raw in set(smoothed["animal_id"])
        print(f"{display}: {raw} -> {'FOUND' if found else 'NOT FOUND'}")

    make_fig3e(smoothed, summary, out_dir, dpi=args.dpi)
    make_supplement_ml(smoothed, summary, out_dir, dpi=args.dpi)
    make_supplement_sham(smoothed, summary, out_dir, dpi=args.dpi)

    print("\nSaved:")
    print(f"  {out_dir / 'Fig3E_Q75_timecourse_revised.png'}")
    print(f"  {out_dir / 'Fig3E_Q75_timecourse_revised.svg'}")
    print(f"  {out_dir / 'Supp_Q75_all_ML_trajectories_plus_sham.png'}")
    print(f"  {out_dir / 'Supp_Q75_all_ML_trajectories_plus_sham.svg'}")
    print(f"  {out_dir / 'Supp_Q75_all_sham_trajectories.png'}")
    print(f"  {out_dir / 'Supp_Q75_all_sham_trajectories.svg'}")
    print("\nDone.")


if __name__ == "__main__":
    main()

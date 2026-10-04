# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "altair>=5.0",
#     "marimo>=0.14.0",
#     "pandas>=2.0",
# ]
# ///
#
# Run from the repository root to export the HTML with:
#   uv run --script src/npc_lims/scripts/completeness_dashboard.py
# Add `--serve` to launch the live marimo app instead.

import marimo

__generated_with = "0.25.1"
app = marimo.App(width="full")


@app.cell
def _():
    import subprocess
    from io import StringIO
    from pathlib import Path

    import altair as alt
    import marimo as mo
    import pandas as pd

    return Path, StringIO, alt, mo, pd, subprocess


@app.cell
def _(mo):
    mo.md("""
    # `status.csv` completeness over time

    This dashboard reconstructs `tables/status.csv` from every commit that changed
    the file, then shows the percentage complete among applicable sessions in
    each status column. `true` is complete, `false` is incomplete, and blank
    values are excluded because they are not applicable or are blocked by
    another process. The `date` and `*_id` identifier columns are omitted.
    """)
    return


@app.cell
def _(Path, subprocess):
    repo_root = Path(
        subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"], text=True
        ).strip()
    )
    status_relpath = "tables/status.csv"
    return repo_root, status_relpath


@app.cell
def _(StringIO, pd, repo_root, status_relpath, subprocess):
    def load_status_history(repo_root, status_relpath):
        """Return completeness records for all and production-only sessions."""
        history_text = subprocess.check_output(
            [
                "git",
                "-C",
                str(repo_root),
                "log",
                "--reverse",
                "--format=%H%x1f%aI%x1f%s",
                "--",
                status_relpath,
            ],
            text=True,
            encoding="utf-8",
            errors="replace",
        )

        records = []
        column_order = []
        for history_line in history_text.splitlines():
            commit_sha, committed_at, commit_message = history_line.split("\x1f", 2)
            csv_text = subprocess.check_output(
                [
                    "git",
                    "-C",
                    str(repo_root),
                    "show",
                    f"{commit_sha}:{status_relpath}",
                ],
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            snapshot = pd.read_csv(StringIO(csv_text)).replace(
                r"^\s*$", pd.NA, regex=True
            )
            commit_date = pd.to_datetime(committed_at, utc=True)

            if "is_prod" in snapshot.columns:
                prod_mask = (
                    snapshot["is_prod"]
                    .astype("string")
                    .str.strip()
                    .str.lower()
                    .eq("true")
                )
            else:
                prod_mask = pd.Series(False, index=snapshot.index)

            scoped_snapshots = {
                "all": snapshot,
                "prod": snapshot.loc[prod_mask],
            }
            for scope, scoped_snapshot in scoped_snapshots.items():
                for column in snapshot.columns:
                    if column not in column_order:
                        column_order.append(column)
                    true_count = int(
                        scoped_snapshot[column]
                        .astype("string")
                        .str.strip()
                        .str.lower()
                        .eq("true")
                        .sum()
                    )
                    false_count = int(
                        scoped_snapshot[column]
                        .astype("string")
                        .str.strip()
                        .str.lower()
                        .eq("false")
                        .sum()
                    )
                    applicable_count = true_count + false_count
                    excluded_count = len(scoped_snapshot) - applicable_count
                    records.append(
                        {
                            "scope": scope,
                            "commit_sha": commit_sha,
                            "commit": commit_sha[:7],
                            "commit_date": commit_date,
                            "commit_message": commit_message,
                            "column": column,
                            "true_count": true_count,
                            "false_count": false_count,
                            "applicable_count": applicable_count,
                            "excluded_count": excluded_count,
                            "percent_complete": (
                                100 * true_count / applicable_count
                                if applicable_count
                                else None
                            ),
                        }
                    )

        if not records:
            raise RuntimeError(f"No history found for {status_relpath}")

        return pd.DataFrame(records), column_order


    all_metrics, columns = load_status_history(repo_root, status_relpath)
    columns = [
        column
        for column in columns
        if column not in {"date", "is_prod"} and not column.endswith("_id")
    ]
    all_metrics = all_metrics[all_metrics["column"].isin(columns)].copy()
    sep_28_nwb_error = (
        all_metrics["column"].eq("is_nwb_cached")
        & all_metrics["commit_date"].dt.strftime("%Y-%m-%d").eq("2026-09-28")
        & all_metrics["percent_complete"].eq(0)
    )
    all_metrics = all_metrics.loc[~sep_28_nwb_error].copy()
    metrics = all_metrics[all_metrics["scope"].eq("prod")].copy()
    snapshot_count = metrics["commit_sha"].nunique()
    latest_commit = metrics["commit_date"].max()
    latest_sha = metrics.loc[
        metrics["commit_date"].eq(latest_commit), "commit_sha"
    ].iloc[0]
    return (
        all_metrics,
        columns,
        latest_commit,
        latest_sha,
        metrics,
        snapshot_count,
    )


@app.cell
def _(columns, mo):
    hidden_by_default = {"is_rig_json", "is_session_json"}
    default_line_columns = [
        column for column in columns if column not in hidden_by_default
    ]
    column_selector = mo.ui.multiselect(
        options=columns,
        value=default_line_columns,
        label="Columns in the time-series chart",
    )
    return (column_selector,)


@app.cell
def _(all_metrics, alt, column_selector, metrics, mo):
    selected_columns = column_selector.value
    def make_line_chart(chart_metrics, title, selection_name):
        legend_selection = alt.selection_point(
            name=selection_name,
            fields=["column"],
            bind="legend",
        )
        return (
            alt.Chart(chart_metrics)
            .add_params(legend_selection)
            .mark_line(interpolate="step-after", point=True)
            .encode(
                x=alt.X("commit_date:T", title="Commit date"),
                y=alt.Y(
                    "percent_complete:Q",
                    title="% complete",
                    scale=alt.Scale(zero=False, domainMax=100),
                ),
                color=alt.Color("column:N", title="Column"),
                detail="column:N",
                opacity=alt.condition(
                    legend_selection,
                    alt.value(1),
                    alt.value(0.15),
                ),
                tooltip=[
                    alt.Tooltip("column:N", title="Column"),
                    alt.Tooltip(
                        "percent_complete:Q",
                        title="% complete",
                        format=".1f",
                    ),
                    alt.Tooltip("true_count:Q", title="Done"),
                    alt.Tooltip("false_count:Q", title="Pending"),
                    alt.Tooltip("excluded_count:Q", title="NA"),
                    alt.Tooltip("commit_date:T", title="Commit date"),
                    alt.Tooltip("commit:N", title="Commit"),
                    alt.Tooltip("commit_message:N", title="Commit message"),
                ],
            )
            .properties(title=title, height=480)
            .interactive()
        )

    prod_chart = make_line_chart(
        metrics[metrics["column"].isin(selected_columns)],
        "Production sessions",
        "prod_legend_selection",
    )
    all_chart = make_line_chart(
        all_metrics[
            all_metrics["scope"].eq("all")
            & all_metrics["column"].isin(selected_columns)
        ],
        "All sessions",
        "all_legend_selection",
    )
    plot_tabs = mo.ui.tabs(
        {
            "Prod-only": prod_chart,
            "All sessions": all_chart,
        }
    )
    mo.vstack(
        [
            mo.md("## Completeness trends"),
            column_selector,
            plot_tabs,
        ]
    )
    return


@app.cell
def _(latest_commit, latest_sha, metrics, mo, snapshot_count):
    latest_metrics = metrics[metrics["commit_sha"].eq(latest_sha)].copy()
    latest_metrics["% complete"] = latest_metrics["percent_complete"].round(1)
    latest_summary = latest_metrics[
        ["column", "% complete", "true_count", "false_count", "applicable_count", "excluded_count"]
    ].sort_values("column")
    latest_summary = latest_summary.rename(
        columns={
            "true_count": "true sessions",
            "false_count": "false sessions",
            "applicable_count": "applicable sessions",
            "excluded_count": "excluded sessions",
        }
    )
    latest_summary_widget = mo.ui.table(
        latest_summary.to_dict(orient="records"),
        pagination=False,
        selection=None,
        show_data_types=False,
        max_height=400,
        freeze_columns_left=["column"],
    )

    mo.vstack(
        [
            mo.md(
                f"**{snapshot_count} snapshots** | latest commit `{latest_sha[:7]}` "
                f"on {latest_commit.strftime('%Y-%m-%d %H:%M UTC')}"
            ),
            mo.md("## Latest snapshot"),
            latest_summary_widget,
        ]
    )
    return


@app.cell
def _(StringIO, latest_sha, mo, pd, repo_root, status_relpath, subprocess):
    latest_status_csv = subprocess.check_output(
        [
            "git",
            "-C",
            str(repo_root),
            "show",
            f"{latest_sha}:{status_relpath}",
        ],
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    latest_status_table = pd.read_csv(StringIO(latest_status_csv))
    latest_status_widget = mo.ui.table(
        latest_status_table.to_dict(orient="records"),
        pagination=False,
        selection=None,
        show_data_types=False,
        max_height=600,
        freeze_columns_left=["date", "session_id"],
    )

    mo.vstack(
        [
            mo.md("## Latest full status table"),
            latest_status_widget,
        ]
    )
    return


if __name__ == "__main__":
    import shutil as _shutil
    import subprocess as _subprocess
    import sys as _sys
    from pathlib import Path as _Path

    if "--serve" in _sys.argv:
        app.run()
    else:
        _marimo = _shutil.which("marimo")
        if _marimo is None:
            raise RuntimeError(
                "Could not find the marimo executable; run with uv or use --serve."
            )
        _notebook_path = _Path(__file__).resolve()
        _repo_root = _Path(
            _subprocess.check_output(
                ["git", "rev-parse", "--show-toplevel"], text=True
            ).strip()
        )
        _output_path = _repo_root / "tables" / "dashboard.html"
        _subprocess.run(
            [
                _marimo,
                "export",
                "html",
                str(_notebook_path),
                "--no-sandbox",
                "--no-include-code",
                "--force",
                "-o",
                str(_output_path),
            ],
            check=True,
        )

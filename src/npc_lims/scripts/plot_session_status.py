#!/usr/bin/env python

# /// script
# requires-python = ">=3.9"
# dependencies = [
#     "plotly>=5.0",
#     "kaleido>=0.2.1",
# ]
# ///

"""Create an interactive Sankey plot from a session-status CSV.

The plot is limited to production sessions by default. Metadata is tracked as
an independent aside, while annotation, video processing, and cache endpoints
show their own dependencies.
"""

from __future__ import annotations

import argparse
import csv
import io
from collections import Counter
from pathlib import Path
from typing import Protocol
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


class FigureLike(Protocol):
    def write_html(self, file: Path, include_plotlyjs: bool) -> None: ...

    def write_image(self, file: Path, format: str) -> None: ...


VIDEO_STATUS_COLUMNS = (
    ("Gamma encoding", "is_gamma_encoding"),
    ("DLC eye", "is_dlc_eye"),
    ("Facemap", "is_facemap"),
    ("LPFaceParts", "is_LPFaceParts"),
)
STALLED_NODES = {
    "Not uploaded",
    "Metadata incomplete",
    "Not sorted",
    "Surface channels not sorted",
    "Not imaged",
    "Not annotated",
    "Missing Gamma encoding",
    "Missing DLC eye",
    "Missing Facemap",
    "Missing LPFaceParts",
    "Parquet not cached",
    "NWB not cached",
}
PARALLEL_BRANCH_WEIGHT = 0.5


def _is_true(value: str | None) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def _filter_rows(
    rows: list[dict[str, str]], production_only: bool
) -> list[dict[str, str]]:
    if not production_only:
        return rows
    return [row for row in rows if _is_true(row.get("is_prod"))]


def _common_path(row: dict[str, str]) -> list[str]:
    """Return the common workflow path, ending at its first stall."""
    path = ["All sessions"]

    if not _is_true(row.get("is_uploaded")):
        return [*path, "Not uploaded"]
    path.append("Uploaded")

    if not _is_true(row.get("is_sorted")):
        return [*path, "Not sorted"]
    path.append("Sorted")

    if row.get("surface_channels_asset_id") and not _is_true(
        row.get("is_surface_channels_sorted")
    ):
        return [*path, "Surface channels not sorted"]

    return path


def session_paths(  # noqa: C901
    row: dict[str, str],
) -> tuple[tuple[tuple[str, ...], float], ...]:
    """Return weighted workflow paths for one session.

    Successful metadata, annotation, and video-processing paths rejoin at
    ``Caching``. Parquet and NWB cache status then branch independently from
    that node; incomplete branches stop at their current status.
    """
    common_path = _common_path(row)
    paths: list[tuple[tuple[str, ...], float]] = [(tuple(common_path), 1.0)]

    if _is_true(row.get("is_uploaded")):
        uploaded_path = ("All sessions", "Uploaded")
        metadata_complete = _is_true(row.get("is_session_json")) and _is_true(
            row.get("is_rig_json")
        )
        metadata_path = [
            *uploaded_path,
            "Metadata",
            "Metadata complete" if metadata_complete else "Metadata incomplete",
        ]
        if metadata_complete:
            metadata_path.append("Caching")
        paths.extend(
            [
                (tuple(metadata_path), PARALLEL_BRANCH_WEIGHT),
                (
                    (
                        *uploaded_path,
                        "Caching",
                        "Parquet cached"
                        if _is_true(row.get("is_parquet_cached"))
                        else "Parquet not cached",
                    ),
                    PARALLEL_BRANCH_WEIGHT,
                ),
                (
                    (
                        *uploaded_path,
                        "Caching",
                        "NWB cached"
                        if _is_true(row.get("is_nwb_cached"))
                        else "NWB not cached",
                    ),
                    PARALLEL_BRANCH_WEIGHT,
                ),
            ]
        )

    if common_path[-1] == "Sorted":
        annotation_path = [*common_path, "Annotation"]
        if not _is_true(row.get("is_imaged")):
            annotation_path.append("Not imaged")
        else:
            annotation_path.append(
                "Annotated" if _is_true(row.get("is_annotated")) else "Not annotated"
            )
            if annotation_path[-1] == "Annotated":
                annotation_path.append("Caching")
        paths.append((tuple(annotation_path), PARALLEL_BRANCH_WEIGHT))

    video_path = ["All sessions"]
    if not _is_true(row.get("is_uploaded")):
        pass
    elif not _is_true(row.get("is_video")):
        video_path.append("Uploaded")
        video_path.append("Video processing")
        video_path.append("No video")
        video_path.append("Caching")
        paths.append((tuple(video_path), PARALLEL_BRANCH_WEIGHT))
    else:
        video_path.extend(("Uploaded", "Video processing"))
        # DLC and Facemap depend only on upload/video. LPFaceParts depends on
        # gamma encoding, so it gets its own branch from the same prerequisite.
        gamma_complete = _is_true(row.get("is_gamma_encoding"))
        for process_name, column in VIDEO_STATUS_COLUMNS:
            if process_name == "Gamma encoding":
                continue
            process_path = [*video_path]
            if process_name == "LPFaceParts":
                process_path.append(
                    "Gamma encoding" if gamma_complete else "Missing Gamma encoding"
                )
                if not gamma_complete:
                    paths.append((tuple(process_path), PARALLEL_BRANCH_WEIGHT / 3))
                    continue
            process_path.append(
                process_name if _is_true(row.get(column)) else f"Missing {process_name}"
            )
            if process_path[-1] == process_name:
                process_path.extend(("Video processing complete", "Caching"))
            paths.append((tuple(process_path), PARALLEL_BRANCH_WEIGHT / 3))

    return tuple(paths)


def build_links(
    rows: list[dict[str, str]],
) -> tuple[list[str], list[int], list[int], list[float], Counter[str]]:
    """Aggregate weighted session paths into Sankey node and link data."""
    link_counts: dict[tuple[str, str], float] = {}
    node_counts: Counter[str] = Counter()
    for row in rows:
        paths = session_paths(row)
        seen_nodes: set[str] = set()
        for path, weight in paths:
            node_counts.update(node for node in path if node not in seen_nodes)
            seen_nodes.update(path)
            for link in zip(path, path[1:]):
                link_counts[link] = link_counts.get(link, 0.0) + weight

    nodes = list(node_counts)
    node_index = {node: index for index, node in enumerate(nodes)}
    source: list[int] = []
    target: list[int] = []
    values: list[float] = []
    for (from_node, to_node), count in link_counts.items():
        source.append(node_index[from_node])
        target.append(node_index[to_node])
        values.append(count)
    return nodes, source, target, values, node_counts


def make_plot(
    rows: list[dict[str, str]], input_source: str, *, production_only: bool = True
) -> FigureLike:
    """Build the Plotly Sankey figure."""
    try:
        import plotly.graph_objects as go
    except ImportError:
        raise ImportError(
            "plotly is required: run `uv run --script "
            "src/npc_lims/scripts/plot_session_status.py`"
        ) from None

    rows = _filter_rows(rows, production_only)
    nodes, source, target, values, node_counts = build_links(rows)
    labels = [f"{node}<br><sup>n={node_counts[node]}</sup>" for node in nodes]
    session_link_counts: Counter[tuple[str, str]] = Counter()
    for row in rows:
        for path, _ in session_paths(row):
            session_link_counts.update(zip(path, path[1:]))
    link_sessions = [
        session_link_counts[(nodes[from_index], nodes[to_index])]
        for from_index, to_index in zip(source, target)
    ]
    terminal_nodes = [node for node in nodes if node in STALLED_NODES]
    colors = ["#d95f02" if node in terminal_nodes else "#4c78a8" for node in nodes]
    return go.Figure(
        go.Sankey(
            arrangement="snap",
            node={
                "label": labels,
                "color": colors,
                # Keep every node on the left side of the plot so Plotly renders
                # every label to the right of its proportion bar.
                "align": "left",
                "pad": 20,
                "thickness": 20,
                "line": {"color": "white", "width": 0.5},
                "hovertemplate": "%{label}<extra></extra>",
            },
            link={
                "source": source,
                "target": target,
                "value": values,
                "customdata": link_sessions,
                "hovertemplate": "%{source.label} → %{target.label}<br>"
                "Sessions: %{customdata}<br>"
                "Weighted flow: %{value}<extra></extra>",
            },
        )
    ).update_layout(
        title=(
            f"Session status ({len(rows):,} sessions; "
            f"is_prod={'true' if production_only else 'any'})\n{input_source}"
        ),
        font={"size": 12},
        margin={"l": 20, "r": 20, "t": 80, "b": 20},
    )


def _github_blob_to_raw(source: str) -> str:
    """Convert a normal GitHub file URL to its raw-content equivalent."""
    parsed = urlsplit(source)
    parts = parsed.path.strip("/").split("/")
    if parsed.netloc == "github.com" and len(parts) >= 5 and parts[2] == "blob":
        return (
            "https://raw.githubusercontent.com/"
            f"{parts[0]}/{parts[1]}/{'/'.join(parts[3:])}"
        )
    return source


def read_rows(source: str) -> list[dict[str, str]]:
    """Read status rows from a local CSV or an HTTP(S) CSV URL."""
    if urlsplit(source).scheme in {"http", "https"}:
        request = Request(
            _github_blob_to_raw(source),
            headers={"User-Agent": "npc-lims-session-status"},
        )
        with urlopen(request) as response:
            text = response.read().decode("utf-8-sig")
        return list(csv.DictReader(io.StringIO(text)))

    with Path(source).open(newline="") as file:
        return list(csv.DictReader(file))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "input_csv",
        nargs="?",
        default="tables/status.csv",
        help="Session status CSV path or GitHub URL (default: tables/status.csv)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("session_status_sankey.html"),
        help="Output HTML path (default: session_status_sankey.html)",
    )
    parser.add_argument(
        "--png",
        type=Path,
        help="Additionally write a PNG image to this path",
    )
    parser.add_argument(
        "--svg",
        type=Path,
        help="Additionally write an SVG image to this path",
    )
    parser.add_argument(
        "--all-sessions",
        action="store_true",
        help="Include non-production sessions (default: production only)",
    )
    args = parser.parse_args()

    rows = read_rows(args.input_csv)
    if not rows:
        raise ValueError(f"No session rows found in {args.input_csv}")

    production_only = not args.all_sessions
    figure = make_plot(rows, args.input_csv, production_only=production_only)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    figure.write_html(args.output, include_plotlyjs=True)
    session_count = len(_filter_rows(rows, production_only))
    print(f"Wrote interactive Sankey for {session_count:,} sessions to {args.output}")
    for image_path, image_format in ((args.png, "png"), (args.svg, "svg")):
        if image_path is None:
            continue
        image_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            figure.write_image(image_path, format=image_format)
        except (ImportError, ValueError) as exc:
            raise RuntimeError(
                "Static image export requires Kaleido. Run with "
                "`uv run --script ...` or install `kaleido`."
            ) from exc
        print(f"Wrote {image_format.upper()} Sankey to {image_path}")


if __name__ == "__main__":
    main()

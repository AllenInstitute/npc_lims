#!/usr/bin/env python

# /// script
# requires-python = ">=3.9"
# dependencies = [
#     "plotly>=5.0",
#     "kaleido>=0.2.1",
# ]
# ///

"""Create an interactive Sankey plot from a session-status CSV.

Each session is assigned to the first incomplete stage in the workflow. This
makes the terminal stalled counts mutually exclusive rather than counting a
session once for every missing status.
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
    "Missing session/rig JSON",
    "Not sorted",
    "Surface channels not sorted",
    "Not annotated",
    "Missing Gamma encoding",
    "Missing DLC eye",
    "Missing Facemap",
    "Missing LPFaceParts",
}


def _is_true(value: str | None) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def session_path(row: dict[str, str]) -> tuple[str, ...]:
    """Return the workflow path for one session, ending at its first stall."""
    path = ["All sessions"]

    if not _is_true(row.get("is_uploaded")):
        return (*path, "Not uploaded")
    path.append("Uploaded")

    if not (
        _is_true(row.get("is_session_json"))
        and _is_true(row.get("is_rig_json"))
    ):
        return (*path, "Missing session/rig JSON")
    path.append("Metadata complete")

    if not _is_true(row.get("is_sorted")):
        return (*path, "Not sorted")
    path.append("Sorted")

    if row.get("surface_channels_asset_id") and not _is_true(
        row.get("is_surface_channels_sorted")
    ):
        return (*path, "Surface channels not sorted")

    if not _is_true(row.get("is_annotated")):
        return (*path, "Not annotated")
    path.append("Annotated")

    if not _is_true(row.get("is_video")):
        return (*path, "Complete (no video)")
    path.append("Video")

    for process_name, column in VIDEO_STATUS_COLUMNS:
        if not _is_true(row.get(column)):
            return (*path, f"Missing {process_name}")
    return (*path, "Complete")


def build_links(
    rows: list[dict[str, str]],
) -> tuple[list[str], list[int], list[int], list[int], Counter[str]]:
    """Aggregate session paths into Sankey node and link data."""
    link_counts: Counter[tuple[str, str]] = Counter()
    node_counts: Counter[str] = Counter()
    for row in rows:
        path = session_path(row)
        node_counts.update(path)
        link_counts.update(zip(path, path[1:]))

    nodes = list(node_counts)
    node_index = {node: index for index, node in enumerate(nodes)}
    source: list[int] = []
    target: list[int] = []
    values: list[int] = []
    for (from_node, to_node), count in link_counts.items():
        source.append(node_index[from_node])
        target.append(node_index[to_node])
        values.append(count)
    return nodes, source, target, values, node_counts


def make_plot(rows: list[dict[str, str]], input_source: str) -> FigureLike:
    """Build the Plotly Sankey figure."""
    try:
        import plotly.graph_objects as go
    except ImportError:
        raise ImportError(
            "plotly is required: run `uv run --script "
            "src/npc_lims/scripts/plot_session_status.py`"
        ) from None

    nodes, source, target, values, node_counts = build_links(rows)
    labels = [f"{node}<br><sup>n={node_counts[node]}</sup>" for node in nodes]
    terminal_nodes = [node for node in nodes if node in STALLED_NODES]
    colors = [
        "#d95f02" if node in terminal_nodes else "#4c78a8" for node in nodes
    ]
    return go.Figure(
        go.Sankey(
            arrangement="snap",
            node={
                "label": labels,
                "color": colors,
                "pad": 20,
                "thickness": 20,
                "line": {"color": "white", "width": 0.5},
                "hovertemplate": "%{label}<extra></extra>",
            },
            link={
                "source": source,
                "target": target,
                "value": values,
                "hovertemplate": "%{source.label} → %{target.label}<br>"
                "Sessions: %{value}<extra></extra>",
            },
        )
    ).update_layout(
        title=f"Session status ({len(rows):,} sessions)\n{input_source}",
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
    args = parser.parse_args()

    rows = read_rows(args.input_csv)
    if not rows:
        raise ValueError(f"No session rows found in {args.input_csv}")

    figure = make_plot(rows, args.input_csv)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    figure.write_html(args.output, include_plotlyjs=True)
    print(f"Wrote interactive Sankey for {len(rows):,} sessions to {args.output}")
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

from __future__ import annotations

import argparse
from typing import Literal

import npc_lims


def setup() -> dict[
    Literal[
        "capsule_or_pipeline_id",
        "process_name",
        "create_data_assets_from_results",
        "rerun_all_jobs",
        "is_pipeline",
        "rerun_errored_jobs",
        "overwrite_existing_assets",
    ],
    str | bool | None,
]:
    args = parse_args()
    kwargs = vars(args)

    return kwargs  # type: ignore[return-value]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--capsule_or_pipeline_id",
        required=True,
        help="Capsule or pipeline id",
    )
    parser.add_argument(
        "--process_name",
        required=True,
        help="Process name of capsule or pipeline",
    )

    parser.add_argument(
        "--max_running_jobs",
        type=int,
        default=6,
        help="Maximum number of jobs to run to not overload",
    )
    parser.add_argument(
        "--create_data_assets_from_results",
        type=bool,
        default=True,
        help="Whether or not to create data assets from results",
    )
    parser.add_argument(
        "--rerun_all_jobs",
        type=bool,
        default=False,
        help="Rereun all sessions for capsule or pipeline",
    )

    parser.add_argument(
        "--is_pipeline",
        type=bool,
        default=False,
        help="Whether or not capsule or pipeline",
    )

    parser.add_argument(
        "--rerun_errored_jobs", type=bool, default=False, help="Rerun jobs that failed"
    )

    parser.add_argument(
        "--overwrite_existing_assets",
        type=bool,
        default=False,
        help="Overwrite existing assets for capsule or pipeline results",
    )

    return parser.parse_args()


def main() -> None:
    kwargs = setup()
    npc_lims.process_capsule_or_pipeline_queue(**kwargs)  # type: ignore[misc, arg-type]


if __name__ == "__main__":
    main()

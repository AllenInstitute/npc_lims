"""Reconcile ephys upload batches with the experiment tracking workbook.

The experiment tracking workbook is authoritative when it supplies a value.
``session_config.json`` fills gaps, and existing YAML values are preserved for
fields that neither source controls.
"""

from __future__ import annotations

import argparse
import dataclasses
import datetime
import json
import os
import pathlib
import re
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence

import openpyxl
import yaml
from openpyxl.worksheet._read_only import ReadOnlyWorksheet
from openpyxl.worksheet.worksheet import Worksheet

PROBE_LETTERS = "ABCDEF"
DEEP_INSERTION_THRESHOLD_UM = 3800
PROJECT_NAMES = {
    "dr": "DynamicRouting",
    "dynamicrouting": "DynamicRouting",
    "templeton": "TempletonPilotSession",
    "templetonpilotsession": "TempletonPilotSession",
}
SESSION_PATTERN = re.compile(
    r"(?:DRpilot_)?(?P<subject>\d{6})_(?P<year>\d{4})-?"
    r"(?P<month>\d{2})-?(?P<day>\d{2})",
    re.IGNORECASE,
)
UPLOAD_PATTERN = re.compile(
    r"^\s*upload_dr_ecephys\s+[\"']?(?P<path>.+?)[\"']?\s*$",
    re.IGNORECASE,
)

_CONTROLLED_SESSION_KWARGS = (
    "perturbation_day",
    "is_production",
    "is_split_recording",
    "is_context_naive",
    "is_injection_perturbation",
    "is_opto_perturbation",
    "is_deep_insertion",
    "probe_letters_to_skip",
    "surface_recording_probe_letters_to_skip",
)


def _mapping(value: object) -> dict[str, object]:
    if not isinstance(value, Mapping):
        return {}
    return {str(key): item for key, item in value.items()}


@dataclasses.dataclass(frozen=True)
class SessionKey:
    subject: int
    date: datetime.date

    @property
    def compact(self) -> str:
        return f"{self.subject}_{self.date:%Y%m%d}"


@dataclasses.dataclass(frozen=True)
class Conflict:
    session: str
    field: str
    spreadsheet: object
    session_config: object


@dataclasses.dataclass
class ReconciledSession:
    path: str
    project: str
    ephys_day: int
    perturbation_day: int | None = None
    is_production: bool = True
    is_split_recording: bool = False
    is_context_naive: bool = False
    is_injection_perturbation: bool = False
    is_opto_perturbation: bool = False
    is_deep_insertion: bool = False
    probe_letters_to_skip: str | None = None
    surface_recording_probe_letters_to_skip: str | None = None
    notes: str = ""
    spreadsheet_sources: tuple[str, ...] = ()
    authoritative_fields: frozenset[str] = frozenset()

    @property
    def key(self) -> SessionKey:
        return session_key(self.path)

    def yaml_config(  # noqa: C901
        self, existing: Mapping[str, object] | None = None
    ) -> dict[str, object]:
        """Return the YAML value for this session, preserving unrelated data."""
        result = dict(existing or {})
        result.pop("day", None)
        result["ephys_day"] = self.ephys_day

        if self.notes:
            old_notes = str(result.get("notes") or "").strip()
            if old_notes and self.notes not in old_notes:
                result["notes"] = f"{old_notes}; {self.notes}"
            else:
                result["notes"] = old_notes or self.notes

        session_kwargs = _mapping(result.get("session_kwargs"))
        if "perturbation_day" in result:
            session_kwargs.setdefault(
                "perturbation_day", result.pop("perturbation_day")
            )
        for field in self.authoritative_fields:
            if field in _CONTROLLED_SESSION_KWARGS:
                session_kwargs.pop(field, None)

        overrides: dict[str, object] = {}
        if (
            "perturbation_day" in self.authoritative_fields
            and self.perturbation_day is not None
        ):
            overrides["perturbation_day"] = self.perturbation_day
        if "is_production" in self.authoritative_fields and not self.is_production:
            overrides["is_production"] = False
        if (
            "is_split_recording" in self.authoritative_fields
            and self.is_split_recording
        ):
            overrides["is_split_recording"] = True
        if "is_context_naive" in self.authoritative_fields and self.is_context_naive:
            overrides["is_context_naive"] = True
        if (
            "is_injection_perturbation" in self.authoritative_fields
            and self.is_injection_perturbation
        ):
            overrides["is_injection_perturbation"] = True
        if (
            "is_opto_perturbation" in self.authoritative_fields
            and self.is_opto_perturbation
        ):
            overrides["is_opto_perturbation"] = True
        if "is_deep_insertion" in self.authoritative_fields and self.is_deep_insertion:
            overrides["is_deep_insertion"] = True
        if (
            "probe_letters_to_skip" in self.authoritative_fields
            and self.probe_letters_to_skip
        ):
            overrides["probe_letters_to_skip"] = self.probe_letters_to_skip
        if (
            "surface_recording_probe_letters_to_skip" in self.authoritative_fields
            and self.surface_recording_probe_letters_to_skip
        ):
            overrides["surface_recording_probe_letters_to_skip"] = (
                self.surface_recording_probe_letters_to_skip
            )
        session_kwargs.update(overrides)
        if session_kwargs:
            result["session_kwargs"] = session_kwargs
        else:
            result.pop("session_kwargs", None)

        order = ("ephys_day", "notes", "issues", "session_kwargs")
        return {key: result[key] for key in (*order, *result) if key in result}


@dataclasses.dataclass
class _SpreadsheetEvidence:
    values: dict[str, object] = dataclasses.field(default_factory=dict)
    sources: list[str] = dataclasses.field(default_factory=list)
    notes: list[str] = dataclasses.field(default_factory=list)
    surface_recording: bool | None = None


def session_key(value: str) -> SessionKey:
    match = SESSION_PATTERN.search(value)
    if match is None:
        raise ValueError(f"No session ID found in {value!r}")
    return SessionKey(
        subject=int(match.group("subject")),
        date=datetime.date(
            int(match.group("year")),
            int(match.group("month")),
            int(match.group("day")),
        ),
    )


def get_uncommented_upload_paths(batch_path: str | os.PathLike[str]) -> tuple[str, ...]:
    """Return only active ``upload_dr_ecephys`` commands from a batch file."""
    paths = []
    for line in pathlib.Path(batch_path).read_text(encoding="utf-8").splitlines():
        if match := UPLOAD_PATTERN.match(line):
            paths.append(match.group("path"))
    return tuple(paths)


def _normalize_header(value: object) -> str | None:
    return str(value).strip().lower() if value is not None else None


def _rows_by_header(
    worksheet: Worksheet | ReadOnlyWorksheet,
) -> Iterable[tuple[int, dict[str, object]]]:
    rows = worksheet.iter_rows(values_only=True)
    headers = tuple(_normalize_header(value) for value in next(rows))
    for row_number, row in enumerate(rows, 2):
        yield row_number, {
            header: value for header, value in zip(headers, row) if header is not None
        }


def _as_date(value: object) -> datetime.date | None:
    if isinstance(value, datetime.datetime):
        return value.date()
    return value if isinstance(value, datetime.date) else None


def _project_name(value: object) -> str | None:
    if value is None:
        return None
    normalized = re.sub(r"[^a-z]", "", str(value).lower())
    return PROJECT_NAMES.get(normalized)


def _probe_letters(value: object) -> set[str] | None:
    if value is None:
        return None
    normalized = re.sub(r"[^A-Z]", "", str(value).upper())
    if normalized in {"", "X", "NONE", "NOPROBES"}:
        return None
    if set(normalized) <= set(PROBE_LETTERS):
        return set(normalized)
    return None


def _probes_from_locations(row: Mapping[str, object]) -> set[str]:
    probes = set()
    for letter in PROBE_LETTERS:
        location = row.get(f"{letter.lower()} loc")
        depth = row.get(f"{letter.lower()} depth")
        if isinstance(depth, (int, float)) and depth > 0:
            probes.add(letter)
        elif location is not None and str(location).strip().lower() not in {
            "",
            "x",
            "n/a",
            "none",
        }:
            probes.add(letter)
    return probes


def _skip_letters(recorded: set[str]) -> str | None:
    result = "".join(letter for letter in PROBE_LETTERS if letter not in recorded)
    return result or None


def _combine_letters(*values: object) -> str | None:
    letters = {
        letter
        for value in values
        if value
        for letter in str(value).upper()
        if letter in PROBE_LETTERS
    }
    result = "".join(letter for letter in PROBE_LETTERS if letter in letters)
    return result or None


def _is_deep_insertion(depths_um: Iterable[float]) -> bool:
    return max(depths_um) > DEEP_INSERTION_THRESHOLD_UM


def _recorded_dates(row: Mapping[str, object]) -> tuple[datetime.date, ...]:
    value = row.get("days recorded")
    week_of = _as_date(row.get("week of"))
    if value is None or week_of is None:
        return ()
    result = []
    year = week_of.year
    previous_month = None
    for month_text, day_text, explicit_year in re.findall(
        r"(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?", str(value)
    ):
        month = int(month_text)
        if explicit_year:
            year = int(explicit_year)
            if year < 100:
                year += 2000
        elif previous_month is not None and previous_month >= 11 and month <= 2:
            year += 1
        result.append(datetime.date(year, month, int(day_text)))
        previous_month = month
    return tuple(result)


def _production_from_experiment_type(value: object) -> bool | None:
    if value is None:
        return None
    text = str(value).lower()
    if any(token in text for token in ("prod", "standard", "naive", "templeton")):
        return True
    if any(
        token in text
        for token in ("test", "muscimol", "opto", "virus", "enhancer", "dye")
    ):
        return False
    return None


def _load_session_config(path: str) -> dict[str, object]:
    local_path = path
    if os.name == "nt" and path.startswith("//"):
        local_path = "\\\\" + path[2:].replace("/", "\\")
    config_path = pathlib.Path(local_path) / "session_config.json"
    if not config_path.is_file():
        return {}
    return json.loads(config_path.read_text(encoding="utf-8"))


def _preferred_value(
    spreadsheet: Mapping[str, object],
    session_config: Mapping[str, object],
    field: str,
    default: object,
) -> object:
    if field in spreadsheet:
        return spreadsheet[field]
    return session_config.get(field, default)


def _optional_int(value: object) -> int | None:
    return None if value is None else int(str(value))


def _required_int(value: object) -> int:
    result = _optional_int(value)
    if result is None:
        raise ValueError("Expected an integer, got None")
    return result


def _spreadsheet_evidence(  # noqa: C901
    workbook_path: str | os.PathLike[str], upload_paths: Sequence[str]
) -> dict[SessionKey, _SpreadsheetEvidence]:
    workbook = openpyxl.load_workbook(workbook_path, read_only=True, data_only=True)
    keys = tuple(session_key(path) for path in upload_paths)
    active_dates_by_subject: dict[int, set[datetime.date]] = defaultdict(set)
    for key in keys:
        active_dates_by_subject[key.subject].add(key.date)

    mouse_rows: dict[int, dict[str, object]] = {}
    recorded_dates_by_subject: dict[int, tuple[datetime.date, ...]] = {}
    for _row_number, row in _rows_by_header(workbook["by_mouse"]):
        mouse = row.get("mouse")
        if not isinstance(mouse, int) or mouse not in active_dates_by_subject:
            continue
        mouse_rows[mouse] = row
        recorded_dates_by_subject[mouse] = _recorded_dates(row)

    session_rows: dict[SessionKey, list[tuple[str, int, dict[str, object]]]] = (
        defaultdict(list)
    )
    workbook_dates_by_subject: dict[int, set[datetime.date]] = defaultdict(set)
    for sheet_name in ("by_session_prod", "by_session_muscimol", "by_session_other"):
        for row_number, row in _rows_by_header(workbook[sheet_name]):
            mouse = row.get("mouse", row.get("mid"))
            date = _as_date(row.get("date"))
            if not isinstance(mouse, int) or date is None:
                continue
            workbook_dates_by_subject[mouse].add(date)
            key = SessionKey(mouse, date)
            if key in keys:
                session_rows[key].append((sheet_name, row_number, row))

    evidence_by_key = {}
    for key in keys:
        evidence = _SpreadsheetEvidence()
        mouse_row = mouse_rows.get(key.subject, {})
        if project := _project_name(mouse_row.get("project")):
            evidence.values["project"] = project
            evidence.sources.append(f"by_mouse!project ({key.subject})")

        experiment_type = mouse_row.get("exp type")
        if production := _production_from_experiment_type(experiment_type):
            evidence.values["is_production"] = production
        elif production is False:
            evidence.values["is_production"] = False
        if experiment_type is not None:
            text = str(experiment_type).lower()
            evidence.values["is_context_naive"] = "naive" in text
            evidence.values["is_opto_perturbation"] = any(
                token in text for token in ("opto", "virus", "enhancer")
            )
            evidence.sources.append(f"by_mouse!exp type ({experiment_type})")

        recorded_dates = recorded_dates_by_subject.get(key.subject, ())
        if key.date in recorded_dates:
            evidence.values["ephys_day"] = recorded_dates.index(key.date) + 1
            evidence.sources.append(f"by_mouse!days recorded ({key.subject})")
        else:
            fallback_dates = sorted(
                active_dates_by_subject[key.subject]
                | workbook_dates_by_subject.get(key.subject, set())
            )
            if key.date in fallback_dates:
                evidence.values["ephys_day"] = fallback_dates.index(key.date) + 1

        rows = session_rows.get(key, [])
        recorded_probes: set[str] = set()
        has_probe_evidence = False
        depths: list[float] = []
        surface_values: list[bool] = []
        is_injection = False
        split_recording = False
        for sheet_name, row_number, row in rows:
            evidence.sources.append(f"{sheet_name}!row {row_number}")
            probes = _probe_letters(row.get("probes in brain", row.get("probes")))
            inferred_probes = _probes_from_locations(row)
            if probes:
                recorded_probes.update(probes)
                has_probe_evidence = True
            elif inferred_probes:
                recorded_probes.update(inferred_probes)
                has_probe_evidence = True
            for letter in PROBE_LETTERS:
                depth = row.get(f"{letter.lower()} depth")
                if isinstance(depth, (int, float)):
                    depths.append(float(depth))
            surface = row.get("surface channel recording")
            if isinstance(surface, bool):
                surface_values.append(surface)
            if row.get("injection substance") not in (None, ""):
                substance = str(row["injection substance"]).lower()
                is_injection = not any(
                    token in substance for token in ("control", "acsf")
                )
            note = str(row.get("notes") or "").strip()
            if note and note not in evidence.notes:
                evidence.notes.append(note)
            split_recording |= "split" in note.lower()
            other_experiment = str(row.get("exp") or "").lower()
            if any(token in other_experiment for token in ("opto", "jaws", "virus")):
                evidence.values["is_opto_perturbation"] = True

        if has_probe_evidence:
            evidence.values["probe_letters_to_skip"] = _skip_letters(recorded_probes)
        if depths:
            evidence.values["is_deep_insertion"] = _is_deep_insertion(depths)
        if surface_values:
            evidence.surface_recording = any(surface_values)
        if rows and any(name == "by_session_muscimol" for name, _, _ in rows):
            evidence.values["is_injection_perturbation"] = is_injection
        if split_recording:
            evidence.values["is_split_recording"] = True

        if evidence.values.get("is_injection_perturbation") or evidence.values.get(
            "is_opto_perturbation"
        ):
            evidence.values["perturbation_day"] = evidence.values.get("ephys_day")
        evidence_by_key[key] = evidence
    return evidence_by_key


def reconcile_upload_batch(
    batch_path: str | os.PathLike[str],
    workbook_path: str | os.PathLike[str],
) -> tuple[tuple[ReconciledSession, ...], tuple[Conflict, ...]]:
    """Reconcile active batch entries, preferring spreadsheet metadata."""
    upload_paths = get_uncommented_upload_paths(batch_path)
    evidence_by_key = _spreadsheet_evidence(workbook_path, upload_paths)
    sessions = []
    conflicts = []
    for path in upload_paths:
        key = session_key(path)
        spreadsheet = evidence_by_key[key]
        config = _load_session_config(path)
        authoritative_fields = set(spreadsheet.values) | set(config)

        for field, spreadsheet_value in spreadsheet.values.items():
            if field in config and config[field] != spreadsheet_value:
                conflicts.append(
                    Conflict(key.compact, field, spreadsheet_value, config[field])
                )

        probe_skip = _preferred_value(
            spreadsheet.values, config, "probe_letters_to_skip", None
        )
        surface_skip = config.get("surface_recording_probe_letters_to_skip")
        if spreadsheet.surface_recording is True:
            surface_skip = _combine_letters(surface_skip, probe_skip)
            authoritative_fields.add("surface_recording_probe_letters_to_skip")
        elif spreadsheet.surface_recording is False:
            surface_skip = None
            authoritative_fields.add("surface_recording_probe_letters_to_skip")

        sessions.append(
            ReconciledSession(
                path=path,
                project=str(
                    _preferred_value(
                        spreadsheet.values, config, "project", "DynamicRouting"
                    )
                ),
                ephys_day=_required_int(
                    _preferred_value(spreadsheet.values, config, "ephys_day", 1)
                ),
                perturbation_day=_optional_int(
                    _preferred_value(
                        spreadsheet.values, config, "perturbation_day", None
                    )
                ),
                is_production=bool(
                    _preferred_value(spreadsheet.values, config, "is_production", True)
                ),
                is_split_recording=bool(
                    _preferred_value(
                        spreadsheet.values, config, "is_split_recording", False
                    )
                ),
                is_context_naive=bool(
                    _preferred_value(
                        spreadsheet.values, config, "is_context_naive", False
                    )
                ),
                is_injection_perturbation=bool(
                    _preferred_value(
                        spreadsheet.values,
                        config,
                        "is_injection_perturbation",
                        False,
                    )
                ),
                is_opto_perturbation=bool(
                    _preferred_value(
                        spreadsheet.values, config, "is_opto_perturbation", False
                    )
                ),
                is_deep_insertion=bool(
                    _preferred_value(
                        spreadsheet.values, config, "is_deep_insertion", False
                    )
                ),
                probe_letters_to_skip=(str(probe_skip) if probe_skip else None),
                surface_recording_probe_letters_to_skip=(
                    str(surface_skip) if surface_skip else None
                ),
                notes="; ".join(spreadsheet.notes),
                spreadsheet_sources=tuple(spreadsheet.sources),
                authoritative_fields=frozenset(authoritative_fields),
            )
        )
    return tuple(sessions), tuple(conflicts)


def _existing_entries(
    contents: Mapping[str, object], keys: set[SessionKey]
) -> dict[SessionKey, dict[str, object]]:
    existing: dict[SessionKey, dict[str, object]] = {}
    for project_entries in _mapping(contents.get("ephys")).values():
        if not isinstance(project_entries, Sequence) or isinstance(
            project_entries, str
        ):
            continue
        for item in project_entries:
            if not isinstance(item, Mapping):
                continue
            path, config = next(iter(item.items()))
            try:
                key = session_key(str(path))
            except ValueError:
                continue
            if key not in keys:
                continue
            merged = existing.setdefault(key, {})
            current = _mapping(config)
            kwargs = _mapping(merged.get("session_kwargs"))
            kwargs.update(_mapping(current.pop("session_kwargs", None)))
            merged.update(current)
            if kwargs:
                merged["session_kwargs"] = kwargs
    return existing


def render_yaml_entries(
    sessions: Sequence[ReconciledSession],
    tracked_sessions_path: str | os.PathLike[str],
) -> dict[str, str]:
    """Render reconciled entries grouped by their YAML project heading."""
    path = pathlib.Path(tracked_sessions_path)
    contents = yaml.safe_load(path.read_text(encoding="utf-8"))
    existing = _existing_entries(contents, {session.key for session in sessions})
    grouped: dict[str, list[str]] = defaultdict(list)
    for session in sessions:
        value = session.yaml_config(existing.get(session.key))
        rendered = yaml.safe_dump(
            [{session.path: value}],
            sort_keys=False,
            allow_unicode=True,
            width=1000,
            indent=2,
        ).rstrip()
        grouped[session.project].append(
            "\n".join(f"    {line}" for line in rendered.splitlines())
        )
    return {project: "\n\n".join(entries) for project, entries in grouped.items()}


def update_tracked_sessions_text(
    sessions: Sequence[ReconciledSession],
    tracked_sessions_path: str | os.PathLike[str],
) -> str:
    """Return updated YAML text with one entry per reconciled session.

    Entry-level text replacement preserves comments and formatting elsewhere in
    the hand-maintained YAML file.
    """
    path = pathlib.Path(tracked_sessions_path)
    lines = path.read_text(encoding="utf-8").splitlines()
    keys = {session.key for session in sessions}
    ephys_start = next(i for i, line in enumerate(lines) if line == "ephys:")
    ephys_end = next(
        i
        for i in range(ephys_start + 1, len(lines))
        if re.match(r"^[A-Za-z_][^:]*:", lines[i])
    )

    spans = []
    entry_indexes = [
        i for i in range(ephys_start + 1, ephys_end) if lines[i].startswith("    - ")
    ]
    for position, start in enumerate(entry_indexes):
        end = (
            entry_indexes[position + 1]
            if position + 1 < len(entry_indexes)
            else ephys_end
        )
        for candidate in range(start + 1, end):
            if lines[candidate].startswith("  ") and not lines[candidate].startswith(
                "    "
            ):
                end = candidate
                break
        try:
            key = session_key(lines[start])
        except ValueError:
            continue
        if key in keys:
            spans.append((start, end))
    for start, end in reversed(spans):
        del lines[start:end]

    snippets = render_yaml_entries(sessions, tracked_sessions_path)
    for project in ("DynamicRouting", "TempletonPilotSession"):
        snippet = snippets.get(project)
        if not snippet:
            continue
        heading = f"  {project}:"
        start = next(i for i, line in enumerate(lines) if line == heading)
        end = next(
            (
                i
                for i in range(start + 1, len(lines))
                if re.match(r"^[A-Za-z_][^:]*:", lines[i])
                or (re.match(r"^  [A-Za-z_][^:]*:", lines[i]) is not None)
            ),
            len(lines),
        )
        while end > start + 1 and not lines[end - 1].strip():
            del lines[end - 1]
            end -= 1
        addition = ["", *snippet.splitlines()]
        lines[end:end] = addition
    return "\n".join(lines).rstrip() + "\n"


def _main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("batch_path", type=pathlib.Path)
    parser.add_argument("workbook_path", type=pathlib.Path)
    parser.add_argument("tracked_sessions_path", type=pathlib.Path)
    parser.add_argument(
        "--write",
        action="store_true",
        help="write the reconciled YAML; otherwise print entries and conflicts",
    )
    args = parser.parse_args()
    sessions, conflicts = reconcile_upload_batch(args.batch_path, args.workbook_path)
    if args.write:
        args.tracked_sessions_path.write_text(
            update_tracked_sessions_text(sessions, args.tracked_sessions_path),
            encoding="utf-8",
        )
    else:
        print(json.dumps([dataclasses.asdict(item) for item in conflicts], indent=2))
        for project, entries in render_yaml_entries(
            sessions, args.tracked_sessions_path
        ).items():
            print(f"\n# {project}\n{entries}")


if __name__ == "__main__":
    _main()

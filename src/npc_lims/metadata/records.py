from __future__ import annotations

import dataclasses
from typing import ClassVar, Literal, Union

import npc_session
from typing_extensions import Self

NWBType = Union[str, int, float, None, list]
DBType = Union[str, int, float, None]


@dataclasses.dataclass
class Record:
    db_excl: ClassVar[tuple[str, ...]] = (
        "db_excl",
        "nwb_excl",
        "table",
    )

    @property
    def db(self) -> dict[str, DBType]:
        row = self.__dict__.copy()
        for k, v in row.items():
            if k in self.db_excl:
                del row[k]
                continue
            if not isinstance(v, (str, int, float, type(None))):
                row[k] = str(v)
        return row

    @classmethod
    def from_db(cls, row: dict[str, str | int | float | None]) -> Self:
        for k, v in row.items():
            if not isinstance(v, str):
                continue
            if all(ends in "()[]{{}}" for ends in (v[0], v[-1])):
                row[k] = eval(v)
        return cls(**row)


@dataclasses.dataclass
class RecordWithNWB(Record):
    nwb_excl: ClassVar[tuple[str, ...]] = (
        "db_excl",
        "nwb_excl",
        "table",
    )

    @property
    def nwb(self) -> dict[str, NWBType]:
        nwb = {}
        for k, v in self.__dict__.items():
            if k in self.nwb_excl:
                continue
            if isinstance(v, (str, int, float, type(None), list)):
                nwb[k] = v
            else:
                nwb[k] = str(v)
        return nwb


@dataclasses.dataclass
class Subject(RecordWithNWB):
    """
    >>> from npc_lims import tracked, NWBSqliteDBHub as DB
    >>> all_subjects = DB().get_records(Subject)
    """

    db_excl: ClassVar[tuple[str, ...]] = (
        *RecordWithNWB.db_excl,
        "age",  # depends on session
        "species",  # fixed
    )

    table: ClassVar[str] = "subjects"

    subject_id: int | npc_session.SubjectRecord
    sex: Literal["M", "F", "U"] | None = None
    date_of_birth: str | npc_session.DateRecord | None = None
    genotype: str | None = None
    """e.g., Sst-IRES-Cre/wt;Ai148(TIT2L-GC6f-ICL-tTA2)/wt"""
    description: str | None = None
    strain: str | None = None
    """e.g., C57BL/6J"""
    notes: str | None = None
    species: str = "Mus musculus"
    age: str | None = None


@dataclasses.dataclass
class Session(RecordWithNWB):
    """
    >>> from npc_lims import tracked, NWBSqliteDBHub as DB
    >>> all_sessions = DB().get_records(Session)
    """

    nwb_excl: ClassVar[tuple[str, ...]] = (
        *RecordWithNWB.nwb_excl,
        "subject_id",
    )

    table: ClassVar[str] = "sessions"

    session_id: str | npc_session.SessionRecord
    subject_id: int | npc_session.SubjectRecord
    session_start_time: str | npc_session.DatetimeRecord | None = None
    stimulus_notes: str | None = None
    experimenter: str | None = None
    experiment_description: str | None = None
    epoch_tags: list[str] = dataclasses.field(default_factory=list)
    source_script: str | None = None
    identifier: str | None = None
    notes: str | None = None


@dataclasses.dataclass
class Epoch(RecordWithNWB):
    """
    >>> from npc_lims import NWBSqliteDBHub as DB

    >>> epoch = Epoch('626791_2022-08-15', '11:23:36', '12:23:54', ['DynamicRouting1'])
    >>> DB().add_records(epoch)

    >>> all_epochs = DB().get_records(Epoch)
    >>> assert epoch in all_epochs, f"{epoch=} not in {all_epochs=}"
    >>> session_epochs = DB().get_records(Epoch, session_id='626791_2022-08-15')
    >>> session_epochs[0].tags
    ['DynamicRouting1']
    """

    nwb_excl: ClassVar[tuple[str, ...]] = ("session_id",)

    table: ClassVar = "epochs"

    session_id: str | npc_session.SessionRecord
    start_time: float
    stop_time: float
    tags: list[str]
    notes: str | None = None

    @property
    def nwb(self) -> dict[str, NWBType]:
        nwb = super().nwb
        nwb["notes"] = "" if nwb["notes"] is None else nwb["notes"]
        nwb["start_time"] = float(str(nwb["start_time"]))
        nwb["stop_time"] = float(str(nwb["stop_time"]))
        return nwb


@dataclasses.dataclass
class File(Record):
    table: ClassVar = "files"

    session_id: str | npc_session.SessionRecord
    name: str
    suffix: str
    size: int
    timestamp: str | npc_session.DatetimeRecord
    s3_path: str | None = None
    allen_path: str | None = None
    data_asset_id: str | None = None
    notes: str | None = None


@dataclasses.dataclass
class Folder(Record):
    table: ClassVar = "folders"

    session_id: str | npc_session.SessionRecord
    name: str
    timestamp: str | npc_session.DatetimeRecord
    s3_path: str | None = None
    allen_path: str | None = None
    data_asset_id: str | None = None
    notes: str | None = None


@dataclasses.dataclass
class DataAsset(Record):
    table: ClassVar = "data_assets"
    data_asset_id: str
    session_id: str
    name: str
    notes: str | None
    """e.g. raw ephys data"""


@dataclasses.dataclass
class CCFRegion(Record):
    table: ClassVar = "ccf_regions"
    ccf_region_id: str


@dataclasses.dataclass
class Device(RecordWithNWB):
    """A probe serial number, used across sessions"""

    table: ClassVar = "devices"

    device_id: int
    """Serial number of the device"""
    description: str | None = "Neuropixels 1.0"
    manufacturer: str | None = "IMEC"


@dataclasses.dataclass
class ElectrodeGroup(RecordWithNWB):
    """All the channels used on one probe, in one session"""

    nwb_excl: ClassVar[tuple[str, ...]] = ("session_id",)

    table: ClassVar = "electrode_groups"

    session_id: str | npc_session.SessionRecord
    device: int
    """Serial number of the device"""
    name: Literal["probeA", "probeB", "probeC", "probeD", "probeE", "probeF"]
    description: str | None = None
    location: str | None = None
    """Implant name + location, e.g. 2002 B2"""


@dataclasses.dataclass
class Electrode(RecordWithNWB):
    """A single channel on a probe"""

    nwb_excl: ClassVar[tuple[str, ...]] = ("session_id",)

    table: ClassVar = "electrodes"

    session_id: str | npc_session.SessionRecord
    group: Literal["probeA", "probeB", "probeC", "probeD", "probeE", "probeF"]
    location: str | None = None
    """CCF location acronym/abbreviation"""
    channel_index: int | None = None
    id: int | None = None
    """Channel number on the probe"""
    x: float | None = None
    y: float | None = None
    z: float | None = None
    imp: float | None = None
    filtering: str | None = None
    reference: str | None = None


@dataclasses.dataclass
class Units(RecordWithNWB):
    nwb_excl: ClassVar[tuple[str, ...]] = ("session_id",)

    table: ClassVar = "units"

    unit_id: str
    sorted_group_id: int
    session_id: str | npc_session.SessionRecord
    sorter_id: int
    peak_channel_index: int
    location: str
    electrode_group: str
    spike_times: list[float] | None = None
    waveform_mean: list[float] | None = None
    waveform_sd: list[float] | None = None
    peak_to_valley: float | None = None
    d_prime: float | None = None
    l_ratio: float | None = None
    peak_trough_ratio: float | None = None
    half_width: float | None = None
    sliding_rp_violation: float | None = None
    num_spikes: int | None = None
    repolarization_slope: float | None = None
    device_name: str | None = None
    isi_violations_ratio: float | None = None
    rp_violations: float | None = None
    ks_unit_id: int | None = None
    rp_contamination: float | None = None
    drift_mad: float | None = None
    drift_ptp: float | None = None
    amplitude_cutoff: float | None = None
    isolation_distance: float | None = None
    amplitude: float | None = None
    default_qc: str | None = None
    snr: float | None = None
    drift_std: float | None = None
    firing_rate: float | None = None
    presence_ratio: float | None = None
    recovery_slope: float | None = None
    cluster_id: int | None = None
    nn_hit_rate: float | None = None
    nn_miss_rate: float | None = None
    silhouette_score: float | None = None
    max_drift: float | None = None
    cumulative_drift: float | None = None
    peak_channel: int | None = None
    duration: float | None = None
    halfwidth: float | None = None
    PT_ratio: float | None = None
    spread: int | None = None
    velocity_above: float | None = None
    velocity_below: float | None = None
    quality: str | None = None


if __name__ == "__main__":
    import doctest

    doctest.testmod(
        optionflags=(doctest.IGNORE_EXCEPTION_DETAIL | doctest.NORMALIZE_WHITESPACE)
    )

# IBL workflow: issues and outstanding work

Snapshot 2026-10-23. Companion to [ibl_tracking.md](ibl_tracking.md) and [ibl.md](ibl.md).

Manifests are staged at `s3://aind-scratch-data/dynamic-routing/ibl_conv/probe_annotations/<subject_id>/<etag16>/`.

## 1. Subjects with no manifest yet: sessions not uploaded/sorted

All the sessions listed below are missing **both** raw and sorted assets. The annotated tracks for those days can't be used until the data are uploaded and sorted. Session times shown as `??-??-??` come from `tables/status.csv`, which has no raw upload for that day.

| Subject | Missing session(s) | Annotated tracks waiting on them | Notes |
|---|---|---|---|
| 796848 | 2025-07-15 | A, C, D, E, F `_0715` | 07-14 has a surface recording |
| 810754 | 2025-10-29, 2025-10-31 | A, B, D, E, F `_1029`; A, B, C, E, F `_1031` | |
| 836629 | 2026-04-28, 2026-04-30 | A, B, D, E, F `_0428`; A, B, D, E, F `_0430` | `A_0501` layer is empty |
| 839146 | 2026-05-18 | A, B, D, E, F `_0518` | |
| 840160 | 2026-04-28 | A, B, D, E, F `_0428` | status.csv has a **surface** asset for 04-28 (`bef64a0e-e2dc-4e0b-9172-c9d4d607646c`) but no main raw asset. Check whether the main recording was uploaded or mislabeled |
| 856845 | 2026-05-28, 2026-06-01 | A–F `_0528`; A, B, D, E, F `_0601` | |
| 856847 | 2026-06-02, 2026-06-04 | A, B, D, E, F `_0602`; A, B, D, E, F `_0604` | |
| 862025 | 2026-08-05 | A–F `_0805` | |
| 862027 | 2026-09-17, 2026-09-18 | A–F `_0917`; A–F `_0918` | status.csv lists only 2 sessions (09-15, 09-16). It is probably out of date, since the annotations cover 4 days. Uses the newer stitched-asset naming (see §4) |

## 2. Probes missing from sorted output (omitted from staged manifests)

The sorted asset has no `curated/` output for these probes. Any of the following could explain it:
- a partial sorting failure (e.g. a CUDA error on one probe)
- the probe was not recorded
- all units failed curation

Re-sorting the session, then rebuilding the manifest, would add these probes back.

| Subject | Session | Probe(s) omitted | Sorted asset used |
|---|---|---|---|
| 810752 | 2025-10-10 | C | `ecephys_810752_2025-10-10_11-17-00_sorted_2026-06-03_06-21-33` (errored) |
| 813586 | 2025-12-02 | E | `ecephys_813586_2025-12-02_11-48-47_sorted_2026-09-17_15-50-37` |
| 813586 | 2025-12-03 | B | `ecephys_813586_2025-12-03_12-15-45_sorted_2026-09-24_05-22-02` (errored) |
| 814669 | 2025-11-10 | A, E | `ecephys_814669_2025-11-10_13-59-35_sorted_2026-01-14_06-53-29` |
| 814669 | 2025-11-11 | E | `ecephys_814669_2025-11-11_13-28-22_sorted_2025-12-11_12-44-05` |
| 814669 | 2025-11-12 | E | `ecephys_814669_2025-11-12_13-34-19_sorted_2025-12-11_14-59-06` |
| 822061 | 2026-01-14 | A | `ecephys_822061_2026-01-14_12-08-30_sorted_2026-05-27_09-33-10` (errored) |
| 836726 | 2026-02-11 | C | `ecephys_836726_2026-02-11_12-18-03_sorted_2026-02-25_07-51-48` |
| 854390 | 2026-04-27 | C | `ecephys_854390_2026-04-27_10-32-52_sorted_2026-09-03_09-23-24` (errored) |
| 859582 | 2026-06-29 | D | `ecephys_859582_2026-06-29_09-50-42_sorted_2026-09-18_21-24-11` |
| 859582 | 2026-06-30 | C | `ecephys_859582_2026-06-30_09-57-58_sorted_2026-09-18_09-25-48` (errored) |
| 859584 | 2026-07-06 | B, D, E | `ecephys_859584_2026-07-06_09-55-34_sorted_2026-09-17_14-04-33` |
| 859584 | 2026-07-07 | B, D, E | `ecephys_859584_2026-07-07_09-34-53_sorted_2026-09-17_10-36-17` |

"(errored)" means aind-session flags the asset as having an error. It is still the only or latest KS2.5 asset, so `npc_lims.get_session_sorted_data_asset` falls back to it.

## 3. Annotation layers with unrecognized names (omitted from staged manifests)

Each of these needs a decision from whoever did the annotation: rename the layer to `<probe>_<MMDD>`, delete it, or confirm that it should be left out.

| Subject | Layer | Context |
|---|---|---|
| 796012 | `B_07111` | `B_0711` also exists (9 points each, different tracks): possibly a second insertion or a redo? |
| 796847 | `unknown DiI A track` | 6 points, near the `A_0729` track |
| 822061 | `D_disappears` | |
| 837230 | `F_04212` | `F_0421 ` (with a trailing space) also exists |
| 852255 | `F_06171` | `F_0617` exists but is **empty**, so `F_06171` is probably the real `F_0617` track |
| 854390 | `F_04231` | |

There are also minor layer-name issues that didn't block building the manifests. Some layer names have a trailing space, e.g. `F_0420 ` and `F_0421 ` (837230) and `F_0618 ` (852255). These are passed through unchanged as `probe_id`.

## 4. Other risks

- **Newer stitched-asset naming:** image sources are named `<subject>_<date>_stitched_...`, with no `SmartSPIM_` prefix. This affects 857681, 872697, and 862027 (not built yet). aind-session can't parse this naming, so `build_manifest` works around it. It hasn't been verified that the conversion capsule handles it.
- **Manifests aren't at the path in `ibl.md`:** they're staged only under `probe_annotations/`, not at the `ibl_conv/manifests/<subject_id>_manifest.csv` path that `ibl.md` describes. This matches what was done for 795555, 798632, and 807082.
- **Downstream steps not started:** B4–B7 (CO asset, trigger run, processed asset, flag) haven't been run for any subject.

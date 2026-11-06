# IBL app workflow

## A) Local, untracked
1. RAs annotate in neuroglancer/neurglancer and save JSON to `\\allen\programs\mindscope\workgroups\dynamicrouting\Mikayla\annotated_neuroglancer_jsons/<subject_id>_annotated.json`
2. allen folder synced to `s3://aind-scratch-data/dynamic-routing/annotated_neuroglancer_jsons/` every day

## B) Cloud, processing workflow (one per subject)
1. Find annotation JSONs available in S3 
2. Check whether corresponding manifest .csv present in `s3://aind-scratch-data/dynamic-routing/ibl_conv/manifests/<subject_id>_manifest.csv`. 
If manifest not available:
    - discover ephys sessions for the subject (from `npc_lims/tables/status.csv`)
    - get uploaded and sorted status for each session, including optional surface channels
    - quit if not all sessions are uploaded and sorted, but ideally a "force" option allows to proceed even if some sessions are not uploaded/sorted
3. Create .csv manifest using aind_session's ibl/neuroglancer plugins (or a custom version thereof). Manifest csv spec is here: https://github.com/AllenNeuralDynamics/aind-ibl-ephys-alignment-preprocessing/blob/main/src/aind_ibl_ephys_alignment_preprocessing/types.py
4. **Always run `scripts/normalize_ng_json.py <subject_id>` first** - it overwrites the annotation JSON in S3, converting list-form coordinate spaces (`[{"name": "z", "scale": [...]}, ...]`) in `dimensions`/`outputDimensions`/`localDimensions` to dict form (`{"z": [...], ...}`), which is the only form aind-ibl-ephys-alignment-preprocessing can read (otherwise every probe is skipped: "outputDimensions this reader cannot interpret"). No-op if already normalized. The bucket is versioned, so the original is kept. Overwriting changes the ETag, and the daily allen->S3 sync may restore the list form if the RA re-saves the file, so re-run it before every manifest asset.
   Create a "probe annotations" asset in code ocean  containing the annotated neuroglancer json and the manifest csv file (CO assets support links from S3)
   - Standard format: see asset `36717d06-d03b-4372-9d6d-a7b229a65113` (`ibl_manifest_834408_2026-09-25`), a local (internal) dataset with exactly 2 files:
     - `<subject_id>_data_converter_manifest.csv` - columns `index,mouseid,sorted_recording,probe_file,probe_name,probe_shank,probe_id,surface_finding,annotation_format`; `index` is 0..n-1, rows sorted by `sorted_recording` then `probe_name`; `probe_file` is the stem of the JSON file below (no extension)
     - `SmartSPIM_<subject_id>_<acquisition date>_<time>_neuroglancer-state_<YYYY-MM-DD_HH-MM-SS>.json` - the annotated neuroglancer state (the SmartSPIM acquisition comes from the stitched image layer sources; the timestamp is that of the annotation JSON's last-modified time (UTC))
   - Name `ibl_manifest_<subject_id>_<YYYY-MM-DD>` (date = creation date), mount = name, tags `ibl`, `<subject_id>`, `manifest`, empty description, custom metadata `data level`=`derived data`, `experiment type`=`ecephys`, `institution`=`AIND`, `modality`=`extracellular electrophysiology`, `subject id`=`<subject_id>`, `subject species`=`Mus musculus`
   - Created from the S3 prefix `s3://aind-scratch-data/dynamic-routing/ibl_conv/probe_annotations/<subject_id>/<etag>/asset/` holding the two renamed files (`keep_on_external_storage=False`, so CO copies them in)
   - Newer stitched assets are named `<subject>_<date>_stitched_...` (no `SmartSPIM_` prefix); the JSON is still named with a `SmartSPIM_` prefix so aind-session can parse it
5. Run trigger capsule https://codeocean.allenneuraldynamics.org/capsule/2273914 id:`d89073c0-e1ff-44e8-8ca1-4130b4964fba` supplying newly created "probe annotations" asset ID as first input, and the worker capsule id:`cba3374d-cd09-4297-a17d-152c371e117d` (bh-pinned version withaind-ibl-ephys-alignment-preprocessing==0.8.0 before metadata change that affects sessions with 'ecephys_session' in data_description.json). max runs in flight 4 if launching a single session, 1 if launching many. don't clean up on failure and do reuse intermediates. stagger launches if running many to avoid hitting rate limit on CO API.
6. verify processed smartspim asset is created by conversion capsule https://codeocean.allenneuraldynamics.org/capsule/3646731
7. Flag the processed asset as ready for attaching to IBL app with stitched smartspim asset

## Orchestration details
- The B2 readiness producer runs with each annotation observation and records an
  `ibl_readiness/<subject_id>` asset observation. Its `report` metadata contains
  one entry per production ephys session, including the missing fields that
  prevent manifest generation. It reads the current
  `tables/status.csv` from the repository's raw GitHub URL. `ready: true` means
  B3 may build the manifest.
- B5 may take up to 30 minutes to complete. We need a mechanism to track launched/finished that persists across restarts of the orchestration system.
- No more than 3 instances of the B5 capsule should be running concurrently.
- need to be able to retrigger B4 in case we make updates to the annotations or manifest.
- ability to see the contents of json and csv that were used for for historical runs would be nice. Neuroglancer JSON can be long though. Could store URI + ETAG if size is a problem.

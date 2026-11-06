# IBL tracking

Status of each subject through the [IBL workflow](ibl.md). One row per subject with an annotated neuroglancer JSON in
`s3://aind-scratch-data/dynamic-routing/annotated_neuroglancer_jsons/`.

- **ETag**: first 16 hex chars of the S3 ETag of the annotation JSON (same as the folder name used under `ibl_conv/probe_annotations/<subject_id>/`). If the JSON changes, the ETag changes and the downstream steps need to be redone.
- **Staged**: the JSON and manifest have been copied to `s3://aind-scratch-data/dynamic-routing/ibl_conv/probe_annotations/<subject_id>/<etag>/`.
- **CO asset (B4)**: ID of the "probe annotations" data asset `ibl_manifest_<subject_id>_<date>` created 2026-10-23 from the staged files (`<etag>/asset/` subfolder; format in [ibl.md](ibl.md)). If the ETag changes, a new asset is needed.
- Record failures and manual manifest edits in **Notes** (with the date).

Last synced from S3: 2026-10-23 00:51 UTC

| Subject | JSON modified (UTC) | ETag | Manifest | Staged | CO asset (B4) | Trigger run (B5) | Processed asset (B6) | Flagged (B7) | Notes |
|---|---|---|---|---|---|---|---|---|---|
| 795555 | 2026-09-29 00:57 | `9d76d9c81f666743` | yes | yes | `716103e5-9982-4d35-a24f-c37321106f6b` | `0deefc36-eb55-4505-bff1-58d726e6f8f0` |  |  |  |
| 796012 | 2026-09-29 00:57 | `8c797d1169734809` | yes | yes | `6dfe8123-ee08-4f49-a002-19c61fd17e14` | `d6c81a4d-13bb-4d9e-b819-35b63d1791e5` |  |  | 2026-10-23: layers with unrecognized names omitted: `B_07111` |
| 796847 | 2026-09-29 00:57 | `ee2e4814d0b72168` | yes | yes | `9682a1a9-1949-4103-a4b8-aee046ca20e7` | `72255cac-f522-442c-a601-682f083b4282` |  |  | 2026-10-23: layers with unrecognized names omitted: `unknown DiI A track` |
| 796848 | 2026-09-29 00:57 | `a28137e596b30f94` |  |  |  |  |  |  |  |
| 798632 | 2026-09-29 00:57 | `c099d65d0fcbe4e9` | yes | yes | `8f1db101-f9cb-437c-a3c4-316b34008801` | `83b0aac8-3d4b-429f-9d82-724db9d8a1c9` |  |  |  |
| 805752 | 2026-11-05 19:22 | `6ed9ff95c853509b` | yes | yes | `d3cd890b-4773-4e43-a947-c7779da6179b`, `31f307b0-eade-4ff7-8c89-eeba2dbb9066` (2026-11-05, normalized dims) | `3c5a70dc-2c40-46b3-af60-d159271d251f`, `534fca40-f75c-4d7c-add6-653febc1c1d3` (retrigger), `8f9a11fa-a553-41a4-9f06-b80762ddae26` (retrigger), `da66f8ef-6102-4e9a-a1e1-2dfb74478a57` (retrigger, worker cba3374d), `1fcd0c3d-1636-4f52-9978-66ccbce711db` (retrigger, worker cba3374d), `5c728036-e841-470a-8c05-152d85e5fcb0` (2026-11-05 normalized dims, reuse=0, max-in-flight=3), `43c3a20a-bec0-4091-935a-936a0b41e1c9` (2026-11-05 retrigger, reuse=1, max-in-flight=5) | `91099f62-6416-4db1-a455-feb8d56bdbf3` (`SmartSPIM_805752_2025-11-25_09-50-32_preprocessed_2026-11-05_23-00-13`) |  | 2026-11-05: list-form dimensions normalized (preprocessing skipped all probes); restaged from `6ee3f31202aef2a7` in `6ed9ff95c853509b/`. 2026-11-05: run `5c728036` aborted before pack (status-check 404 on 10-20 ProbeC worker); `43c3a20a` reran ProbeC and packed. |
| 807082 | 2026-09-29 00:57 | `aa6eb2faaf40922d` | yes | yes | `02a80624-9a39-446a-aa0a-41b60758bd7b` | `0d3263d8-3e04-4a7b-94bd-c59f937fd36f` |  |  |  |
| 810752 | 2026-09-29 00:57 | `ddb9a58bddd814c3` | yes | yes | `996b872c-228d-4808-99f5-ae5b9fcd0b90` | `12b90d18-e899-44f0-8b16-dea2139056be` |  |  | 2026-10-23: layers omitted (probe not in sorted output): `C_1010` |
| 810754 | 2026-09-29 00:57 | `7df6be746d8bfcd9` | yes | yes | `bdfd8a62-9a69-4fa8-bde5-c0d8afdc9616` | `095a6f3a-cd0e-4dd1-ba04-95478bd0385e` (worker cba3374d, reuse=1, max-in-flight=4) | `12852f7a-ecf5-463b-a7cb-b053ee2460d0` (`SmartSPIM_810754_2025-11-25_12-43-44_preprocessed_2026-11-05_23-56-10`) |  | 2026-11-05: built with --force (10-29, 10-31 not uploaded/sorted); layers omitted: `A_1029`, `B_1029`, `D_1029`, `E_1029`, `F_1029`, `A_1031`, `B_1031`, `C_1031`, `E_1031`, `F_1031`. Surface recordings found for all 3 sessions. |
| 813586 | 2026-09-29 00:57 | `503fc8bb36a6cb99` | yes | yes | `fd2cfdce-e1d2-425f-9dc6-0df55d58b982`, `432ee62c-31fa-4a10-ad9d-172a2a6ec3ac` (2026-10-24, with surface channels) | `19f95ae5-13b1-4c0e-8e1c-af55cce916bb`, `81bff8ce-2cf9-4c86-a74b-8d7ca3dca798` (surface retrigger, reuse=1, failed), `f4e8b05a-da6b-4288-859f-13c456951c6d` (surface retrigger, reuse=0, max-in-flight=5, failed), `a63e2c03-c2ef-437c-9c78-4b03e0a05c76` (surface retrigger, reuse=0, max-in-flight=5, failed: ambiguous raw), `c752989d-72ae-4c76-9cc8-f365c48cf1b8` (worker cba3374d, failed), `ae11b710-bf75-4ca4-8ff1-5e0b256fe702` (worker cba3374d, failed: iblatlas 1.3.1 lut v02), `c9965631-ce26-45f8-9717-13b539841562` (surface retrigger, worker cba3374d, reuse=0, max-in-flight=5) |  |  | 2026-10-23: layers omitted (probe not in sorted output): `B_1203`, `E_1202`; 2026-10-24: surface assets uploaded, manifest rebuilt in `503fc8bb36a6cb99_surface/` |
| 814666 | 2026-09-29 00:57 | `d7050f7f48442cfc` | yes | yes | `ae7a2469-d13a-4fe2-be2d-b2a51a429563` | `9b0859dc-2902-4cb3-9ff0-8865917b3b3b` |  |  |  |
| 814669 | 2026-09-29 00:57 | `d7ded75dbafbc51f` | yes | yes | `83920790-0d0e-4771-ac71-c43f6a3c71dc` | `ca0ecb74-8d11-4c4d-bed9-12afd3cd673b` |  |  | 2026-10-23: layers omitted (probe not in sorted output): `A_1110`, `E_1110`, `E_1111`, `E_1112` |
| 822061 | 2026-09-29 00:57 | `e3cf8fa12557efec` | yes | yes | `015e2fc7-4b7b-4c8c-a8dd-41edd083b99c` , `6c945565-a5dc-450c-95a2-5f38e0dc72be` (2026-10-24, restitched), `edb7e9b8-88cb-4ef9-bedb-b70304ba51eb` (2026-11-05, rebuilt with latest 1/14 sort) | `c86e20e6-4653-406f-bab4-2147099a5297`, `3bc8b7ae-931c-47d3-8e5c-4ea0f0310d7c` (retrigger) , `d40d2d37-1d3a-4776-a673-1c582d070ce0` (restitched), `2bebdc02-ccd6-427a-91f7-ee5cd838bf8b` (retrigger), `f81f7627-cd8c-47a4-8026-32e10236e77b` (retrigger, worker cba3374d), `026f4276-8388-4845-aa79-1503b5874560` (retrigger, worker cba3374d), `51be099e-bacc-4253-a5fc-afe9fdc92446` (2026-11-05 retrigger, worker cba3374d, reuse=0, max-in-flight=5) | `6f64da64-0b97-427b-833d-35c55879203c` (`SmartSPIM_822061_2026-02-17_14-46-20_preprocessed_2026-11-05_18-20-19`) |  | 2026-10-23: layers with unrecognized names omitted: `D_disappears`; layers omitted (probe not in sorted output): `A_0114` 2026-10-24: annotation referenced missing stitched asset; manifest asset rebuilt with stitched_2026-04-24_03-38-35. 2026-11-05: manifest rebuilt with latest 2026-01-14 sorted asset (b350bda5) in `e3cf8fa12557efec_restitched_resort/` |
| 831994 | 2026-09-29 00:57 | `064d40b116f72b23` | yes | yes | `254e1f58-4305-478d-a23f-819c9b12d330` , `13bd1060-9d93-4cf4-a2e8-61f25983014e` (2026-10-24, restitched)| `5605f0a2-5912-4b75-a1da-a51973f208bd`, `2fb4c9e4-16c1-4a57-8d54-56ef09e00077` (retrigger) , `649fbac2-c2ae-4cfd-ac53-5d120760668d` (restitched) |  |  | 2026-10-24: annotation referenced missing stitched asset; manifest asset rebuilt with stitched_2026-04-24_23-43-37. |
| 834408 | 2026-11-05 20:08 | `8a1cfb7a61924e5b` | yes | yes | `1894ffa3-7aff-47e9-9f80-3a6a72bd13f6` , `1e04c441-7824-49ea-be5c-e7bf1e02e6e1` (2026-10-24, restitched), `a30dfbdc-9884-42d3-9c72-71a139f6cdf4` (2026-11-05, normalized dims) | `8ab37397-0ee1-4698-893d-36e003833f4a`, `cf7d70a3-c6f1-499a-9a48-3a61bb72ef13` (retrigger) , `a0fbba2a-e992-42ff-85ae-8e9cf79fd636` (restitched), `e35c16ad-c010-4dbd-a1f0-d3ff1e259f17` (2026-11-05 normalized dims, reuse=0, max-in-flight=3) | `77e23648-5b82-4266-b1f9-b14c566e025c` (`SmartSPIM_834408_2026-02-16_13-42-28_preprocessed_2026-11-05_21-42-11`) |  | 2026-10-24: annotation referenced missing stitched asset; manifest asset rebuilt with stitched_2026-04-24_02-13-01. 2026-11-05: list-form dimensions normalized (preprocessing skipped all probes); restaged from `ee1d8d5c6168de10_restitched` in `8a1cfb7a61924e5b/`. |
| 835598 | 2026-09-29 00:57 | `9f52e46529ab478b` | yes | yes | `124a88b4-f5c1-452f-818e-85e19ef406b4` | `69f5723a-13df-4fa6-825b-b2d651fa1d14` |  |  |  |
| 836629 | 2026-09-29 00:57 | `2cb79df4a1a9d8da` |  |  |  |  |  |  |  |
| 836726 | 2026-09-29 00:57 | `dfb75a859264a457` | yes | yes | `a95f14df-4fc1-4f22-8cfd-8bfc38e39642` | `4879a698-9333-416a-8a48-9416a3cc0b4b` |  |  | 2026-10-23: layers omitted (probe not in sorted output): `C_0211` |
| 836729 | 2026-09-29 00:57 | `b8ac58bef1a4e526` | yes | yes | `98655dcd-5529-4cac-bed4-017ab5911247` | `91a0e02a-7332-4fa8-882d-d45a3a48bd07` |  |  |  |
| 837230 | 2026-11-05 20:09 | `ed43df6bee216e87` | yes | yes | `fe9dda82-e67b-4722-87c0-68d9374827c1`, `5fb4ac6e-9213-4f05-8752-cdc2d4a53840` (2026-11-05, normalized dims) | `d1c7ca12-ebd4-47af-a468-33448e294eb1`, `8bb486c2-3c70-42cc-b7bd-bd996944c856` (retrigger), `5ddf1010-62c5-40c0-b928-dda0fe5025da` (2026-11-05 normalized dims, reuse=0, max-in-flight=3) | `c1257d42-a7aa-4a6f-892e-3780d72cb5d6` (`SmartSPIM_837230_2026-05-11_18-41-54_preprocessed_2026-11-05_21-36-26`) |  | 2026-10-23: layers with unrecognized names omitted: `F_04212` 2026-11-05: list-form dimensions normalized (preprocessing skipped all probes); restaged from `a766da0f8918a925` in `ed43df6bee216e87/`. |
| 837959 | 2026-09-29 00:57 | `5bde99f8fae866c9` | yes | yes | `8d52f8d0-d298-4bde-94ef-1d20d3322868` | `93e585d8-c182-4757-a1fd-450e2e304145`, `e2623622-3aa9-4cd6-947e-0a2379fee843` (retrigger), `2362ee18-22d8-4bff-a73c-120f679433b1` (retrigger), `d35175bd-ce12-4b0e-ab21-ea79c4038102` (retrigger, worker cba3374d) |  |  |  |
| 839146 | 2026-09-29 00:57 | `46a85bf0347101b9` |  |  |  |  |  |  |  |
| 840160 | 2026-09-29 00:57 | `894b80f81bf92f1f` |  |  |  |  |  |  |  |
| 841308 | 2026-09-29 00:57 | `f9507aa99017fcb8` | yes | yes | `00e3ed3f-dee5-476c-bc58-bd46af077007` , `71ad2ab3-ddd8-41ee-b507-62c2e74d004d` (2026-10-24, restitched), `07b9d0af-8eb2-461d-bb8d-ff491de576bb` (2026-11-05, surface channels updated) | `5d8e61e0-f1b0-4c9b-a6b8-696bc8a783c1`, `474bfd16-c418-427d-b671-3b1a2122b37a` (retrigger) , `b2ad5ceb-9cb6-4feb-8110-7d5d93c62129` (restitched), `cf12813c-1538-4abd-a67a-be519bb99650` (retrigger, max-in-flight=1), `d8641a4a-c0eb-4f38-a921-9f0823dbac35` (2026-11-05 surface retrigger, worker 09e00815, reuse=1, max-in-flight=1), `94ac31b6-7408-473e-b46a-26c960e093dd` (retrigger, worker cba3374d) |  |  | 2026-10-24: annotation referenced missing stitched asset; manifest asset rebuilt with stitched_2026-06-10_07-38-10. 2026-11-05: manifest rebuilt with new surface assets in `f9507aa99017fcb8_restitched_surface2/` |
| 847958 | 2026-09-29 00:57 | `55bd28be6bfaea16` | yes | yes | `9b890605-4d5e-4446-adc2-574493c6753a` | `d95e250b-082f-4243-8a63-250cdaaf4175`, `e16580fd-6dbf-4555-b919-d6d370892b7a` (retrigger), `31540a58-6c56-45bd-aa20-cf4328f0047d` (retrigger), `4c7b6f8f-5f90-47f5-a588-881c8305d3fc` (retrigger, worker cba3374d) |  |  |  |
| 850215 | 2026-09-29 00:57 | `976a2062f5ee3858` | yes | yes | `262654b6-8c7a-431e-bc69-e51901ed5429` | `3d42b95a-9d55-47a6-b655-d7ef8156af5d`, `c0450897-784e-4010-b66f-e9a5198057d9` (retrigger) |  |  |  |
| 850217 | 2026-09-29 00:57 | `dc738c83f8cdd7a5` | yes | yes | `493e7462-ea40-4b82-95cd-064b8e9126e5` | `788123e8-aaee-426b-b437-c3530152b27a`, `bfd8ffd4-2fc3-48f3-abee-4552b92124ba` (retrigger) |  |  |  |
| 852252 | 2026-11-05 20:09 | `13fc0eb1b857f1bf` | yes | yes | `92edbdcf-a795-42d6-9f44-ebe766e57b65`, `519904ec-bd5c-4a8b-af2a-ce7705b70e5d` (2026-11-05, normalized dims) | `5ff122ef-cdda-4a66-850b-551394458f05`, `baf1dc42-0ba9-4bf9-a2cb-8767b0bd0d37` (retrigger), `8436243d-5419-4a9f-ae93-4dcc00847743` (2026-11-05 normalized dims, reuse=0, max-in-flight=3) | `0abef20c-8a62-48fa-a3af-5d26b50c48b7` (`SmartSPIM_852252_2026-07-29_23-38-46_preprocessed_2026-11-05_21-30-49`) |  | 2026-11-05: list-form dimensions normalized (preprocessing skipped all probes); restaged from `3b98eec084b64479` in `13fc0eb1b857f1bf/`. |
| 852255 | 2026-11-05 20:09 | `090ef142a5a66f6e` | yes | yes | `1578b14f-0bec-4b97-a4ce-a1776be39365`, `ed87c0d3-18a4-428a-b544-5e4759a4513d` (2026-11-05, normalized dims) | `4ef5a5f4-1e15-4cec-82cb-2056da4bcbb5`, `d15c0f41-fe99-4943-bc23-95f6e073a317` (retrigger), `4506ed82-f36f-497e-8afa-7b469a183db5` (2026-11-05 normalized dims, reuse=0, max-in-flight=3) | `d6f93a85-5e73-46e2-936e-a573a55d05cd` (`SmartSPIM_852255_2026-07-14_19-45-16_preprocessed_2026-11-05_21-38-45`) |  | 2026-10-23: layers with unrecognized names omitted: `F_06171` 2026-11-05: list-form dimensions normalized (preprocessing skipped all probes); restaged from `61dca145ed820550` in `090ef142a5a66f6e/`. |
| 854390 | 2026-09-29 00:57 | `e3386877e0408584` | yes | yes | `777902e0-9cbd-4c26-80c7-bdadf7b54e4c` | `fd229884-1e1c-422f-a995-43f9219d075b`, `381ac0d0-5439-4fd6-8084-6395c73a467b` (retrigger) |  |  | 2026-10-23: layers with unrecognized names omitted: `F_04231`; layers omitted (probe not in sorted output): `C_0427` |
| 856845 | 2026-09-29 00:57 | `29a663ddefb17dbe` |  |  |  |  |  |  |  |
| 856847 | 2026-09-29 00:57 | `176f97cded741549` |  |  |  |  |  |  |  |
| 857681 | 2026-10-08 21:55 | `65aa3f2a08da26b7` | yes | yes | `a15a8304-1557-4601-89bf-25ac8993b810` | `f4313337-2137-4d89-9839-20ae99aedbaa`, `ad1afad7-7b25-4870-8cb8-cf1e0618daf0` (retrigger) |  |  |  |
| 859582 | 2026-09-29 00:57 | `16d4e156ef6f16ac` | yes | yes | `9ff9a5fd-27aa-4ab4-8e80-8c93ac0d7b23` | `cdc17c98-6ef6-4b2a-a0fa-2ad574f96310` |  |  | 2026-10-23: layers omitted (probe not in sorted output): `D_0629`, `C_0630` |
| 859583 | 2026-11-05 20:10 | `60536f806a6f2d38` | yes | yes | `c5f70af7-9448-4059-8989-c7440957d404`, `330ff1f6-f5dd-427d-aeed-f03987e38e92` (2026-11-05, normalized dims) | `e777d7be-28b8-4e8e-aecf-288f97820ec8`, `b407f55d-955e-4443-95ec-d15c29a425ba` (retrigger), `9b9ffc86-42c7-407e-9b4a-a02aabaf4887` (2026-11-05 normalized dims, reuse=0, max-in-flight=3) | `8d1ccd2c-82fb-459a-8e5e-bc20dc9a62db` (`SmartSPIM_859583_2026-06-15_20-50-53_preprocessed_2026-11-05_21-59-37`) |  | 2026-11-05: list-form dimensions normalized (preprocessing skipped all probes); restaged from `e87b29ebc4715063` in `60536f806a6f2d38/`. |
| 859584 | 2026-09-29 00:57 | `b60c80caf2a7784f` | yes | yes | `1305938a-a370-475b-84ad-ca17253becb8` | `66446d68-83f6-48b5-88ae-5e3eb981bc5c` |  |  | 2026-10-23: layers omitted (probe not in sorted output): `E_0706`, `E_0707`, `B_0706`, `B_0707`, `D_0706`, `D_0707` |
| 862025 | 2026-09-29 00:57 | `eb214b0a83cf2a13` |  |  |  |  |  |  |  |
| 862027 | 2026-10-19 21:55 | `7805397669847429` |  |  |  |  |  |  | 2026-10-23: manifest not built - annotations include 09-17/09-18 but no raw/sorted sessions found for those dates |
| 872697 | 2026-10-09 21:55 | `2aea1543e07a035b` | yes | yes | `f1b49141-2c18-43eb-92ce-c72c72dc1f3d` | `68aa7b5c-0b73-4134-acef-7b30cb59a14b`, `9b488f23-5e96-42c9-bd05-c64374213d99` (retrigger) |  |  |  |

## Ephys sessions per subject

Raw and surface asset IDs come from `tables/status.csv` (last committed 2026-10-06); sorted asset IDs were looked up live in Code Ocean (latest non-errored KS2.5 sorted asset, as chosen by `npc_lims.get_session_sorted_data_asset`). Blank = no asset found. Sessions with `??-??-??` are placeholders with no raw upload yet.

### Summary

| Subject | Sessions | Raw | Sorted | Surface |
|---|---|---|---|---|
| 795555 | 4 | 4/4 | 4/4 | 0/4 |
| 796012 | 4 | 4/4 | 4/4 | 0/4 |
| 796847 | 4 | 4/4 | 4/4 | 0/4 |
| 796848 | 4 | 3/4 | 3/4 | 1/4 |
| 798632 | 4 | 4/4 | 4/4 | 0/4 |
| 805752 | 5 | 5/5 | 5/5 | 5/5 |
| 807082 | 4 | 4/4 | 4/4 | 0/4 |
| 810752 | 4 | 4/4 | 4/4 | 0/4 |
| 810754 | 5 | 3/5 | 3/5 | 0/5 |
| 813586 | 4 | 4/4 | 4/4 | 4/4 |
| 814666 | 4 | 4/4 | 4/4 | 0/4 |
| 814669 | 4 | 4/4 | 4/4 | 0/4 |
| 822061 | 5 | 5/5 | 5/5 | 5/5 |
| 831994 | 4 | 4/4 | 4/4 | 0/4 |
| 834408 | 4 | 4/4 | 4/4 | 4/4 |
| 835598 | 5 | 5/5 | 5/5 | 5/5 |
| 836629 | 4 | 2/4 | 2/4 | 0/4 |
| 836726 | 3 | 3/3 | 3/3 | 0/3 |
| 836729 | 3 | 3/3 | 3/3 | 2/3 |
| 837230 | 4 | 4/4 | 4/4 | 0/4 |
| 837959 | 5 | 5/5 | 5/5 | 5/5 |
| 839146 | 5 | 4/5 | 4/5 | 0/5 |
| 840160 | 5 | 4/5 | 4/5 | 5/5 |
| 841308 | 5 | 5/5 | 5/5 | 3/5 |
| 847958 | 5 | 5/5 | 5/5 | 5/5 |
| 850215 | 4 | 4/4 | 4/4 | 4/4 |
| 850217 | 3 | 3/3 | 3/3 | 2/3 |
| 852252 | 3 | 3/3 | 3/3 | 0/3 |
| 852255 | 4 | 4/4 | 4/4 | 0/4 |
| 854390 | 4 | 4/4 | 4/4 | 4/4 |
| 856845 | 4 | 2/4 | 2/4 | 0/4 |
| 856847 | 4 | 2/4 | 2/4 | 0/4 |
| 857681 | 4 | 4/4 | 4/4 | 0/4 |
| 859582 | 4 | 4/4 | 4/4 | 0/4 |
| 859583 | 4 | 4/4 | 4/4 | 0/4 |
| 859584 | 4 | 4/4 | 4/4 | 0/4 |
| 862025 | 3 | 2/3 | 2/3 | 0/3 |
| 862027 | 2 | 2/2 | 2/2 | 0/2 |
| 872697 | 4 | 4/4 | 4/4 | 0/4 |

### Detail

| Subject | Session | Raw asset | Sorted asset | Surface asset |
|---|---|---|---|---|
| 795555 | ecephys_795555_2025-08-21_12-00-17 | `26a2ff01-43be-428c-b16a-65dbdbc90b2d` | `3a331b77-8ea9-4ff6-acbb-553a7f00f873` |  |
| 795555 | ecephys_795555_2025-08-22_11-32-04 | `08c31bfb-7173-4153-950e-0c1a0d72cd20` | `91e9f735-1ee8-467b-8d02-0d8e9c5c0d31` |  |
| 795555 | ecephys_795555_2025-08-25_12-01-16 | `e7767b57-c5cf-42f0-83a8-71db07b1d2e1` | `8a4f1a9c-546d-4dc4-bec0-4e93e6fd4efe` |  |
| 795555 | ecephys_795555_2025-08-26_11-29-20 | `6d3cbed1-69c2-4386-b6d7-a216cc2cd634` | `17a55ef6-ecd7-4e9d-b743-e506c86a447a` |  |
| 796012 | ecephys_796012_2025-07-10_10-41-58 | `988e74ae-cadd-422d-b339-653d6dbb7cc4` | `99a0aa37-ee3b-44a1-b2e4-52edeaa685d1` |  |
| 796012 | ecephys_796012_2025-07-11_13-25-33 | `50de5622-d678-4f46-9814-985c6c6ee7bc` | `c26af2ca-a8b0-4a2a-9583-4ef74442e2e8` |  |
| 796012 | ecephys_796012_2025-07-14_13-30-15 | `a10eba9d-40cf-4720-87db-c19ff5e55d9e` | `ef58895b-5070-4f87-b1d6-4ee31cc276f4` |  |
| 796012 | ecephys_796012_2025-07-15_13-54-17 | `19cb359a-a7c0-47d2-bc74-51930fd91a03` | `8e85669c-3b4a-40fd-b596-62c8575f4efe` |  |
| 796847 | ecephys_796847_2025-07-29_11-58-20 | `bfa7ac76-2c22-4c82-80ad-0bee89223be1` | `aa56485f-f940-48ea-9040-e0dd32058c33` |  |
| 796847 | ecephys_796847_2025-07-30_12-57-43 | `fc94d55d-7c54-4254-bc26-533d182254c3` | `16611d42-ce47-43e9-917d-2e6fea64fa33` |  |
| 796847 | ecephys_796847_2025-07-31_12-00-52 | `9617850c-b289-4243-995a-eeb028aa45a2` | `bc1a8b2c-601b-455b-a2bd-0bcd1ac1e5c2` |  |
| 796847 | ecephys_796847_2025-08-01_10-56-29 | `fe478e0e-f87f-410f-a6d0-7f774e6b0d35` | `721e909a-d7e6-4df1-9860-f679797e483f` |  |
| 796848 | ecephys_796848_2025-07-14_16-02-52 | `2ff74755-bc13-4bea-9bd2-a92665927167` | `2760b85d-b56a-43eb-ac7a-b05208a0232e` | `f782a0b2-3b32-48cd-9894-52497c364dcd` |
| 796848 | ecephys_796848_2025-07-15_??-??-?? |  |  |  |
| 796848 | ecephys_796848_2025-07-16_12-41-08 | `d4ab71cb-d4ee-4493-bd77-76007ccfa244` | `a56082f3-fef8-447c-8b0c-873f42e68094` |  |
| 796848 | ecephys_796848_2025-07-17_12-32-15 | `d1a142db-d9b5-4534-b354-40293401017c` | `497218e5-5fd2-4cda-b4ff-248cff1b1a57` |  |
| 798632 | ecephys_798632_2025-08-29_10-38-12 | `037b8617-b16d-4ce1-9bde-33989b03a341` | `b844a603-c1d1-48a5-b47b-216561948593` |  |
| 798632 | ecephys_798632_2025-09-02_11-20-02 | `e7801ccf-508f-43db-95b3-a5fbe157ec52` | `0ba521ae-7575-4768-b5ab-e9b4a3356648` |  |
| 798632 | ecephys_798632_2025-09-03_10-33-28 | `0d53f3be-3d39-4bfd-b3d4-9a32be20cea6` | `39059206-9797-4f40-bc26-ab97b8c5845b` |  |
| 798632 | ecephys_798632_2025-09-04_11-30-42 | `f4ca7aff-4d09-4862-82e1-17a65dac6660` | `fc121922-b5b2-401f-b5a8-1831c8f46e7a` |  |
| 805752 | ecephys_805752_2025-10-20_13-10-14 | `04dd58fe-b43c-4832-83c2-7009797db135` | `be5634b7-b8a1-4832-85e8-cfecca32a973` | `a7110144-5315-4f36-9803-78cecb62bf09` |
| 805752 | ecephys_805752_2025-10-21_12-24-14 | `f4c6f71d-9313-42c7-ad23-3b7841ff42c1` | `aefb1ceb-00c2-4172-9f52-db13c4306bdb` | `b5b6db41-f9ff-46f2-b84d-c3af028e199d` |
| 805752 | ecephys_805752_2025-10-22_12-42-18 | `b5844f3d-903c-44ba-8830-f7cf5f0ad514` | `64b0af6a-8859-4086-9c92-6b4504d8da6f` | `aa7cb4a2-373b-48ec-88cd-c0e4bbc3c6ad` |
| 805752 | ecephys_805752_2025-10-23_12-43-41 | `d9c5c678-6f10-481a-a861-afdd1f500701` | `814b5419-5d1b-45ae-8951-206e5f3469ff` | `0efdae38-08e9-4a14-9d56-dc19b99cb045` |
| 805752 | ecephys_805752_2025-10-24_13-20-54 | `80cf08a1-be47-4946-aacd-9a9958a6bc9d` | `b5f6155a-0235-4c3b-84a8-fb7f7bae33e1` | `eb151db7-ffed-4b43-8f97-9ee78be546be` |
| 807082 | ecephys_807082_2025-09-29_13-09-08 | `42d5d755-157d-407a-81b5-09c0a8f8c440` | `a9f30951-5bf3-48eb-a3f5-6cfd5f5b9079` |  |
| 807082 | ecephys_807082_2025-09-30_14-03-30 | `60729cfa-a2cd-4a83-9969-b45f7793bef9` | `3ce480cd-c17f-4e67-b594-155f25f2d9b6` |  |
| 807082 | ecephys_807082_2025-10-01_11-44-55 | `914ab759-215a-47c0-ac1d-ec9346dc5b48` | `b07154d3-3fbc-49f3-8cc0-db535be08f94` |  |
| 807082 | ecephys_807082_2025-10-02_12-44-33 | `351d44c1-0b9c-4c18-8da1-44c6111bc399` | `7104c2b5-5e57-4243-ba77-951b9ed2886e` |  |
| 810752 | ecephys_810752_2025-10-07_12-41-18 | `5ef287ce-81ec-4cb7-9e00-d44c90580f26` | `b1b19cc9-c090-4a92-a172-7133f41d848d` |  |
| 810752 | ecephys_810752_2025-10-08_12-01-47 | `f6982bd6-e60a-4334-82f1-711f085246a8` | `db3d712d-4efe-4186-a89f-dd71dc14ab74` |  |
| 810752 | ecephys_810752_2025-10-09_11-38-01 | `6100817d-8a16-4604-8b89-b7917d7895cf` | `50cc526d-0966-40a4-b48f-047ea1b243f7` |  |
| 810752 | ecephys_810752_2025-10-10_11-17-00 | `05f0d021-fcb0-4fac-a1c3-caa74dd3dd2e` | `8c786c99-1396-49d6-8ebb-178631247587` |  |
| 810754 | ecephys_810754_2025-10-27_12-21-21 | `a4a15887-59c0-413e-808c-3227b82ac34b` | `1ac437ae-3af7-46d1-9c21-b9170c54efbc` |  |
| 810754 | ecephys_810754_2025-10-28_11-26-14 | `032a1593-0bb5-4199-9864-d0f319fd1011` | `10d0ed18-361e-45b2-9fed-07ec45503df2` |  |
| 810754 | ecephys_810754_2025-10-29_??-??-?? |  |  |  |
| 810754 | ecephys_810754_2025-10-30_12-41-14 | `204e9fbd-c1a3-46de-9be7-bfbf64b06873` | `12c04f25-fa31-472a-8d40-c6e084ff3f5c` |  |
| 810754 | ecephys_810754_2025-10-31_??-??-?? |  |  |  |
| 813586 | ecephys_813586_2025-12-02_11-48-47 | `81fb22c8-9f90-402b-8274-6aadfaa5fe23` | `ebbab2f4-a044-4e82-9222-ecaa86c167ab` | `e0578d76-df0d-4854-b294-987d11ceab64` |
| 813586 | ecephys_813586_2025-12-03_12-15-45 | `5d59e6f1-a940-4077-8386-d2cf4e11b1ea` | `c0b80108-4137-4124-aafb-d7df0bae8dba` | `1fe5b633-7030-408b-8cc7-1650689c86c0` |
| 813586 | ecephys_813586_2025-12-04_12-45-16 | `17b98699-ca35-4e28-a9cc-09c87fbbe120` | `4d91d64e-0422-41ff-b4ff-98741e9e9006` | `bb06212d-eb98-4d8d-a5a9-f6748df07378` |
| 813586 | ecephys_813586_2025-12-05_12-45-41 | `11c002c6-ad8b-4321-81a7-91193ca20383` | `37b846a3-a11b-43f7-9932-bc1fd9400d7d` | `6c3bc345-00cd-4ffd-a3eb-b76bf6697498` |
| 814666 | ecephys_814666_2025-11-06_13-07-38 | `d6257f3c-2b4a-4363-88a4-877e6eb78809` | `deaeedf3-8a38-44e0-89fb-4cd20d148edc` |  |
| 814666 | ecephys_814666_2025-11-07_14-37-14 | `5272b9ca-2518-4f6a-b498-f9c76a83f8d3` | `06c42be4-b670-429f-9223-dfcb631de46f` |  |
| 814666 | ecephys_814666_2025-11-10_12-21-30 | `8815e993-6945-4234-aa39-5d264bb2cb9e` | `13907a16-24f1-4362-8967-7dbefba86d68` |  |
| 814666 | ecephys_814666_2025-11-11_13-19-33 | `8183fe42-a92a-4d52-abc9-f04fbbc64d9a` | `82e90a1a-1ca2-4a81-b651-28d48340f5cb` |  |
| 814669 | ecephys_814669_2025-11-10_13-59-35 | `8d1af64d-2111-44bc-8064-edab81009936` | `9a72546a-81bf-466c-b6f7-74d5568765c2` |  |
| 814669 | ecephys_814669_2025-11-11_13-28-22 | `ce53adab-1cab-48af-82f4-f25c2157c5c0` | `ba5201d2-4f94-4f64-acf3-0d67b548dc96` |  |
| 814669 | ecephys_814669_2025-11-12_13-34-19 | `e80b863b-fe6c-4209-b97f-fad7d6eb5882` | `aa8d8d30-1c7a-4c70-b42b-c2e7e81deceb` |  |
| 814669 | ecephys_814669_2025-11-13_13-17-03 | `50beff2a-c773-4e9f-92bd-a7d9106c2f4c` | `83ace8c7-bf9d-4e44-b7ae-4bd28ac42f88` |  |
| 822061 | ecephys_822061_2026-01-12_16-06-30 | `2426c9fd-92e2-44d0-9f88-aca1b90ed2cc` | `224d754c-68b8-459f-b0a7-f642d34117c3` | `08e16a72-58b4-4147-9450-fd89cc82fb47` |
| 822061 | ecephys_822061_2026-01-13_11-30-15 | `686eac00-f1c3-4e5b-8b83-bdc033d839c5` | `f242523e-b67f-45f1-b876-669c753c0381` | `b22908ad-02c3-4f77-a544-36976ccf4d57` |
| 822061 | ecephys_822061_2026-01-14_12-08-30 | `ad19bcee-b675-4060-a19a-b4b4e79b9261` | `a4de99df-c93a-48f5-9af3-ae1d9598ea0d` | `43647802-fc30-4164-855c-cde1ad35aa62` |
| 822061 | ecephys_822061_2026-01-15_12-56-46 | `93e5c412-755a-4252-8d28-e3e42c284d48` | `9ceef9c6-652f-4522-8dbd-126cbf565920` | `34cb4386-a973-41fb-a454-625eb3b23c35` |
| 822061 | ecephys_822061_2026-01-16_11-22-19 | `dd031c1b-b1e2-4af9-a867-cbd5ffa01a3f` | `c2e912c3-9005-4497-9750-37bd25695a65` | `00854151-c185-4431-9b90-46c5316ded85` |
| 831994 | ecephys_831994_2025-12-15_14-23-59 | `820cf536-e968-4d14-b747-f062b4376596` | `a20342ec-f34b-48b2-8bf9-bf4032627103` |  |
| 831994 | ecephys_831994_2025-12-16_11-43-18 | `3d0528d4-ddbd-46a1-8104-bffe306c6137` | `27259fe3-b2e0-4ec5-b296-dc45d7b8e9be` |  |
| 831994 | ecephys_831994_2025-12-17_11-31-28 | `40b33e22-5188-4912-a770-e22cfe72f85c` | `28f6e777-a6b3-4d3c-bb86-76c601dda956` |  |
| 831994 | ecephys_831994_2025-12-18_11-22-34 | `384e591a-055a-4d48-b35a-389df2361d0f` | `73c5f5fc-5a9c-4a65-b39e-def49c40b664` |  |
| 834408 | ecephys_834408_2025-12-17_13-03-16 | `7e0d6edc-52b6-4bd3-9faa-e9d5ac04bdbd` | `82b7ffea-b8e6-4f46-83ad-d633025a854d` | `24a4e76b-61c4-4950-8a72-b21eaaf7e8cb` |
| 834408 | ecephys_834408_2025-12-18_12-27-07 | `e69b6498-8210-46e5-8444-fc1fbc57dbc3` | `d33a977f-884f-463f-9816-a061b7698762` | `61fc933e-298d-4900-b328-89d3f314a99d` |
| 834408 | ecephys_834408_2025-12-19_12-24-44 | `923a1969-9dc3-447a-b5d7-30c449671c4d` | `070b16eb-40c5-49e5-b275-0763e81f9dd3` | `e4f362b5-79a8-46c6-86cf-2777f42065ff` |
| 834408 | ecephys_834408_2025-12-22_11-34-00 | `158fef48-dce4-4db7-af86-796bd20e1019` | `4915aaa2-421a-46fb-be42-3cf970ba22a8` | `93426703-0d75-4ce3-9f90-9eb6f71c27b4` |
| 835598 | ecephys_835598_2026-02-23_11-11-38 | `3628a83c-e8eb-4944-8034-a52bfa35d6b8` | `4cc5f78a-8682-48cf-bc93-d5c4fd1fb457` | `14bfce34-8da5-41c0-8bff-47047c8b0bab` |
| 835598 | ecephys_835598_2026-02-24_11-05-13 | `f16367b2-4ba1-4b2a-8af6-dd99c005a200` | `823fef81-2cca-4e33-b234-225c964e57c7` | `68c7943d-5d0f-46ba-b6ea-a8c09fefa46b` |
| 835598 | ecephys_835598_2026-02-25_11-11-16 | `4b362fbb-1589-4c05-9faf-a55348a09d19` | `6840c26f-57ad-4487-a61f-092d2ed45fe1` | `15e3f94e-0535-4c48-934d-490716c1b468` |
| 835598 | ecephys_835598_2026-02-26_11-17-19 | `77105671-2eff-4362-96f4-0df87c901422` | `e54123bb-434f-4d4a-b150-50579fd71da3` | `f05e8e31-0d8f-4cf7-8696-a9a7d7d2a458` |
| 835598 | ecephys_835598_2026-02-27_10-52-55 | `f8698e30-71d0-4d77-8363-8cf9ffda9cf0` | `7b6417bb-2b1c-432b-99c0-881b8dedc1f7` | `c789c8f4-55af-48ef-ad8a-3b0af69ee4d3` |
| 836629 | ecephys_836629_2026-04-28_??-??-?? |  |  |  |
| 836629 | ecephys_836629_2026-04-29_12-17-29 | `a87c481c-ab94-4c3f-9052-ad39387e1b1c` | `64fe5200-ef3b-41c1-927e-87d2299b4a6e` |  |
| 836629 | ecephys_836629_2026-04-30_??-??-?? |  |  |  |
| 836629 | ecephys_836629_2026-05-01_11-36-21 | `b363323b-2465-4a1a-8739-499865954e90` | `5e769fb3-906f-4110-a6a9-3ed26a550394` |  |
| 836726 | ecephys_836726_2026-02-11_12-18-03 | `585229f6-ddf8-414d-b375-fbb65c423020` | `41b92540-dbe5-4ab4-9260-6d4d1b2bf59d` |  |
| 836726 | ecephys_836726_2026-02-12_11-39-49 | `14c59648-82be-4111-8006-cb488c4cfdf7` | `dc9f67dd-6b10-41ea-9d3b-6ca34e873bd3` |  |
| 836726 | ecephys_836726_2026-02-13_10-19-31 | `d51549a6-ef74-4e68-8395-6729c14c2bda` | `5e2bae43-d8de-4a03-9fff-1a59c8050f96` |  |
| 836729 | ecephys_836729_2026-02-16_13-20-53 | `7a6b032f-a219-45e0-9b44-90031d76bbdd` | `af72f092-4fc2-45e1-91b4-7903ab5fe507` |  |
| 836729 | ecephys_836729_2026-02-17_12-11-16 | `e47383b7-bea6-4e51-92bc-b06de38d83f2` | `13a4f29e-8991-4989-b550-62605c9189d3` | `46790a9b-b65e-405b-af41-a35a2346dc25` |
| 836729 | ecephys_836729_2026-02-18_12-21-19 | `be20f438-b8db-4a30-9c1d-f5edab5f1738` | `fbcb0eb0-5d9c-4a02-8c38-92aa67961690` | `b0275774-eb0d-4fb7-adb0-a272d3ee6c5b` |
| 837230 | ecephys_837230_2026-04-17_13-31-48 | `d498f156-4d62-44b7-bbb4-a9898b40930c` | `736c8d43-e046-4027-b5ed-a80b3899876d` |  |
| 837230 | ecephys_837230_2026-04-20_13-56-09 | `1473f0bf-28d4-41a9-912a-122af654ffbc` | `6f8fb71b-6bc6-47df-8858-2280449dd2b0` |  |
| 837230 | ecephys_837230_2026-04-21_12-26-27 | `fe466541-94e2-4e64-8549-b576b33cc361` | `36e1344e-8afd-4645-a7df-f2862f1d1828` |  |
| 837230 | ecephys_837230_2026-04-22_12-34-16 | `6f2c8b4c-6e92-4223-8f35-eb96e00c1a44` | `4e9dcb11-fde5-4bfd-9a66-ea6f3843cb32` |  |
| 837959 | ecephys_837959_2026-03-30_11-05-52 | `16c39466-d02c-43ac-b218-5a6b32d6fdd9` | `27fa9a92-f5f0-4b75-9bc2-c04bcc1749fe` | `108fa5f7-81fd-4f72-9009-e2a061e54cd1` |
| 837959 | ecephys_837959_2026-03-31_10-20-14 | `0df200cd-d3e5-4f35-9325-61eb4d6f5ee1` | `70a5f0ac-177b-4bae-9e8f-efa6465d8bfb` | `efd83b61-e311-48b9-b224-b3a357e74db9` |
| 837959 | ecephys_837959_2026-04-01_10-24-02 | `92115fb8-3132-4293-93b4-7df346b84fe7` | `b1a0c0c5-c1bc-4fdb-9b22-9ab688f05516` | `a2e6b5cc-09db-4f85-a814-b0096383977e` |
| 837959 | ecephys_837959_2026-04-02_10-30-11 | `43371e85-82c9-4ed9-9fa4-73fceeb93ed3` | `69137729-dbdc-4d94-b9c3-0905190af5a4` | `a53589d0-fbea-4849-b2ff-f293ffa789f0` |
| 837959 | ecephys_837959_2026-04-03_10-47-23 | `e72c43b9-9cbd-456c-a0f1-e91cfa7c04f9` | `e11e512b-9bce-467c-b0a5-b882b72b66b8` | `3c7da0db-3dd7-4151-a292-24510fe5e7cc` |
| 839146 | ecephys_839146_2026-05-12_10-09-59 | `64eb8273-d394-470e-b607-5a9c9bde9614` | `3eb26dea-1a0b-4ca2-907c-9702af7b2da3` |  |
| 839146 | ecephys_839146_2026-05-13_10-27-48 | `bca21d4d-c844-4d44-b742-d4d9ca690628` | `70fe3faf-d974-44d1-9e70-a5eec66e8172` |  |
| 839146 | ecephys_839146_2026-05-14_10-26-09 | `8d7aa2b4-7a36-4217-998f-936559eb1c0c` | `c0cc30de-2f63-4734-a75b-05151759cb30` |  |
| 839146 | ecephys_839146_2026-05-15_10-04-43 | `8a04c65d-cdcc-45fb-8b54-ac63f8f23dd7` | `4b092f79-ab28-4ff1-a268-677b76d79048` |  |
| 839146 | ecephys_839146_2026-05-18_??-??-?? |  |  |  |
| 840160 | ecephys_840160_2026-04-28_??-??-?? |  |  | `bef64a0e-e2dc-4e0b-9172-c9d4d607646c` |
| 840160 | ecephys_840160_2026-04-29_10-22-59 | `45fb0463-651b-4ee3-992c-3ac54915fb1f` | `110863c9-a07d-4a71-8c33-e60304cd41a0` | `fd619f48-cf39-49c4-857c-ae180524d91a` |
| 840160 | ecephys_840160_2026-04-30_10-20-53 | `3bc148ad-8a70-4300-aa33-79bf05882235` | `5cb75380-e939-4c75-b8d2-f06c1a46a2cb` | `eb24950e-1e87-475e-967f-2031f7e48ae4` |
| 840160 | ecephys_840160_2026-05-01_10-09-37 | `c992df40-ebba-4bf1-a4ee-4a50991c782d` | `dcdac42d-e6ed-4fa7-a988-8ea53dcc9cd6` | `e0c632f0-2a3a-4769-9f15-7f838ad7cd40` |
| 840160 | ecephys_840160_2026-05-04_10-36-17 | `8c54d855-6ace-4c7f-8b21-c0aac7404feb` | `1d20d301-9792-408b-b032-3810be604985` | `d586ca99-0fcc-4661-984f-20d1568f7cce` |
| 841308 | ecephys_841308_2026-05-05_12-24-44 | `c62700fb-4d4a-4a97-9860-ba8737a4ebb0` | `a6005269-c27a-4c61-8fa9-bba9b3af2408` | `ae4250ae-7eba-41f6-baf4-7f20c23de5b1` |
| 841308 | ecephys_841308_2026-05-06_11-59-39 | `58c49d94-5d87-4acf-8b9e-f16293aac122` | `beae5259-d6b0-4001-8a64-157b11c18a41` | `b544bcf5-22d8-48a6-985b-8d5ddf6773b4` |
| 841308 | ecephys_841308_2026-05-07_11-22-58 | `d7868a56-984d-4c8f-9130-10710b8e7968` | `b23befd4-317d-4e68-8581-42aae9553b58` | `4fcbfaad-fc79-41ce-86a6-731d0a6bb990` |
| 841308 | ecephys_841308_2026-05-08_11-25-33 | `39b67cab-f619-4232-bd6c-5ff0136d4173` | `be4090d1-5bd8-4379-9777-a97ab9f9bf73` |  |
| 841308 | ecephys_841308_2026-05-11_11-42-04 | `1f398005-ec1a-40f7-a159-2461955a12c1` | `c7ca5709-7482-43fd-9f1f-89a919f89bc6` |  |
| 847958 | ecephys_847958_2026-04-13_10-25-09 | `e7f5f83b-34f8-483f-9ac6-bfc519b52363` | `da3d5da9-8955-4117-b965-2babb8e6ebb7` | `cd9fd568-eae2-4e2b-a4d1-128d19961fcc` |
| 847958 | ecephys_847958_2026-04-14_10-10-18 | `c7884409-2788-44e1-8839-3b397e5b8e4c` | `a6a46a3d-6b35-469c-8acc-ef13163f5490` | `b242eb2c-cd57-4b3a-ba80-7a298f2de670` |
| 847958 | ecephys_847958_2026-04-15_10-09-26 | `f507203b-59e2-4e76-bb36-fd8307114a80` | `06019a75-7c49-42e4-bbf5-92a4e286e3a2` | `88188966-537c-4bb4-9e37-a3911748d99b` |
| 847958 | ecephys_847958_2026-04-16_10-27-00 | `fc9c06ca-29b0-4013-ae89-8db7b437e117` | `a76ac17a-d2e3-4dde-ab29-0cc193e78164` | `bff5ff12-8848-48af-a1d6-c159635bc3bb` |
| 847958 | ecephys_847958_2026-04-17_10-19-54 | `15cde4bd-5c1c-4e71-9420-5971a729c6b5` | `39f400c6-d8b9-443b-8aad-530a2b7e0bc2` | `c5142fdc-67db-4bda-b579-46c68dccc1a7` |
| 850215 | ecephys_850215_2026-03-18_12-44-47 | `716bd594-5cca-4e81-a6ec-d0003e17a408` | `f7c173da-bdf3-4895-abc5-ef19862a9a66` | `4a9feeb3-39ce-4555-b93e-8209e41d7841` |
| 850215 | ecephys_850215_2026-03-19_13-25-49 | `a0bfa271-39d6-414d-b868-4855988bdfb6` | `209b7a72-730e-49b6-9849-a7ef4cadfd7a` | `edbcee71-566e-468e-bcb7-a3e340c6336b` |
| 850215 | ecephys_850215_2026-03-20_13-08-15 | `092e929c-27ce-4168-abd9-27dcfd86f121` | `274f68d8-7d69-4608-9c15-aac093278631` | `6c6cf004-d365-4bb4-bbff-f24e7d4dc4a4` |
| 850215 | ecephys_850215_2026-03-23_13-01-09 | `65be5c44-06de-4c11-9c81-4c615d5ad313` | `013b0101-402a-43b9-846c-82e4b678ed19` | `d61a9df7-a033-4416-9c17-7a4bfa29e59d` |
| 850217 | ecephys_850217_2026-04-02_13-42-31 | `dabc217c-11e2-4aa3-9db3-80ca5e56d65f` | `86662475-5783-4499-b2ae-8f9f991b1670` |  |
| 850217 | ecephys_850217_2026-04-03_11-40-38 | `8af0bfdb-218e-4c8b-82f0-7e037954cfb5` | `d4723ba9-4485-4c4d-84c0-0de9ee1351f9` | `0300b0de-f53d-40eb-a924-8526d820d963` |
| 850217 | ecephys_850217_2026-04-06_12-58-25 | `b4d1bcf6-c571-4113-ae00-efeb6043568b` | `d095cab2-91ee-45d7-b67e-c9d308d34bbe` | `8fd78134-40a3-48c6-96b5-f3fc049fdc23` |
| 852252 | ecephys_852252_2026-06-24_12-17-44 | `8f6382c6-6d44-4019-bc6a-bcf4e94c5171` | `4d5bab43-7907-483b-8b5e-268b94c730ae` |  |
| 852252 | ecephys_852252_2026-06-25_12-58-54 | `c3025f6d-c722-4362-bbe5-cd4f4e0dc2b2` | `d5ec4711-721a-444d-8968-b05635455c0c` |  |
| 852252 | ecephys_852252_2026-06-26_11-48-53 | `bf93f041-6189-4760-9718-a35781a02bd8` | `43a4106f-9ca7-436d-b3fd-a282ddb474fe` |  |
| 852255 | ecephys_852255_2026-06-16_12-45-55 | `d5119dec-4d83-44b8-84e2-27d3a8f8388c` | `cc242196-c1cc-475e-9846-a27733c7ecbd` |  |
| 852255 | ecephys_852255_2026-06-17_13-19-16 | `7e68b1ec-1767-4d9b-b61d-920c5aa32adc` | `d78d83fa-c417-4704-8bb9-4fac4a9c81b1` |  |
| 852255 | ecephys_852255_2026-06-18_14-04-51 | `458ddc05-a2b6-4bf1-8e74-d173cebf7d92` | `583ac078-ba69-47bc-8edc-15a74dcfbf51` |  |
| 852255 | ecephys_852255_2026-06-22_14-07-12 | `4c23e543-42c4-43ad-81b2-8d557d74108e` | `fa3acca4-7c8c-4348-99ba-49faf3ed64d6` |  |
| 854390 | ecephys_854390_2026-04-22_10-18-59 | `5c3ced5c-4e7c-40e0-9d35-076f006b1efc` | `77e6fefc-3e65-4ae4-9957-0f6b231decfc` | `9c2011bf-5b08-4cc0-8c41-7fafe57c0a96` |
| 854390 | ecephys_854390_2026-04-23_10-33-36 | `a9a22920-43f3-456a-b7db-ac27cbfde897` | `f41ccfd5-d077-4290-a49f-7f84670dc3cd` | `e457c616-0bb7-4446-a742-99ffed6c119c` |
| 854390 | ecephys_854390_2026-04-24_10-19-35 | `df5de2ab-c6c3-4143-ac47-f8886fa6515d` | `bc559704-6c30-4198-9e8c-2ccba2c32ce0` | `bfe0c07f-16f0-4214-a7e2-0d559c9592b9` |
| 854390 | ecephys_854390_2026-04-27_10-32-52 | `ea1c16c1-42f8-48d4-941c-1cd4ab4ca0d2` | `40b8770e-9eca-46db-b6e9-f36d0873ab18` | `587d1f80-ec82-416f-8058-a023d0e410f3` |
| 856845 | ecephys_856845_2026-05-27_13-08-26 | `81ab42f1-5a61-4b5b-84c0-73097700e652` | `1f867e3e-6656-440c-ad84-2ec381dc30f4` |  |
| 856845 | ecephys_856845_2026-05-28_??-??-?? |  |  |  |
| 856845 | ecephys_856845_2026-05-29_13-06-55 | `69fcd692-b42b-43e7-a4ca-cbf044eebaa2` | `cb3a8fb5-10a8-4cbb-a56e-f812769c27c4` |  |
| 856845 | ecephys_856845_2026-06-01_??-??-?? |  |  |  |
| 856847 | ecephys_856847_2026-06-02_??-??-?? |  |  |  |
| 856847 | ecephys_856847_2026-06-03_13-09-46 | `6bd89739-7ba7-49d8-bfeb-da99c7542c29` | `b89730a2-a84e-4333-b122-24fd4f4f7211` |  |
| 856847 | ecephys_856847_2026-06-04_??-??-?? |  |  |  |
| 856847 | ecephys_856847_2026-06-05_11-22-31 | `d18d2af2-4103-4dd4-963d-682358c0c7c6` | `7c6f114e-390f-4d1c-96db-f397c79524a6` |  |
| 857681 | ecephys_857681_2026-08-13_10-34-33 | `c135e61f-2e25-420a-9c83-532a78338cd2` | `9fabf4b8-539b-4deb-8e30-4bb0ed4f0d70` |  |
| 857681 | ecephys_857681_2026-08-14_10-28-32 | `b7250bd4-e74e-4422-a055-7f351f36e202` | `8ec658e6-505a-4d9f-b4a3-233b34135c29` |  |
| 857681 | ecephys_857681_2026-08-17_10-25-26 | `de346fda-1457-4d26-b4f0-1ae2a7c2d17e` | `a0cd6292-7a4a-44d4-ac47-24a705b65912` |  |
| 857681 | ecephys_857681_2026-08-18_09-59-00 | `6bb73311-18b5-41c0-ac2a-2670167bce44` | `2654fc29-b16d-4c19-887c-86aeb5ce5c1d` |  |
| 859582 | ecephys_859582_2026-06-29_09-50-42 | `70262550-8651-4514-855e-b3b93263bacb` | `4f02b8cd-73d2-4a69-a9bb-1311fef3601b` |  |
| 859582 | ecephys_859582_2026-06-30_09-57-58 | `b180e196-0305-4eb1-ad7f-28e8fa9ccdc8` | `472979b4-a3da-4042-b55d-cda6a8af2262` |  |
| 859582 | ecephys_859582_2026-07-01_10-03-33 | `27a2f7fa-68db-4df7-a884-2d42336157f4` | `4f9fa6ee-2fc8-411b-801b-1f5e99bbd6bf` |  |
| 859582 | ecephys_859582_2026-07-02_09-42-32 | `520a1ca7-f848-4ba2-902a-89f499da79df` | `4276f22f-0175-4f3e-b321-05fdfd9857ed` |  |
| 859583 | ecephys_859583_2026-05-14_13-04-30 | `8e4eedd4-3acd-47fe-97e1-bec350e9d451` | `492eaa32-257c-40b3-96b8-eed9835481ec` |  |
| 859583 | ecephys_859583_2026-05-15_11-43-26 | `7dada8d1-11de-4928-b3e6-003a9dd563f1` | `b7e3cdb7-0c60-43a8-a06e-61f57a85e75d` |  |
| 859583 | ecephys_859583_2026-05-19_13-05-18 | `d1a7f39a-7c96-4404-af37-20f2ef5fd943` | `09109a4d-aadc-48bd-bc03-855b72dbbe1a` |  |
| 859583 | ecephys_859583_2026-05-20_12-28-48 | `155ad2cc-7dae-4e6c-a233-4aee090fc142` | `43915f30-4639-44ae-922a-af6efe3fc111` |  |
| 859584 | ecephys_859584_2026-07-06_09-55-34 | `858b6c06-1d35-4e7c-bd62-4dc9ee911ce4` | `e2f8b08c-6e66-4b63-b30a-99be9e836f8c` |  |
| 859584 | ecephys_859584_2026-07-07_09-34-53 | `16cec8ab-062b-4e89-ba5b-491ed9369af0` | `d8b74933-8825-4638-95aa-0845faf3651e` |  |
| 859584 | ecephys_859584_2026-07-08_11-32-00 | `a9431166-6567-4db9-a6c7-b5532a2beadc` | `11d42b88-6276-448f-b5a1-9fac6f280eee` |  |
| 859584 | ecephys_859584_2026-07-09_09-37-30 | `a417daa9-4fea-409d-91a6-9d3e5f8ffaa9` | `fbcfa604-acb4-4516-9c7e-4018433a6832` |  |
| 862025 | ecephys_862025_2026-08-04_11-16-16 | `e4e74a5a-e385-4cdd-80a5-47ada76e2799` | `55afe830-bb1b-4863-985a-9b2328677ae7` |  |
| 862025 | ecephys_862025_2026-08-05_??-??-?? |  |  |  |
| 862025 | ecephys_862025_2026-08-06_11-30-52 | `19def93e-3a19-4e30-bf98-5dd2843ed49a` | `8c1fdf49-0f63-4192-bcc4-a0fb42d06b57` |  |
| 862027 | ecephys_862027_2026-09-15_11-26-31 | `7d45a728-17bf-4d96-8446-aa6b22e69e23` | `422ea855-951a-48d3-926e-e11895fb377a` |  |
| 862027 | ecephys_862027_2026-09-16_11-04-15 | `bfab0fe7-54a6-4c09-b1ee-49658c90d3c8` | `2f24785d-aec7-4526-b134-3eb20a4b7071` |  |
| 872697 | ecephys_872697_2026-08-31_10-48-32 | `14539784-37ce-49b9-aa80-9affcb75863a` | `27f90da9-3a8d-452f-b35f-72c660e32faa` |  |
| 872697 | ecephys_872697_2026-09-01_11-08-20 | `8b3739b9-3565-4ae9-9acc-87a87a8edb4b` | `f8b1d740-411c-4ec7-b133-af42bb80ee65` |  |
| 872697 | ecephys_872697_2026-09-02_10-40-31 | `1390a50c-8223-4f40-adce-3da062c0f1ef` | `bdab879d-a14b-400c-ba82-65cf6e67a8b0` |  |
| 872697 | ecephys_872697_2026-09-03_10-57-10 | `05b21f99-c235-4603-85b5-c7b08d55e800` | `de73ea0f-5541-4acc-b779-d1bddd7b11b5` |  |

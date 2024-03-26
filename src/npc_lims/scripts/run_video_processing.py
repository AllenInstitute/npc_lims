import npc_lims

DLC_EYE_CAPSULE_ID = "4cf0be83-2245-4bb1-a55c-a78201b14bfe"
DLC_PLOT_CAPSULE_ID = "85097267-9d7b-40a4-81db-75f38a35c67e"


def main() -> None:
    npc_lims.process_capsule_or_pipeline_queue(
        DLC_PLOT_CAPSULE_ID,
        "dlc_pupil_validation",
        rerun_all_jobs=True,
        create_data_assets_from_results=False,
    )


if __name__ == "__main__":
    main()

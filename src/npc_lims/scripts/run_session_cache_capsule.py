from codeocean.computation import RunParams

import npc_lims

NPC_SESSIONS_CACHE_CAPSULE_ID = "99b14fe5-e66a-45fd-a2f5-1835aa61ced1"


def main() -> None:
    npc_lims.get_codeocean_client().computations.run_capsule(
        RunParams(
            capsule_id=NPC_SESSIONS_CACHE_CAPSULE_ID,
            data_assets=[],
        )
    )


if __name__ == "__main__":
    main()

from codeocean.computation import RunParams

import npc_lims.metadata.codeocean_utils as codeocean_utils
import npc_lims.status

NWB_EXPORT_CAPSULE_ID = "43f661ab-b29b-4a64-bb70-2d59ac58a9af"
"""Uses `npc_sessions` to write nwb. Requires `session_id` as input else it will
run with default test session."""


def main() -> None:
    for session in npc_lims.status.get_session_info():
        data_assets = []

        if session.is_uploaded:
            data_assets.append(
                {
                    "id": codeocean_utils.get_session_raw_data_asset(session.id).id,
                    "mount": "raw",
                }
            )

        if session.is_sorted:
            data_assets.append(
                {
                    "id": codeocean_utils.get_session_sorted_data_asset(session.id).id,
                    "mount": "sorted",
                }
            )

        codeocean_utils.get_codeocean_client().run_capsule(
            RunParams(
                capsule_id=NWB_EXPORT_CAPSULE_ID,
                data_assets=data_assets,
                parameters=[session.id],
            )
        )


if __name__ == "__main__":
    import dotenv

    _ = dotenv.load_dotenv(
        dotenv.find_dotenv(usecwd=True)
    )  # take environment variables from .env

    main()

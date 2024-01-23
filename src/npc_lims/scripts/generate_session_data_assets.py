import npc_lims.metadata.codeocean as codeocean


def create_eye_tracking_data_asset_for_sessions() -> None:
    session = "676909_2023-12-13"
    codeocean.create_session_data_asset(session, "dlc_eye")


if __name__ == "__main__":
    create_eye_tracking_data_asset_for_sessions()

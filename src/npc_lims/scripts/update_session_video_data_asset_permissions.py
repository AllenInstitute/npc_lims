import npc_lims.status as status


def update_helper(session_info: status.SessionInfo, model_name: str) -> None:
    """
    if getattr(session_info, f"is_{model_name}"):
        try:
            model_session_data = codeocean.get_model_data_asset(
                session_info.id, model_name
            )
            codeocean.update_permissions_for_data_asset(model_session_data)
        except (ValueError, FileNotFoundError):
            pass
    """
    pass


def main() -> None:
    for session_info in status.get_session_info():
        if not session_info.is_uploaded:
            continue

        update_helper(session_info, "dlc_eye")
        update_helper(session_info, "dlc_side")
        update_helper(session_info, "dlc_face")
        update_helper(session_info, "facemap")


if __name__ == "__main__":
    main()

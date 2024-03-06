import npc_lims.status as status


def generate_helper(session_info: status.SessionInfo, model_name: str) -> None:
    """
    if not getattr(session_info, f"is_{model_name}"):
        try:
            codeocean.create_session_data_asset(
                session_info.id, model_name, computation_id=""
            )
        except UnboundLocalError:
            pass
    """
    pass


def main() -> None:
    for session_info in status.get_session_info():
        if not session_info.is_uploaded:
            continue

        generate_helper(session_info, "dlc_eye")
        generate_helper(session_info, "dlc_face")
        generate_helper(session_info, "dlc_side")
        generate_helper(session_info, "facemap")


if __name__ == "__main__":
    main()

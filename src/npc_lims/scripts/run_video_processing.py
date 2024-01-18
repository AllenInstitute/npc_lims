import npc_lims.metadata.codeocean as codeocean
import npc_lims.status as status


def main() -> None:
    for session_info in status.get_session_info():
        if not session_info.is_uploaded:
            continue

        """
        codeocean.run_capsule(session_info.id, "dlc_eye")
        codeocean.run_capsule(session_info.id, "dlc_front")
        codeocean.run_capsule(session_info.id, "dlc_side")
        codeocean.run_capsule(session_info.id, "facemap")
        """
        codeocean.run_capsule(session_info.id, "video_pipeline")


if __name__ == "__main__":
    main()

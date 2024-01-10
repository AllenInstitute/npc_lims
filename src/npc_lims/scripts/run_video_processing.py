import npc_lims.metadata.codeocean as codeocean
import npc_lims.status as status

def main() -> None:
    for session_info in status.get_session_info():
        if not session_info.is_uploaded:
            continue

        codeocean.run_eye_tracking_capsule(session_info.id)
        codeocean.run_dlc_side_tracking_capsule(session_info.id)
        codeocean.run_dlc_face_tracking_capsule(session_info.id)
        codeocean.run_facemap_capsule(session_info.id)

if __name__ == '__main__':
    main()
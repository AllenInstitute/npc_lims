import npc_lims.status as status


def run_helper(session_info: status.SessionInfo, model_name: str, num_jobs: int) -> int:
    if not getattr(session_info, f"is_{model_name}"):
        # codeocean.run_capsule_or_pipeline(session_info.id, model_name)
        num_jobs += 1

    return num_jobs


def main() -> None:
    num_jobs = 0
    for session_info in status.get_session_info():
        if not session_info.is_uploaded:
            continue

        num_jobs = run_helper(session_info, "dlc_eye", num_jobs)
        num_jobs = run_helper(session_info, "dlc_side", num_jobs)
        num_jobs = run_helper(session_info, "dlc_face", num_jobs)
        num_jobs = run_helper(session_info, "facemap", num_jobs)

        if num_jobs == 12:
            break


if __name__ == "__main__":
    main()

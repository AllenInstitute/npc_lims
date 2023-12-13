# npc_lims

**n**euro**p**ixels **c**loud **l**ab **i**nformation **m**anagement **s**ystem
Tools to fetch and update paths, metadata and state for Mindscope Neuropixels sessions, in the cloud.

[![PyPI](https://img.shields.io/pypi/v/npc-lims.svg?label=PyPI&color=blue)](https://pypi.org/project/npc-lims/)
[![Python version](https://img.shields.io/pypi/pyversions/npc-lims)](https://pypi.org/project/npc-lims/)

[![Coverage](https://img.shields.io/codecov/c/github/alleninstitute/npc_lims?logo=codecov)](https://app.codecov.io/github/AllenInstitute/npc_lims)
[![CI/CD](https://img.shields.io/github/actions/workflow/status/alleninstitute/npc_lims/publish.yml?label=CI/CD&logo=github)](https://github.com/alleninstitute/npc_lims/actions/workflows/publish.yml)
[![GitHub
issues](https://img.shields.io/github/issues/alleninstitute/npc_lims?logo=github)](https://github.com/alleninstitute/npc_lims/issues)

## quickstart

- make a new Python >=3.9 virtual environment with conda or venv (lighter option, since this package does not require pandas, numpy etc.):
  ```bash
  python -m venv .venv
  ```
- activate the virtual environment:
  - Windows
  ```cmd
  .venv\scripts\activate
  ```
  - Unix
  ```bash
  source .venv/bin/activate.sh
  ```
- install the package:
  ```bash
  python -m pip install npc_lims
  ```
- setup credentials
  - required environment variables:
    - AWS S3
      - `AWS_DEFAULT_REGION`
      - `AWS_ACCESS_KEY_ID`
      - `AWS_SECRET_ACCESS_KEY`
      - to find and read files on S3
      - must have read access on relevant aind buckets
      - can be in a standard `~/.aws` location, as used by AWS CLI or boto3
    - CodeOcean API
      - `CODE_OCEAN_API_TOKEN`
      - `CODE_OCEAN_DOMAIN`
      - to find processed data in "data assets" via the Codeocean API
      - generated in CodeOcean:
        - right click on `Account` (bottom left, person icon)
        - click `User Secrets` - these are secrets than can be made available as environment variables in CodeOcean capsules
        - go to `Access Tokens` and click `Generate new token` - this is for programatically querying CodeOcean's databases
          - in `Token Name` enter `Codeocean API (read)` and check `read` on capsules and datasets
          - a token will be generated: click copy (storing it in a password manager, if you use one)
        - head back to `User Secrets` where we'll paste it into a new secret via `Add secret > API credentials` - in `description` enter `Codeocean API (read)` - in `API key` enter `CODE_OCEAN_API_KEY` - in `API secret` paste the copied secret from before (should start with `cop_`...)
          `CODE_OCEAN_DOMAIN` is the codeocean https address, up to and including `.org`
  - environment variables can also be specified in a file named `.env` in the current working directory
    - example: https://www.dotenv.org/docs/security/env.html
    - be very careful that this file does not get pushed to public locations, e.g. github
      - if using git, add it to a `.gitignore` file in your project's root directory:
      ```gitignore
      .env*
      ```
- now in Python we can find sessions that are available to work with:

  ```python
      >>> import npc_lims;

  # get a sequence of `SessionInfo` dataclass instances, one per session:
      >>> tracked_sessions: tuple[npc_lims.SessionInfo, ...] = npc_lims.get_session_info()

  # each `SessionInfo` instance has minimal metadata about its session:
      >>> tracked_sessions[0]                 # doctest: +SKIP
      npc_lims.SessionInfo(id='626791_2022-08-15', subject=626791, date='2022-08-15', idx=0, project='DRPilotSession', is_ephys=True, is_sync=True, allen_path=PosixUPath('//allen/programs/mindscope/workgroups/dynamicrouting/PilotEphys/Task 2 pilot/DRpilot_626791_20220815'))
          >>> tracked_sessions[0].is_ephys        # doctest: +SKIP
      False

  # currently, we're only tracking behavior and ephys sessions that use variants of https://github.com/samgale/DynamicRoutingTask/blob/main/TaskControl.py:
      >>> all(s.date.year >= 2022 for s in tracked_sessions)
      True

  ```

- "tracked sessions" are discovered via 3 routes:
  - https://github.com/AllenInstitute/npc_lims/blob/main/tracked_sessions.yaml
  - `\\allen\programs\mindscope\workgroups\dynamicrouting\DynamicRoutingTask\DynamicRoutingTraining.xlsx`
  - `\\allen\programs\mindscope\workgroups\dynamicrouting\DynamicRoutingTask\DynamicRoutingTrainingNSB.xlsx`

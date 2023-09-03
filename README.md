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

```bash
pip install npc_lims
```

Get some minimal info on all the tracked sessions available to work with:
```python
>>> from npc_lims import tracked as tracked_sessions;

# each record in the sequence has info about one session:
>>> tracked_sessions[0]._fields
('session', 'subject', 'date', 'idx', 'project', 'is_ephys', 'is_sync', 'allen_path')
>>> tracked_sessions[0].is_ephys
True
>>> all(s.date.year >= 2022 for s in tracked_sessions)
True

```
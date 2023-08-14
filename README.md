# npc_lims

**n**euro**p**ixels **c**loud **lims**
	
Tools to fetch and update paths, metadata and state for Mindscope Neuropixels sessions, in the cloud.   

[![Python
Versions](https://img.shields.io/pypi/pyversions/npc_lims.svg)](https://pypi.python.org/pypi/npc-lims/)
## quickstart

```bash
pip install npc_lims
```

Get some minimal info on all the tracked sessions available to work with:
```python
>>> from npc_lims import tracked as tracked_sessions;

# each record in the sequence has info about one session:
>>> tracked_sessions[0]._fields
('session', 'subject', 'date', 'idx', 'project', 'is_ephys', 'is_sync')
>>> tracked_sessions[0].is_ephys
True
>>> all(s.date.year >= 2022 for s in tracked_sessions)
True

```
# npc_lims

**n**euro**p**ixels **c**loud **session**
	
Interfaces for working with behavior and epyhys sessions from the
Mindscope Neuropixels team, in the cloud.

[![Python
Versions](https://img.shields.io/pypi/pyversions/npc_session.svg)](https://pypi.python.org/pypi/npc-session/)
## quickstart

```bash
pip install npc_session
```

Parse a normalized IDs from a path or string:
```python
>>> from npc_session import SessionRecord;

>>> s = SessionRecord('//allen/programs/mindscope/workgroups/templeton/TTOC/2022-07-26_14-09-36_366122')
>>> s
'366122_2022-07-26'
>>> s.subject
366122
>>> s.date
'2022-07-26'
>>> s.date.year
2022

```

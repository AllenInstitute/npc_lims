from __future__ import annotations
from upath import UPath
import npc_session
from aind_codeocean_api import codeocean
from functools import reduce
import operator

def get_session_s3_paths(session:npc_session.SessionRecord) -> tuple[UPath, ...]:
    session_id = session.id[0:session.id.rindex('_')]
    raw_data_root = UPath('s3://aind-ephys-data')
    raw_session_s3_path = tuple(raw_data_root.glob('*{}*'.format(session_id)))[0]
    directories = tuple(directory for directory in list(raw_session_s3_path.iterdir()) if directory.is_dir())
    first_level_files_directories = tuple(tuple(directory.iterdir()) for directory in directories)
    
    return reduce(operator.add, first_level_files_directories)

def get_session_data_assets(session:npc_session.SessionRecord) -> tuple[dict, ...]:
    session_id = session.id[0:session.id.rindex('_')]
    # Maybe extract out from aind api later
    token = 'API_TOKEN'
    domain = "DOMAIN"
    codeocean_client = codeocean.CodeOceanClient(domain=domain, token=token)
    data_assets = codeocean_client.search_data_assets(query='subject id: {}'.format(session_id[0:session_id.index('_')])).json()['results']
    session_data_assets = tuple(data_asset for data_asset in data_assets if session_id in data_asset['name'])

    return session_data_assets

if __name__ == '__main__':
    session_record = npc_session.SessionRecord('660023_20230808')
    s3_paths = get_session_s3_paths(session_record)
    data_assets = get_session_data_assets(session_record)
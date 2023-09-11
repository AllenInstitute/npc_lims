import dotenv

import npc_lims.status.tracked_sessions
from npc_lims.jobs import *
from npc_lims.metadata import *
from npc_lims.paths import *
from npc_lims.status import *
from npc_lims.status.get_day_from_status import *

_ = dotenv.load_dotenv(
    dotenv.find_dotenv(usecwd=True)
)  # take environment variables from .env

tracked = npc_lims.status.tracked_sessions.get_session_info()

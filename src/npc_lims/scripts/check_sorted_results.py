import datetime

import npc_lims

SORTING_PIPELINE_ID = "1f8f159a-7670-47a9-baf1-078905fc9c2e"

client = npc_lims.get_codeocean_client()

results: list[dict[str, int | str]] = client.get_capsule_computations(SORTING_PIPELINE_ID).json()

march_3 = datetime.datetime(2024, 3, 3).timestamp()
march_6 = datetime.datetime(2024, 3, 6).timestamp()
filtered_results = [result for result in results if march_3 <= result["created"] <= march_6]

all_result_names = set()

for result in filtered_results:
    if not result.get('has_results'):
        continue
    all_result_names.update(set(npc_lims.get_result_names(result["id"])))
    
    if any(name in result_item_names for name in ("temp", "tmp")):
        print(datetime.datetime.fromtimestamp(result["created"]))

LABELS_PREFIX = "labels.swarmchestrate.eu/"

def get_labels_from_sat(nodes: dict, offer: dict) -> dict:
    
    labels = {}
    for ms_id, spec in nodes.items():
        if not spec.get("type", "").endswith("Microservice"):
            continue
        if ms_id not in offer:
            continue
        if "colocated" in offer[ms_id]:
            continue
        labels[ms_id] = {
            "node_labels": {
                f"{LABELS_PREFIX}ms_id": ms_id
            }
        }
    return labels
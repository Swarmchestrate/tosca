import os

from .utils import extract_properties


def get_cluster(rdt, resource_suffix=None):
    resource_suffix = (
        resource_suffix or os.getenv("TOSCA_RESOURCE_SUFFIX") or "::Capacity"
    )

    resources = {}

    for name, node in rdt.nodeTemplates._to_dict().items():
        is_resource = any(
            t.get("parent", "").endswith(resource_suffix) or k.endswith(resource_suffix)
            for k, t in node.get("types", {}).items()
        )

        if not is_resource:
            continue

        extracted = extract_properties(node.get("properties", {}))

        extracted["node_labels"] = {
            "labels.swarmchestrate.io/ms_id": node.get("metadata", {}).get("ms_id")
        }
        resources[name] = extracted

    return resources

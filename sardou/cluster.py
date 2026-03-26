import os


def get_cluster(rdt, resource_suffix=None):
    def flatten(val):
        if isinstance(val, dict):
            if "$primitive" in val:
                return val["$primitive"]
            if "$list" in val:
                return [flatten(v) for v in val["$list"]]
            if "$map" in val:
                out = {}
                for pair in val["$map"]:
                    key = flatten(pair.get("$key"))
                    value = flatten(pair)
                    out[key] = value
                return out
            return {k: flatten(v) for k, v in val.items()}
        return val

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

        extracted = {}

        def extract_properties(prop_dict):
            for k, v in prop_dict.items():
                meta = v.get("$meta", {}) if isinstance(v, dict) else {}
                alias = meta.get("metadata", {}).get("alias")
                extracted_key = alias if alias else k
                extracted[extracted_key] = flatten(v)

        extract_properties(node.get("properties", {}))

        extracted["node_labels"] = {
            "labels.swarmchestrate.io/ms_id": node.get("metadata", {}).get("ms_id")
        }
        resources[name] = extracted

    return resources

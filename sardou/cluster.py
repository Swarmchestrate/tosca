import json
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
        types = node.get("types", {})

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

        def extract_cap_props(cap_dict):
            for cap in cap_dict.values():
                extract_properties(cap.get("properties", {}))
                if "capabilities" in cap:
                    extract_cap_props(cap["capabilities"])

        extract_cap_props(node.get("capabilities", {}))

        for type_def in types.values():
            for k, prop_def in type_def.get("properties", {}).items():
                if (
                    k not in extracted
                    and isinstance(prop_def, dict)
                    and "default" in prop_def
                ):
                    extracted[k] = flatten({"$primitive": prop_def["default"]})

            def extract_type_cap_defaults(cap_dict):
                for cap in cap_dict.values():
                    for k, prop_def in cap.get("properties", {}).items():
                        if (
                            k not in extracted
                            and isinstance(prop_def, dict)
                            and "default" in prop_def
                        ):
                            extracted[k] = flatten(
                                {"$primitive": prop_def["default"]}
                            )
                    if "capabilities" in cap:
                        extract_type_cap_defaults(cap["capabilities"])

            for type_cap in type_def.get("capabilities", {}).values():
                extract_type_cap_defaults(type_cap.get("capabilities", {}))

        resources[name] = extracted

    return json.dumps(resources, indent=2)

_CAPACITY_KEY = "capacity"


def _unwrap(value):
    if isinstance(value, dict):
        if "$primitive" in value:
            return value["$primitive"]
        if "$list" in value:
            return [_unwrap(item) for item in value["$list"]]
        if "$map" in value:
            return dict(_unwrap_map_entry(entry) for entry in value["$map"])
    return value


def _unwrap_map_entry(entry):
    key = _unwrap(entry["$key"])
    value = _unwrap({k: v for k, v in entry.items() if k != "$key"})
    return key, value


def _is_overall(node: dict) -> bool:
    types = node.get("types") or {}
    return any("OverallCapacity" in type_name for type_name in types)


def _get_res_key(node: dict) -> str:
    res_type = (
        _unwrap(
            node.get("capabilities", {})
            .get("resource", {})
            .get("properties", {})
            .get("type", {})
        )
        or ""
    )

    return "edge_instances" if "edge" in res_type.lower() else "cloud_flavours"


def _process_node(name, node, capabilities, capacities, capacity_by):
    res_key = _get_res_key(node)
    capacities.setdefault(res_key, {})[name] = {}

    for cap_name, capability in capabilities.items():
        props = capability.get("properties", {}) or {}
        if props and cap_name != _CAPACITY_KEY:
            capacities[res_key][name][cap_name] = {
                k: _unwrap(v) for k, v in props.items()
            }

    instances = (
        capabilities.get(_CAPACITY_KEY, {}).get("properties", {}).get("instances")
    )
    if res_key == "cloud_flavours":
        capacity_by[name] = _unwrap(instances) if instances is not None else 1


def extract_capacities(processed_nodes: dict) -> dict:
    capacity_by = {}
    capacities = {}
    overall = None

    for name, node in processed_nodes.items():
        capabilities = node.get("capabilities", {}) or {}
        if _is_overall(node):
            cap_props = capabilities.get(_CAPACITY_KEY, {}).get("properties", {})
            overall = {k: _unwrap(v) for k, v in cap_props.items()}
            continue

        _process_node(name, node, capabilities, capacities, capacity_by)

    if overall is not None:
        capacities["cloud_capacity_raw"] = overall
    elif capacity_by:
        capacities["cloud_capacity_flavour"] = capacity_by

    return capacities

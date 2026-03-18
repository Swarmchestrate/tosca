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
    return any("OverallCapacity" in type_name for type_name in types.keys())


def _get_res_key(node: dict) -> str:
    res_type = _unwrap(
        node.get("capabilities", {}).get("resource", {}).get("properties", {}).get("type", {})
    ) or ""

    return "edge" if "edge" in res_type.lower() else "flavour"


def extract_capacities(processed_nodes: dict):
    capacity_by = {}
    capacities = {}
    overall = None

    for name, node in processed_nodes.items():
        caps = node.get("capabilities", {}) or {}
        if _is_overall(node):
            cap_props = caps.get("capacity", {}).get("properties", {})
            overall = {k: _unwrap(v) for k, v in cap_props.items()}
            continue

        res_key = _get_res_key(node)
        capacities.setdefault(res_key, {})[name] = {}
        for cap_name, cap in caps.items():
            props = cap.get("properties", {}) or {}
            if props and cap_name != "capacity":
                capacities[res_key][name][cap_name] = {
                    k: _unwrap(v) for k, v in props.items()
                }

        if overall is not None:
            continue
        inst = caps.get("capacity", {}).get("properties", {}).get("instances")
        if res_key == "flavour":
            capacity_by[name] = _unwrap(inst) if inst is not None else 1

    if capacity_by:
        capacities["capacity_flavour"] = capacity_by

    if overall is not None:
        capacities["capacity_raw"] = overall

    return capacities

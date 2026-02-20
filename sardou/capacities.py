def _unwrap(v):
    if isinstance(v, dict):
        if "$primitive" in v:
            return v["$primitive"]
        if "$list" in v:
            return [_unwrap(x) for x in v["$list"]]
        if "$map" in v:
            return {_unwrap(entry["$key"]): _unwrap({k: x for k, x in entry.items() if k != "$key"}) for entry in v["$map"]}
    return v


def _is_overall(node: dict) -> bool:
    types = node.get("types") or {}
    return any("OverallCapacity" in type_name for type_name in types.keys())


def extract_capacities(processed_nodes: dict):
    flavour_definition = {}
    capacity_by = {}
    capacities = {}
    overall = None

    
    for _, node in processed_nodes.items():
        if _is_overall(node):
            cap_props = node.get("capabilities", {}).get("capacity", {}).get("properties", {}) or {}
            overall = {k: _unwrap(v) for k, v in cap_props.items()}
            break

    
    for name, node in processed_nodes.items():
        if _is_overall(node):
            continue

        caps = node.get("capabilities", {}) or {}
        flavour_definition[name] = {}
        for cap_name, cap in caps.items():
            props = cap.get("properties", {}) or {}
            if props and cap_name != "capacity":
                flavour_definition[name][cap_name] = {k: _unwrap(v) for k, v in props.items()}

    if overall is not None:
        capacities = {"flavour": flavour_definition, "capacity_raw": overall}
    else:
        for name, node in processed_nodes.items():
            caps = node.get("capabilities", {}) or {}
            inst = caps.get("capacity", {}).get("properties", {}).get("instances")
            capacity_by[name] = _unwrap(inst) if inst is not None else 1
        
        capacities = {"flavour": flavour_definition, "capacity_flavour": capacity_by}

    return capacities

def _unwrap(v):
    if isinstance(v, dict):
        if "$primitive" in v:
            return v["$primitive"]
        if "$list" in v:
            return [_unwrap(x) for x in v["$list"]]
    return v


def _is_overall(node: dict) -> bool:
    types = node.get("types") or {}
    return any("OverallCapacity" in type_name for type_name in types.keys())


def extract_capacities(processed_nodes: dict):
    flavor_definition = {}
    capacity_by = {}
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
        flavor_definition[name] = {}
        for cap_name, cap in caps.items():
            props = cap.get("properties", {}) or {}
            if props:
                flavor_definition[name][cap_name] = {k: _unwrap(v) for k, v in props.items()}

    
    if overall is not None:
        capacity_by = overall
    else:
        for name, node in processed_nodes.items():
            caps = node.get("capabilities", {}) or {}
            inst = caps.get("capacity", {}).get("properties", {}).get("instances")
            capacity_by[name] = _unwrap(inst) if inst is not None else 1

    return flavor_definition, capacity_by

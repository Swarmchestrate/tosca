"""
TOSCA Resource Requirements Extractor
Converts TOSCA node_filter data to expression + colocation format
"""

OPERATOR_MAP = {
    "$greater_or_equal": ">=",
    "$greater_than": ">",
    "$less_or_equal": "<=",
    "$less_than": "<",
    "$equal": "==",
    "$not_equal": "!=",
    "$has_any_entry": "has_any_entry",
}

COLOCATION_POLICY = "Scheduling.Colocation"


def get_properties(relationship):
    """Convert properties in relationship to node properties"""
    properties = relationship.get("properties", {})
    if not isinstance(properties, dict):
        return {}

    return properties


def build_expression(node_filter):
    """Convert TOSCA node_filter to a lambda expression string."""
    conditions = node_filter.get("$and", [])
    parts = []

    for condition in conditions:
        for constraint_func, args in condition.items():
            if len(args) < 2:
                continue
            property_path = args[0].get("$get_property", [])
            if len(property_path) < 5:
                continue

            capability_type = property_path[3]
            property_name = property_path[4]
            value = args[1]
            op = OPERATOR_MAP.get(constraint_func, "==")

            key = f"{capability_type}.{property_name}"
            if op == "has_any_entry":
                parts.append(f"(any(entry in vals['{key}'] for entry in {value}))")
            elif isinstance(value, str):
                parts.append(f"(vals['{key}'] {op} '{value}')")
            else:
                parts.append(f"(vals['{key}'] {op} {value})")

    body = " and ".join(parts)
    return f"lambda vals: ({body})"


def extract_colocation_groups(tosca_dict):
    """Extract colocation groups from policies."""
    groups = []
    policies = tosca_dict.get("service_template", {}).get("policies", [])
    for policy in policies:
        for policy_name, policy_data in policy.items():
            if policy_data.get("type", "").endswith(COLOCATION_POLICY):
                targets = policy_data.get("targets", [])
                if targets:
                    groups.append(targets)
    return groups


def extract_reqs_with_filter(tosca_dict):
    reqs_with_filter = {}
    node_templates = tosca_dict.get("service_template", {}).get("node_templates", {})
    for node_name, node_data in node_templates.items():
        for req in node_data.get("requirements", []):
            for _, req_data in req.items():
                if "node_filter" in req_data:
                    reqs_with_filter[node_name] = req_data
    return reqs_with_filter


def tosca_to_ask_dict(tosca_dict):
    """
    Convert TOSCA dict to ask format dict with expressions and colocation.
    """
    reqs_with_filter = extract_reqs_with_filter(tosca_dict)
    colocation_groups = extract_colocation_groups(tosca_dict)

    # Build a map: node -> (representative, list of colocated peers)
    node_to_representative = {}
    representative_colocated = {}

    for group in colocation_groups:
        rep = group[0]
        others = group[1:]
        representative_colocated[rep] = others
        for node in group:
            node_to_representative[node] = rep

    result = {}
    for node_name, req_data in reqs_with_filter.items():
        # Skip non-representative nodes in a colocation group
        if (
            node_name in node_to_representative
            and node_to_representative[node_name] != node_name
        ):
            continue

        node_filter = req_data["node_filter"]
        relationship = req_data.get("relationship", {})
        result[node_name] = {
            "expression": build_expression(node_filter),
            "colocated": representative_colocated.get(node_name, []),
            "properties": get_properties(relationship),
        }

    return result

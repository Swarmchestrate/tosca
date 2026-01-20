"""
TOSCA Resource Requirements Extractor
Converts TOSCA node_filter data to ask.yaml format
"""

from datetime import datetime


def convert_node_filter_to_capabilities(node_filter):
    """Convert TOSCA node_filter to capabilities format"""
    capabilities = {}

    # Extract conditions from $and
    conditions = node_filter.get("$and", [])

    for condition in conditions:
        for constraint_func, args in condition.items():
            if len(args) >= 2:
                # Parse the property path: [SELF, TARGET, CAPABILITY, capability_type, property_name]
                property_path = args[0].get("$get_property", [])
                if len(property_path) >= 5:
                    capability_type = property_path[3]
                    property_name = property_path[4]
                    constraint_value = args[1]

                    # Initialize capability structure
                    if capability_type not in capabilities:
                        capabilities[capability_type] = {"properties": {}}

                    # Set the constraint
                    if constraint_func == "$equal":
                        capabilities[capability_type]["properties"][property_name] = (
                            constraint_value
                        )
                    else:
                        capabilities[capability_type]["properties"][property_name] = {
                            constraint_func: constraint_value
                        }

    return capabilities


def extract_nodes_with_filter(tosca_dict):
    """Extract nodes that have node_filter from node_templates"""
    nodes_with_filter = {}

    node_templates = tosca_dict.get("service_template", {}).get("node_templates", {})

    for node_name, node_data in node_templates.items():
        if "node_filter" in node_data:
            nodes_with_filter[node_name] = node_data["node_filter"]

    return nodes_with_filter


def tosca_to_ask_dict(tosca_dict):
    """
    Convert TOSCA dict to ask format dict

    Args:
        tosca_dict (dict): Parsed TOSCA YAML data

    Returns:
        dict: Ask format data
    """
    nodes_with_filter = extract_nodes_with_filter(tosca_dict)
    ask_data = {}

    for node_name, node_filter in nodes_with_filter.items():
        ask_entry = {
            "metadata": {
                "created_by": "sardou-tosca-lib",
                "created_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
                "description": f"Generated from node {node_name}",
                "version": "1.0",
            },
            "capabilities": convert_node_filter_to_capabilities(node_filter),
        }

        ask_data[node_name] = ask_entry

    return ask_data

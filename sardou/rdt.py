import copy

from ruamel.yaml import YAML

rdt_yaml = YAML()
rdt_yaml.default_flow_style = False


def _validate_offer_against_cdt(selected_offer: dict, cdt_nodes: dict) -> None:
    for _, ms_data in selected_offer.items():
        if not isinstance(ms_data, dict):
            continue
        for offer_key, offer_data in ms_data.items():
            if not isinstance(offer_data, dict):
                continue
            ids = offer_data.get("ids", {})
            res_id = ids.get("res_id")
            if not res_id:
                continue

            if res_id not in cdt_nodes:
                raise KeyError(
                    f"CDT validation failed: res_id '{res_id}' from offer '{offer_key}' "
                    f"does not match any node in the CDT. "
                    f"The CDT may have been modified since this offer was generated."
                )


def generate_rdt(template, selected_offer: dict, output_path: str = "rdt.yaml") -> dict:
    source = template.raw._to_dict()

    rdt = {}
    rdt["tosca_definitions_version"] = source.get(
        "tosca_definitions_version", "tosca_2_0"
    )
    rdt["description"] = source.get("description", "Resource Definition Template")
    rdt["metadata"] = copy.deepcopy(source.get("metadata", {}))
    rdt["metadata"]["kind"] = "RDT"
    rdt["imports"] = copy.deepcopy(source.get("imports", []))

    try:
        cdt_nodes = source.get("service_template", {})["node_templates"]
    except KeyError:
        raise ValueError("Invalid CDT: 'node_templates' not found")

    _validate_offer_against_cdt(selected_offer, cdt_nodes)

    cdt_node_types = source.get("node_types", {})
    new_node_templates = {}

    for _, ms_data in selected_offer.items():
        if not isinstance(ms_data, dict):
            continue

        for offer_key, offer_data in ms_data.items():
            if not isinstance(offer_data, dict):
                continue

            ids = offer_data.get("ids", {})
            res_id = ids.get("res_id")
            if not res_id:
                continue

            node_key = res_id

            node = copy.deepcopy(cdt_nodes[node_key])

            ms_id = ids.get("ms_id", "")
            node.setdefault("metadata", {})["ms_id"] = ms_id

            offer_props = offer_data.get("properties", {})
            if offer_props:
                node.setdefault("properties", {}).update(offer_props)

            node["count"] = offer_data.get("count", 1)

            new_node_templates[offer_key] = node

    if cdt_node_types:
        rdt["node_types"] = copy.deepcopy(cdt_node_types)

    rdt["service_template"] = {"node_templates": new_node_templates}

    with open(output_path, "w") as f:
        rdt_yaml.width = 4096
        for key, value in rdt.items():
            rdt_yaml.dump({key: value}, f)
            f.write("\n")

    return rdt

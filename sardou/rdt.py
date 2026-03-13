import copy

from ruamel.yaml import YAML

rdt_yaml = YAML()
rdt_yaml.default_flow_style = False


def generate_rdt(template, selected_offer: dict, output_path: str = "rdt.yaml") -> dict:

    rdt = copy.deepcopy(template.raw._to_dict())

    rdt["description"] = "Resource Definition Template generated from selected offer"
    rdt.setdefault("metadata", {}).update(
        {
            "name": "rdt-generated",
            "author": "University of Westminster",
            "version": "0.1",
            "kind": "RDT",
        }
    )

    try:
        cdt_nodes = rdt.get("service_template", {})["node_templates"]
    except KeyError:
        raise ValueError("Invalid RDT: 'node_templates' not found")

    new_node_templates = {}

    for _, ms_data in selected_offer.items():
        if isinstance(ms_data, dict):
            for offer_key, offer_data in ms_data.items():
                if not isinstance(offer_data, dict):
                    continue  # skip strings like 'colocated'
                ids = offer_data.get("ids", {})
                res_id = ids.get("res_id")
                if not res_id:
                    continue
                if res_id not in cdt_nodes:
                    raise KeyError(f"res_id '{res_id}' not found in CDT node_templates")
                node = copy.deepcopy(cdt_nodes[res_id])
                node["count"] = offer_data.get("count", 1)
                if "properties" in offer_data:
                    node["properties"] = {
                        **offer_data["properties"],
                        **node.get("properties", {}),
                    }
                new_node_templates[offer_key] = node

    rdt["service_template"]["node_templates"] = new_node_templates

    with open(output_path, "w") as f:
        rdt_yaml.width = 4096
        rdt_yaml.dump(rdt, f)

    return rdt

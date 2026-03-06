import copy

from ruamel.yaml import YAML

rdt_yaml = YAML()
rdt_yaml.default_flow_style = False

rdt_yaml = YAML()
rdt_yaml.default_flow_style = False

def generate_rdt(template, selected_offer: list, output_path: str = "rdt.yaml") -> dict:
    if isinstance(selected_offer, list):
        selected_offer = selected_offer[0]

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
    for offer_key, offer_data in selected_offer.items():
        res_id = offer_data["res_id"]
        if res_id not in cdt_nodes:
            raise KeyError(f"res_id '{res_id}' not found in CDT node_templates")
        node = copy.deepcopy(cdt_nodes[res_id])
        node["count"] = offer_data.get("count", 1)
        new_node_templates[offer_key] = node

    rdt["service_template"]["node_templates"] = new_node_templates

    with open(output_path, "w") as f:
        rdt_yaml.width = 4096
        rdt_yaml.dump(rdt, f)

    return rdt

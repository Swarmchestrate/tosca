import copy
from ruamel.yaml import YAML

rdt_yaml = YAML()
rdt_yaml.default_flow_style = False


def generate_rdt(template, selected_offer: dict, output_path: str = "rdt.yaml") -> dict:
    source = template.raw._to_dict()

    rdt = {}
    rdt["tosca_definitions_version"] = source.get("tosca_definitions_version", "tosca_2_0")
    rdt["description"] = source.get("description", "Resource Definition Template")
    rdt["metadata"] = copy.deepcopy(source.get("metadata", {}))
    rdt["imports"] = copy.deepcopy(source.get("imports", []))

    try:
        cdt_nodes = source.get("service_template", {})["node_templates"]
    except KeyError:
        raise ValueError("Invalid CDT: 'node_templates' not found")

    new_node_templates = {}

    for ms_name, ms_data in selected_offer.items():
        if not isinstance(ms_data, dict):
            continue

        for offer_key, offer_data in ms_data.items():
            if not isinstance(offer_data, dict):
                continue

            ids = offer_data.get("ids", {})
            res_id = ids.get("res_id")
            if not res_id:
                continue

            # Normalize res_id to flavor/instance_type by stripping provider suffix if present
            provider_suffix = ids.get("provider_id", "")
            if provider_suffix and res_id.endswith(f"-{provider_suffix}"):
                flavor_raw = res_id[: -(len(provider_suffix) + 1)]
            else:
                flavor_raw = res_id.rsplit("-", 1)[0]

            instance_type = flavor_raw.replace("-", ".")

            node_key = None
            for k, node in cdt_nodes.items():
                props = node.get("properties", {})
                flavor = props.get("flavor_name") or props.get("instance_type")
                if flavor == instance_type:
                    node_key = k
                    break

            if not node_key:
                raise KeyError(f"No CDT node matches instance type derived from res_id '{res_id}'")

            node = {"type": cdt_nodes[node_key]["type"]}
            count = offer_data.get("count", 1)
            if count > 1:
                node["count"] = count

            new_node_templates[offer_key] = node

    rdt["service_template"] = {"node_templates": new_node_templates}

    with open(output_path, "w") as f:
        rdt_yaml.width = 4096

        # To preserve the structure of TOSCA template
        for i, (key, value) in enumerate(rdt.items()):
            rdt_yaml.dump({key: value}, f)
            f.write("\n")

    return rdt
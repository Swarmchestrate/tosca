import requests
from ruamel.yaml import YAML

SWCH_IMPORT_URL = "https://raw.githubusercontent.com/Swarmchestrate/tosca/refs/heads/main/profiles/eu.swarmchestrate/profile.yaml"


rdt_yaml = YAML()
rdt_yaml.default_flow_style = False

def fetch_cdt(cdt_path: str) -> dict:
    if cdt_path.startswith("http://") or cdt_path.startswith("https://"):
        response = requests.get(cdt_path)
        response.raise_for_status()
        return rdt_yaml.load(response.text)
    else:
        with open(cdt_path, "r") as f:
            return rdt_yaml.load(f)

def generate_rdt(
    selected_offer: list, cdt_path: str, output_path: str = "rdt.yaml"
) -> dict:
    if isinstance(selected_offer, list):
        selected_offer = selected_offer[0]

    cdt = fetch_cdt(cdt_path)
    cdt_templates = cdt.get("service_template", {}).get("node_templates", {})

    imports = [
        {"namespace": "swch", "url": SWCH_IMPORT_URL},
        {"namespace": "cap-def", "url": cdt_path},
    ]

    node_templates = {}

    for resource_key, resource_data in selected_offer.items():
        instance_type = resource_data.get("instance_type", "")

        try:
            node_templates[resource_key] = dict(cdt_templates[instance_type])
        except KeyError:
            raise KeyError(
                f"Instance_type '{instance_type}' not found in CDT."
            )
        
        node_templates[resource_key]["type"] = f"cap-def:{node_templates[resource_key]['type']}"

    rdt = {
        "tosca_definitions_version": "tosca_2_0",
        "description": "Resource Definition Template generated from selected offer",
        "metadata": {
            "name": "rdt-generated",
            "author": "University of Westminster",
            "version": "0.1",
        },
        "imports": imports,
        "service_template": {"node_templates": node_templates},
    }

    with open(output_path, "w") as f:
        rdt_yaml.width = 4096
        rdt_yaml.dump(rdt, f)

    print(f"[sardou] RDT generated → {output_path}")
    return rdt

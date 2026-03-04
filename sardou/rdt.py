from io import StringIO

import requests
from ruamel.yaml import YAML

SWCH_IMPORT_URL = "https://raw.githubusercontent.com/Swarmchestrate/tosca/refs/heads/main/profiles/eu.swarmchestrate/profile.yaml"

TOSCA_RESERVED_KEYS = {
    "derived_from",
    "properties",
    "capabilities",
    "requirements",
    "description",
    "metadata",
}


def fetch_cdt(cdt_path: str) -> dict:
    rdt_yaml = YAML()
    if cdt_path.startswith("http://") or cdt_path.startswith("https://"):
        response = requests.get(cdt_path)
        response.raise_for_status()
        return rdt_yaml.load(response.text)
    else:
        with open(cdt_path, "r") as f:
            return rdt_yaml.load(f)


def extract_node_type(cdt: dict, instance_type: str) -> tuple[str, str | None]:
    namespace = cdt.get("metadata", {}).get("name", "cap-unknown")
    node_types = cdt.get("node_types", {})

    INSTANCE_KEYS = {"instance_type", "flavor_name"}

    for top_name, top_def in node_types.items():
        if not isinstance(top_def, dict):
            continue

        for node_name, node_def in top_def.items():
            if node_name in TOSCA_RESERVED_KEYS:
                continue
            if not isinstance(node_def, dict):
                continue
            if "derived_from" not in node_def:
                continue

            props = node_def.get("properties", {})
            for key in INSTANCE_KEYS:
                if key in props:
                    prop_val = props[key]
                    default = (
                        prop_val.get("default", "")
                        if isinstance(prop_val, dict)
                        else prop_val
                    )
                    if default == instance_type:
                        return namespace, f"{namespace}:{node_name}"

    return namespace, None


def generate_rdt(
    selected_offer: list, cdt_path: str, output_path: str = "rdt.yaml"
) -> dict:
    if isinstance(selected_offer, list):
        selected_offer = selected_offer[0]

    cdt = fetch_cdt(cdt_path)

    imports = [
        {"namespace": "swch", "url": SWCH_IMPORT_URL},
        {"namespace": "cap-definition", "url": cdt_path},
    ]

    node_templates = {}

    for resource_key, resource_data in selected_offer.items():
        instance_type = resource_data.get("instance_type", "")
        _, node_type = extract_node_type(cdt, instance_type)

        if node_type is None:
            print(
                f"[WARNING] instance_type '{instance_type}' not found in CDT, skipping '{resource_key}'"
            )
            continue

        node_templates[resource_key] = {
            "type": node_type,
        }

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

    # To maintain consistent structure
    rdt_yaml = YAML()
    rdt_yaml.default_flow_style = False
    stream = StringIO()
    rdt_yaml.dump(rdt, stream)
    raw = stream.getvalue()

    TOP_LEVEL_KEYS = ["description:", "metadata:", "imports:", "service_template:"]
    lines = raw.splitlines()
    output_lines = []
    for line in lines:
        if any(line.startswith(key) for key in TOP_LEVEL_KEYS):
            output_lines.append("")
        output_lines.append(line)

    with open(output_path, "w") as f:
        f.write("\n".join(output_lines) + "\n")

    print(f"[sardou] RDT generated → {output_path}")
    return rdt

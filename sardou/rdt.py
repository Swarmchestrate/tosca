from io import StringIO
from ruamel.yaml import YAML
import requests
from typing import Union

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

    def _search(defs: dict, lookup: str) -> str | None:
        for name, definition in defs.items():
            if not isinstance(definition, dict):
                continue

            if "derived_from" in definition:
                props = definition.get("properties", {})
                for key in INSTANCE_KEYS:
                    if key in props:
                        prop_val = props[key]
                        default = (
                            prop_val.get("default", "")
                            if isinstance(prop_val, dict)
                            else prop_val
                        )
                        if default == lookup:
                            return name

                if lookup == name:
                    return name

            for child_name, child_def in definition.items():
                if child_name in TOSCA_RESERVED_KEYS:
                    continue
                if isinstance(child_def, dict):
                    result = _search({child_name: child_def}, lookup)
                    if result:
                        return result
        return None

    match = _search(node_types, instance_type)
    if not match and "-" in instance_type:
        stripped = "-".join(instance_type.split("-")[:-1])
        if stripped != instance_type:
            match = _search(node_types, stripped)
    if match:
        return namespace, f"{namespace}:{match}"
    return namespace, None


def generate_rdt(
    selected_offer: dict, cdt_path: str, output_path: str = "rdt.yaml"
) -> dict:
    cdt = fetch_cdt(cdt_path)
    namespace = cdt.get("metadata", {}).get("name", "cap-unknown")

    imports = [
        {"namespace": "swch", "url": SWCH_IMPORT_URL},
        {"namespace": "cap-definition", "url": cdt_path},
    ]

    node_templates = {}

    for service_key, service_data in selected_offer.items():
        if not isinstance(service_data, dict) or "colocated" in service_data:
            continue

        for resource_key, resource_data in service_data.items():
            instance_type = resource_data["ids"]["res_id"]
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
            "name": "generated-rdt",
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

from pathlib import Path

import jinja2
from ruamel.yaml import YAML

yaml = YAML(typ="safe")

jinja_loader = jinja2.FileSystemLoader(searchpath="tools/jinja_templates")
jinja_env = jinja2.Environment(loader=jinja_loader)
template = jinja_env.get_template("docspage.md.j2")

DOCS_LOC = Path("docs/")

SOURCES = {
    "profile": "profiles/eu.swarmchestrate/profile.yaml",
    "capacity": "profiles/eu.swarmchestrate/capacity.yaml",
    "monitoring": "profiles/eu.swarmchestrate/monitoring.yaml",
}

# --- Load YAML sources ---

data = {}
for key, path in SOURCES.items():
    with open(path) as f:
        data[key] = yaml.load(f)


# --- Extraction helpers ---


def extract_fields(properties):
    """Convert a YAML properties dict to template `fields` format."""
    fields = {}
    for name, value in properties.items():
        entry_schema = value.get("entry_schema", {})
        fields[name] = {
            "required": value.get("required", False),
            "type": value.get("type", ""),
            "schema": (
                entry_schema
                if isinstance(entry_schema, str)
                else entry_schema.get("type", "")
            ),
            "description": value.get("description", "No description available"),
        }
    return fields


def extract_types(types_dict):
    """Convert a data_types / policy_types dict to template `types` format."""
    types = {}
    for name, value in types_dict.items():
        types[name] = {
            "description": value.get("description", "No description available"),
            "fields": [
                {
                    "name": prop_name,
                    "required": prop_value.get("required", False),
                    "type": prop_value.get("type", ""),
                    "description": prop_value.get(
                        "description", "No description available"
                    ),
                }
                for prop_name, prop_value in value.get("properties", {}).items()
            ],
        }
    return types


def extract_capacity_fields(node_types_dict, capability_types_dict):
    """Convert node_types to fields format with grouped capabilities.

    Each node type becomes a top-level field.  Its capabilities are grouped
    so that e.g. ``locality`` appears as a heading with ``continent``,
    ``city``, etc. nested underneath (instead of flat ``locality.continent``).
    """
    fields = {}
    for node_name, node_value in node_types_dict.items():
        # Node-level properties (e.g. ip, image_id)
        node_props = [
            {
                "name": prop_name,
                "required": prop_value.get("required", False),
                "type": prop_value.get("type", ""),
                "description": prop_value.get(
                    "description", "No description available"
                ),
            }
            for prop_name, prop_value in node_value.get("properties", {}).items()
        ]

        # Capabilities with their properties grouped
        capabilities = []
        for cap_name, cap_value in node_value.get("capabilities", {}).items():
            props = cap_value.get("properties", {})
            if not props:
                cap_type = cap_value.get("type", "")
                if cap_type in capability_types_dict:
                    props = capability_types_dict[cap_type].get("properties", {})

            cap_fields = [
                {
                    "name": prop_name,
                    "required": prop_value.get("required", False),
                    "type": prop_value.get("type", ""),
                    "default": prop_value.get("default", ""),
                    "description": prop_value.get(
                        "description", "No description available"
                    ),
                }
                for prop_name, prop_value in props.items()
            ]
            if cap_fields:
                cap_desc = cap_value.get("description", "")
                capabilities.append({"name": cap_name, "description": cap_desc, "fields": cap_fields})

        fields[node_name] = {
            "description": node_value.get("description", "No description available"),
            "capabilities": capabilities,
            "props": node_props,
        }
    return fields


# --- Page definitions ---

pages = [
    {
        "name": "Policy",
        "fields": {
            name: {"description": value.get("description", "No description available")}
            for name, value in data["profile"].get("policy_types", {}).items()
            if name.startswith("QoS.")
        },
    },
    {
        "name": "Microservice",
        "fields": extract_fields(
            data["profile"]["node_types"]["Microservice"]["properties"]
        ),
        "types": extract_types(data["profile"].get("data_types", {})),
        "show_primitives": True,
    },
    {
        "name": "Capacity",
        "fields": extract_capacity_fields(
            data["capacity"].get("node_types", {}),
            data["capacity"].get("capability_types", {}),
        ),
    },
    {
        "name": "Monitoring",
        "types": extract_types(data["monitoring"].get("data_types", {})),
    },
]


# --- Render and write ---

for page in pages:
    page.setdefault("fields", {})
    page.setdefault("types", {})
    page.setdefault("show_primitives", False)

    rendered = template.render(**page)
    file_name = page["name"].lower().replace(" ", "_")

    write_path = DOCS_LOC / f"{file_name}.md"
    with open(write_path, "w") as f:
        f.write(rendered)

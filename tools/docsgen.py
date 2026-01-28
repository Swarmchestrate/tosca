from pathlib import Path

import jinja2
from ruamel.yaml import YAML

yaml = YAML(typ="safe")

jinja_loader = jinja2.FileSystemLoader(searchpath="tools/jinja_templates")
jinja_env = jinja2.Environment(loader=jinja_loader)
template = jinja_env.get_template("docspage.md.j2")

PROFILE_URL = "profiles/eu.swarmchestrate/profile.yaml"
CAPACITY_URL = "profiles/eu.swarmchestrate/capacity.yaml"

DOCS_LOC = Path("docs/")

with open(PROFILE_URL) as f:
    profile = yaml.load(f)

with open(CAPACITY_URL) as f:
    capacity = yaml.load(f)

fields = {}
pages_to_write = []

###
## Policy Page
###

PAGE_NAME = "Policy"

for name, value in profile["policy_types"].items():
    if not name.startswith("QoS."):
        continue
    info = {
        "description": value.get("description", "No description available")
    }
    fields[name] = info

pages_to_write.append(
    {
        "name": PAGE_NAME,
        "fields": fields
    }
)
fields = {}
types = {}

###
## Microservice Page
###

PAGE_NAME = "Microservice"

for name, value in profile["node_types"]["Microservice"]["properties"].items():
    entry_schema = value.get("entry_schema", {})
    info = {
        "required": value.get("required", False),
        "type": value.get("type", ""),
        "schema": entry_schema if isinstance(entry_schema, str) else entry_schema.get("type", ""),
        "description": value.get("description", "No description available")
    }
    fields[name] = info

for name, value in profile["data_types"].items():
    info = {
        "description": value.get("description", "No description available"),
        "fields": []
    }
    types[name] = info
    for k, v in value.get("properties", {}).items():
        field = {
            "name": k,
            "required": v.get("required", False),
            "type": v.get("type", ""),
            "description": v.get("description", "No description available")
        }
        info["fields"].append(field)
    types[name] = info

pages_to_write.append(
    {
        "name": PAGE_NAME,
        "fields": fields,
        "types": types
    }
)

###
## Capacity Page
###

## TODO: Implement capacity page generation




###
## Monitoring Page
###


## TODO: Implemenent monitoring page generation
##      - RawMetric
##      - CompositeMetric
##      - SLO



###
## Render and write pages
###

for page_data in pages_to_write:
    rendered = template.render(**page_data)
    file_name = page_data["name"].lower().replace(" ", "_")

    write_path = (
        DOCS_LOC / f"{file_name}.md"
    )
    with open(write_path, "w") as file:
        file.write(rendered)


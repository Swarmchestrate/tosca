import subprocess
import sys
from pathlib import Path
from tempfile import NamedTemporaryFile

from ruamel.yaml import YAML

PUCCINI_CMD = "/usr/bin/puccini-tosca"
PUCCINI_FLAGS = ["-x", "data_types.string.permissive"]

# Read and update YAML using ruamel.yaml
yaml = YAML()


def prevalidate(input_data):
    if isinstance(input_data, Path):
        if not input_data.exists():
            print(f"File does not exist: {input_data}", file=sys.stderr)
            return False
        try:
            with input_data.open("r") as f:
                data = yaml.load(f)
        except Exception as e:
            print(f"Error reading YAML file {input_data}: {e}", file=sys.stderr)
            return False
    elif isinstance(input_data, dict):
        data = input_data
    else:
        try:
            data = yaml.load(input_data)
        except Exception as e:
            print(f"Error parsing YAML content: {e}", file=sys.stderr)
            return False
    
    if not data:
        print("No YAML content found", file=sys.stderr)
        return False
    
    imports = data.get("imports", [])
    template = data.get("service_template", {})

    for imp in imports:
        if isinstance(imp, dict) and "profile" in imp:
            imp["url"] = imp.pop("profile")

    for _, node in template.get("node_templates", {}).items():
        node.pop("node_filter", None)

    return data


def classify_template(template) -> str:
    """Classify a parsed template as 'sat', 'cdt', 'rdt', 'tdt'."""

    valid_kinds = ["sat", "cdt", "rdt", "tdt"]
    kind = template._to_dict()["metadata"].get("kind", "").lower()
    if kind in valid_kinds:
        return kind

    nodes = template.nodeTemplates._to_dict()
    if not nodes:
        return "tdt"

    has_capacity = any(
        any(k.endswith("::Capacity") for k in node.get("types", {}))
        for node in nodes.values()
    )
    has_microservice = any(
        any(k.endswith("::Microservice") for k in node.get("types", {}))
        for node in nodes.values()
    )

    if has_capacity and has_microservice:
        raise ValueError(
            "Invalid template: cannot have both Capacity and Microservice definitions"
        )

    if has_capacity:
        return "cdt"

    return "sat"


def validate_template(input_data) -> bool:
    # will run the puccini-tosca parse <with flag>
    yaml_data = prevalidate(input_data)
    
    if isinstance(input_data, Path):
        file_label = str(input_data)
    elif isinstance(input_data, dict):
        file_label = "(dict content)"
    else:
        file_label = "(string content)"

    # open a temp file
    with NamedTemporaryFile() as temp_file:
        yaml.dump(yaml_data, temp_file)

        try:
            result = subprocess.run(
                [PUCCINI_CMD, "parse", str(temp_file.name)] + PUCCINI_FLAGS,
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                print(f"Processed successfully: {file_label} \n")
                return result
            else:
                print(f"Failed to process: {file_label} \n", file=sys.stderr)
                print("==== Error Output ====", file=sys.stderr)
                print(result.stderr.strip() or result.stdout.strip(), file=sys.stderr)
                print("======================", file=sys.stderr)
                return None

        except FileNotFoundError:
            print(
                f"Puccini not found at {PUCCINI_CMD}. Please install it first.",
                file=sys.stderr,
            )
            sys.exit(1)
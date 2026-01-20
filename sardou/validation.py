import subprocess
import sys
from pathlib import Path
from tempfile import NamedTemporaryFile

from ruamel.yaml import YAML

PUCCINI_CMD = "/usr/bin/puccini-tosca"
PUCCINI_FLAGS = ["-x", "data_types.string.permissive"]

# Read and update YAML using ruamel.yaml
yaml = YAML()


def prevalidate(file_path: Path) -> bool:
    # Check if file exists
    if not file_path.exists():
        print(f"File does not exist: {file_path}")
        return False

    try:
        with file_path.open("r") as f:
            data = yaml.load(f)
    except Exception as e:
        print(f"Error reading YAML file {file_path}: {e}")
        return False
    if not data:
        print("No YAML content found")
        return False
    imports = data.get("imports", [])
    nodes = data["service_template"].get("node_templates", {})

    for imp in imports:
        if isinstance(imp, dict) and "profile" in imp:
            imp["url"] = imp.pop("profile")

    for _, node in nodes.items():
        node.pop("node_filter", None)

    return data


def validate_template(file_path: Path) -> bool:
    # will run the puccini-tosca parse <with flag>
    yaml_data = prevalidate(file_path)

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
                print(f"Processed successfully: {file_path} \n")
                return result
            else:
                print(f"Failed to process: {file_path} \n")
                print("==== Error Output ====")
                print(result.stderr.strip() or result.stdout.strip())
                print("======================")
                return None

        except FileNotFoundError:
            print(f"Puccini not found at {PUCCINI_CMD}. Please install it first.")
            sys.exit(1)

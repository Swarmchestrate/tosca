from ruamel.yaml import YAML
from sardou.manifestGenerator import get_kubernetes_manifest
from pathlib import Path
import sys

yaml_parser = YAML()
yaml_parser.default_flow_style = False

TOSCA_FILE = "templates/fuelics-V1.yaml"
OUTPUT_FILE = "output.yaml"
IMAGE_PULL_SECRET = "regcred"

path = Path(TOSCA_FILE)
if not path.exists():
    sys.exit(f"Error: TOSCA file '{TOSCA_FILE}' not found.")

try:
    with open(path, "r") as f:
        tosca_yaml = f.read()
    manifests = get_kubernetes_manifest(tosca_yaml, image_pull_secret=IMAGE_PULL_SECRET)
    if not manifests:
        sys.exit("Warning: No Kubernetes manifests generated.")
    with open(OUTPUT_FILE, "w") as f:
        yaml_parser.dump_all(manifests, f)
except Exception as e:
    sys.exit(f"Error: {e}")

print(f"✅ Kubernetes manifests written to '{OUTPUT_FILE}' ({len(manifests)} items)")

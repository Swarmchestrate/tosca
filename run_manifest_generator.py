import sys
from pathlib import Path

from ruamel.yaml import YAML

from sardou.manifestGenerator import get_kubernetes_manifest

yaml_parser = YAML()
yaml_parser.default_flow_style = False

TOSCA_FILE = "templates/tosca-filename.yaml"
OUTPUT_FILE = "manifest-out.yaml"
IMAGE_PULL_SECRET = "my-registry-secret"

path = Path(TOSCA_FILE)
if not path.exists():
    sys.exit(f"Error: TOSCA file '{TOSCA_FILE}' not found.")

try:
    manifests = get_kubernetes_manifest(TOSCA_FILE, image_pull_secret=IMAGE_PULL_SECRET)

    if not manifests:
        sys.exit("Warning: No Kubernetes manifests generated.")

    with open(OUTPUT_FILE, "w") as f:
        yaml_parser.dump_all(manifests, f)

    print(f"✅ Kubernetes manifests written to '{OUTPUT_FILE}' ({len(manifests)} items)")

except Exception as e:
    sys.exit(f"Error: {e}")


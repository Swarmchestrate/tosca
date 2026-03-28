import logging
import subprocess
from enum import Enum
from functools import wraps
from pathlib import Path
from tempfile import NamedTemporaryFile

from ruamel.yaml import YAML

from .cache import resolve_imports

logger = logging.getLogger(__name__)


COLOCATION_SUFFIX = "Scheduling.Colocation"
RECONFIGURATION_SUFFIX = "Reconfiguration"


class TemplateKind(Enum):
    SAT = "sat"
    CDT = "cdt"
    RDT = "rdt"
    TDT = "tdt"


def requires_kind(kind):
    def decorator(fn):
        @wraps(fn)
        def wrapper(self, *args, **kwargs):
            if self.kind != kind:
                raise TypeError(f"{fn.__name__}() requires a {kind.value.upper()}")
            return fn(self, *args, **kwargs)

        return wrapper

    return decorator


PUCCINI_CMD = "/usr/bin/puccini-tosca"
PUCCINI_FLAGS = ["-x", "data_types.string.permissive"]

# Read and update YAML using ruamel.yaml
yaml = YAML()
yaml.width = 4096


def _strip_blank_lines(text):
    """Strip whitespace from otherwise blank lines so ruamel preserves them."""
    return "\n".join("" if line.isspace() else line for line in text.split("\n"))


def prevalidate(input_data):
    if isinstance(input_data, Path):
        if not input_data.exists():
            logger.error(f"File does not exist: {input_data}")
            return False
        try:
            text = input_data.read_text()
            data = yaml.load(_strip_blank_lines(text))
        except Exception as e:
            logger.error(f"Error reading YAML file {input_data}: {e}")
            return False
    elif isinstance(input_data, dict):
        data = input_data
    else:
        try:
            if isinstance(input_data, str):
                input_data = _strip_blank_lines(input_data)
            data = yaml.load(input_data)
        except Exception as e:
            logger.error(f"Error parsing YAML content: {e}")
            return False

    if not data:
        logger.error("No YAML content found")
        return False

    imports = data.get("imports", [])
    template = data.get("service_template", {})

    for imp in imports:
        if isinstance(imp, dict) and "profile" in imp:
            imp["url"] = imp.pop("profile")

    resolve_imports(data)

    for _, node in template.get("node_templates", {}).items():
        node.pop("node_filter", None)

    return data


def classify_template(template) -> TemplateKind:
    """Classify a parsed template as SAT, CDT, RDT, or TDT."""

    kind_str = template._to_dict()["metadata"].get("kind", "").lower()
    try:
        return TemplateKind(kind_str)
    except ValueError:
        pass

    nodes = template.nodeTemplates._to_dict()
    if not nodes:
        return TemplateKind.TDT

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
        return TemplateKind.CDT

    return TemplateKind.SAT


def post_validate(tosca_dict) -> bool:
    """Perform any post validation steps."""
    return validate_reconfiguration(tosca_dict)


def validate_reconfiguration(tosca_dict) -> bool:
    """Validate that colocated microservices are not split across
    different Reconfiguration policies."""
    policies = tosca_dict.get("service_template", {}).get("policies", [])

    colocation_groups = []
    reconfig_targets = {}

    for policy in policies:
        for name, data in policy.items():
            ptype = data.get("type", "")
            targets = data.get("targets", [])
            if ptype.endswith(COLOCATION_SUFFIX):
                colocation_groups.append(set(targets))
            elif ptype.endswith(RECONFIGURATION_SUFFIX):
                reconfig_targets[name] = set(targets)

    for group in colocation_groups:
        matching_policies = [
            name for name, targets in reconfig_targets.items() if targets & group
        ]
        if len(matching_policies) > 1:
            raise ValueError(
                f"Colocated microservices {sorted(group)} are targeted by "
                f"different Reconfiguration policies: {matching_policies}"
            )

    return True


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
                logger.info(f"Processed successfully: {file_label}")
                return result
            else:
                logger.error(f"Failed to process: {file_label}")
                logger.error(result.stderr.strip() or result.stdout.strip())
                return None

        except FileNotFoundError:
            raise FileNotFoundError(
                f"Puccini not found at {PUCCINI_CMD}. Please install it first."
            )

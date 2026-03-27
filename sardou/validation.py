import logging
import subprocess
from enum import Enum
from functools import wraps
from pathlib import Path
from tempfile import NamedTemporaryFile

from ruamel.yaml import YAML

logger = logging.getLogger(__name__)


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


def prevalidate(input_data):
    if isinstance(input_data, Path):
        if not input_data.exists():
            logger.error(f"File does not exist: {input_data}")
            return False
        try:
            with input_data.open("r") as f:
                data = yaml.load(f)
        except Exception as e:
            logger.error(f"Error reading YAML file {input_data}: {e}")
            return False
    elif isinstance(input_data, dict):
        data = input_data
    else:
        try:
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

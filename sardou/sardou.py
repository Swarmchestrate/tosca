import json
from pathlib import Path

from ruamel.yaml import YAML

from .capacities import extract_capacities
from .cluster import get_cluster as _get_cluster
from .rdt import generate_rdt as _generate_rdt
from .requirements import tosca_to_ask_dict
from .validation import classify_template, validate_template

yaml = YAML(typ="safe")


class DotDict:
    def __init__(self, **entries):
        for k, v in entries.items():
            if isinstance(v, dict):
                v = DotDict(**v)
            elif isinstance(v, list):
                v = [DotDict(**i) if isinstance(i, dict) else i for i in v]
            setattr(self, k, v)

    def __getitem__(self, key):
        return getattr(self, key)

    def __setitem__(self, key, value):
        setattr(self, key, value)

    def __delitem__(self, key):
        delattr(self, key)

    def __contains__(self, key):
        return hasattr(self, key)

    def __repr__(self):
        return repr(self._to_dict())

    def _to_dict(self):
        result = {}
        for key, value in self.__dict__.items():
            if isinstance(value, DotDict):
                result[key] = value._to_dict()
            elif isinstance(value, list):
                result[key] = [
                    v._to_dict() if isinstance(v, DotDict) else v for v in value
                ]
            else:
                result[key] = value
        return result

    def _to_json(self, indent=None, **kwargs):
        return json.dumps(self._to_dict(), indent=indent, **kwargs)


class Sardou(DotDict):
    def __init__(self, path=None, content=None):
        if path is None and content is None:
            raise ValueError("Either 'path' or 'content' must be provided")

        if path is not None and content is not None:
            raise ValueError("Cannot provide both 'path' and 'content'")

        if path is not None:
            # File-based initialization
            path = Path(path)
            if not path.exists():
                raise FileNotFoundError(f"File does not exist: {path}")
            self.path = path
            source = path
        else:
            self.path = None
            source = content

        template = validate_template(source)
        if not template:
            label = str(path) if path else "provided content"
            raise ValueError(f"Validation failed for: {label}")

        resolved = yaml.load(template.stdout)
        super().__init__(**resolved)

        if path is not None:
            with path.open("r") as f:
                raw = yaml.load(f)
        elif isinstance(content, dict):
            raw = content
        else:
            raw = yaml.load(content)

        self.kind = classify_template(self)
        self.raw = DotDict(**raw)

    def get_requirements(self):
        return tosca_to_ask_dict(self.raw._to_dict())

    def get_qos(self, indent=None, **kwargs):
        if self.kind != "sat":
            raise TypeError("Can only get QoS goals from a SAT")
        if not hasattr(self.raw.service_template, "policies"):
            return []
        policies = self.raw.service_template.policies
        return [p._to_dict() if isinstance(p, DotDict) else p for p in policies]

    def get_capacities(self):
        if self.kind == "sat":
            raise TypeError("Cannot get capacity info from a SAT")
        nodes = self.nodeTemplates._to_dict()
        return extract_capacities(nodes)

    def generate_rdt(self, selected_offer, output_path="rdt.yaml"):
        return _generate_rdt(self, selected_offer, output_path=output_path)

    def get_cluster(self, resource_suffix=None):
        return _get_cluster(self, resource_suffix=resource_suffix)
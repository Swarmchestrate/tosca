from pathlib import Path
import json
from ruamel.yaml import YAML

from .validation import validate_template
from .requirements import tosca_to_ask_dict

yaml = YAML(typ='safe')

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
    def __init__(self, path):
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"File does not exist: {path}")
        template = validate_template(path)
        if not template:
            raise ValueError(f"Validation failed for: {path}")

        resolved = yaml.load(template.stdout)
        super().__init__(**resolved)

        with path.open('r') as f:
            raw = yaml.load(f)
        self.raw = DotDict(**raw)

    def get_requirements(self):
        return tosca_to_ask_dict(self.raw)
    
    def get_qos(self, indent=None, **kwargs):
        if not hasattr(self.raw.service_template, 'policies'):
            return []
        policies = self.raw.service_template.policies
        return [p._to_dict() if isinstance(p, DotDict) else p for p in policies]
    
    def get_cluster(self):
        
        try:
            node_templates = self.service_template["node_templates"]
        except (AttributeError, KeyError):
            raise ValueError("No 'service_template.node_templates' found in the YAML file.")
        
        cluster = {}
        for node_name, node_data in node_templates.items():
            node_info = {}
            for k, v in node_data.items():
                # relevant node parameters
                if k in ("type", "directives", "properties", "requirements", "capabilities"):
                    node_info[k] = v
            cluster[node_name] = node_info

        return cluster
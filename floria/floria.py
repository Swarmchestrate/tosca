from pathlib import Path
import json
from ruamel.yaml import YAML
from .validation import validate_template
from .requirements import tosca_to_ask_dict

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

class Floria(DotDict):
    def __init__(self, path):
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"File does not exist: {path}")
        if not validate_template(path):
            raise ValueError(f"Validation failed for: {path}")
        yaml = YAML(typ='safe')
        with path.open('r') as f:
            data = yaml.load(f)
        super().__init__(**data)

    def get_requirements(self):
        return tosca_to_ask_dict(self._to_dict())
    
    def get_qos(self, indent=None, **kwargs):
        policies = self.service_template.policies
        return [p._to_dict() if isinstance(p, DotDict) else p for p in policies]
        
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
  
        def extract_values(obj):
            if isinstance(obj, dict):
                if "$primitive" in obj:
                    return obj["$primitive"]
                elif "$list" in obj:
                    return [extract_values(i) for i in obj["$list"]]
                elif "$map" in obj:
                    return {
                        i["$key"]["$primitive"]: extract_values(i)
                        for i in obj["$map"]
                    }
                else:
                    return {k: extract_values(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [extract_values(i) for i in obj]
            else:
                return obj

        resources = {}

        for name, node in self.nodeTemplates._to_dict().items():
            # If the node is a resource
            types = node.get("types", {})
            is_resource = any(
                t.get("parent", "") == "eu.swarmchestrate:0.1::Resource"
                or k.endswith("::Resource")
                for k, t in types.items()
            )
            if not is_resource:
                continue

            resource_data = {}

            # Core properties
            if "properties" in node:
                for k, v in node["properties"].items():
                    resource_data[k] = extract_values(v)

            # Capabilities as nested objects
            if "capabilities" in node:
                caps_data = {}
                for cname, cap in node["capabilities"].items():
                    if "properties" in cap:
                        caps_data[cname] = {
                            k: extract_values(v)
                            for k, v in cap["properties"].items()
                        }
                if caps_data:
                    resource_data["capabilities"] = caps_data

            resources[name] = resource_data

        return resources
import os
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
        return tosca_to_ask_dict(self.raw._to_dict())
    
    def get_qos(self, indent=None, **kwargs):
        if not hasattr(self.raw.service_template, 'policies'):
            return []
        policies = self.raw.service_template.policies
        return [p._to_dict() if isinstance(p, DotDict) else p for p in policies]

    def get_cluster(self, resource_suffix=None):

        ALIASES = {
            # AWS
            "image_id": "ami",
            "key_name": "ssh_key",
            "instance_type": "instance_type",
            "region_name": "region",
            "security_group_ids": "security_group_id",
            "provider": "cloud",

            #OS
            "openstack_image_id": "openstack_image_id",
            "openstack_flavor_id": "openstack_flavor_id",
            "volume_size": "volume_size",
            "network_id": "network_id",
            "floating_ip_pool": "floating_ip_pool",

            #Edge
            "edge_device_ip": "edge_device_ip"
        }

        DIRECT_FIELDS = set(ALIASES.values())

        resource_suffix = (
            resource_suffix
            or os.getenv("TOSCA_RESOURCE_SUFFIX")
            or "::Resource"
        )

        resources = {}

        for name, node in self.nodeTemplates._to_dict().items():

            if "properties" not in node or not isinstance(node["properties"], dict):
                continue

            types = node.get("types", {})
            is_resource = any(
                t.get("parent", "").endswith(resource_suffix) or
                k.endswith(resource_suffix)
                for k, t in types.items()
            )
            if not is_resource:
                continue

            extracted = {}

            # copy raw values exactly as-is (preserve $primitive/$list/$meta)
            for key, val in node["properties"].items():
                final_key = ALIASES.get(key, key)

                if final_key in DIRECT_FIELDS or key in ALIASES:
                    extracted[final_key] = val    # ← KEEP RAW STRUCTURE

            # default values from type definitions (as raw structures)
            for type_name, type_def in types.items():
                type_props = type_def.get("properties", {})
                for key, prop_def in type_props.items():
                    final_key = ALIASES.get(key, key)

                    if final_key in extracted:
                        continue

                    if isinstance(prop_def, dict) and "default" in prop_def:
                        extracted[final_key] = {
                            "$primitive": prop_def["default"]
                        }

            resources[name] = extracted

        return json.dumps(resources, indent=2)

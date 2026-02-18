import os
from pathlib import Path
import json
import copy
from ruamel.yaml import YAML

from .capacities import extract_capacities 
from .validation import check_is_sat, validate_template
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

        self.path = path

        
        template = validate_template(path)
        if not template:
            raise ValueError(f"Validation failed for: {path}")
 
        resolved = yaml.load(template.stdout)
        super().__init__(**resolved)

        self.isSAT = check_is_sat(self)
 
        with path.open('r') as f:
            raw = yaml.load(f)
        self.raw = DotDict(**raw)

        self.auto_replace_substitutes()

        
    # Generate concrete nodes
    def _find_capacity_file(self):
        from pathlib import Path

        project_root = Path(self.path).resolve().parent.parent
        cap_dir = project_root / "examples" / "capacities"

        if not cap_dir.exists():
            raise FileNotFoundError(f"Capacity directory not found: {cap_dir}")

        files = list(cap_dir.glob("*.y*ml"))
        if not files:
            raise FileNotFoundError(f"No capacity YAML files found in {cap_dir}")

        return files[0]
    
    def auto_replace_substitutes(self):
        from ruamel.yaml import YAML
        from pathlib import Path

        rt_yaml = YAML(typ="rt")
        rt_yaml.preserve_quotes = True
        rt_yaml.default_flow_style = False

        with Path(self.path).open() as f:
            target_yaml = rt_yaml.load(f)

        node_templates = target_yaml["service_template"]["node_templates"]

        # find swarm nodes for substitution
        placeholders = [
            name for name, node in node_templates.items()
            if "directives" in node and "substitute" in node["directives"]
        ]

        if not placeholders:
            return

        capacity_path = self._find_capacity_file()

        if placeholders:
            capacity_path = self._find_capacity_file()
            self.replace_with_concrete_nodes(
                target_yaml_path=self.path,
                capacity_path=capacity_path,
                save_path=self.path
            )

        
        with Path(self.path).open() as f:
            new_raw = yaml.load(f)
        self.raw = DotDict(**new_raw)


    def replace_with_concrete_nodes(self, target_yaml_path, capacity_path, save_path=None):
        from pathlib import Path
        from ruamel.yaml import YAML

        target_yaml_path = Path(target_yaml_path)
        capacity_path = Path(capacity_path)

        if not target_yaml_path.exists():
            raise FileNotFoundError(f"Target YAML does not exist: {target_yaml_path}")
        if not capacity_path.exists():
            raise FileNotFoundError(f"Capacity definition file does not exist: {capacity_path}")

        # preserve the original TOSCA format
        rt_yaml = YAML(typ="rt")        
        rt_yaml.preserve_quotes = True   
        rt_yaml.default_flow_style = False  

        target_yaml = rt_yaml.load(target_yaml_path)
        capacity_yaml = rt_yaml.load(capacity_path)

        node_templates = target_yaml["service_template"]["node_templates"]
        capacity_nodes = capacity_yaml["service_template"]["node_templates"]

        if "swarm" not in node_templates:
            raise KeyError("No 'swarm' node found in target YAML.")

        # preserve the insertion index
        keys = list(node_templates.keys())
        swarm_index = keys.index("swarm")

        del node_templates["swarm"]

        # insert the concrete nodes 
        for name, node in capacity_nodes.items():
            node_templates.insert(swarm_index, name, node)
            swarm_index += 1

        if save_path:
            with Path(save_path).open("w") as f:
                rt_yaml.dump(target_yaml, f)
            return str(save_path)

        return target_yaml
 
    def get_requirements(self):
        return tosca_to_ask_dict(self.raw._to_dict())
    
    def get_qos(self, indent=None, **kwargs):
        if not hasattr(self.raw.service_template, 'policies'):
            return []
        policies = self.raw.service_template.policies
        return [p._to_dict() if isinstance(p, DotDict) else p for p in policies]
    
    def get_capacities(self):
        if self.isSAT:
            raise TypeError("Cannot get capacity info from a SAT")
        nodes = self.nodeTemplates._to_dict()
        return extract_capacities(nodes)

    def get_cluster(self, resource_suffix=None):
 
        # Cloud alias
        AWS_ALIASES = {
            "provider": "cloud",
            "instance_type": "instance_type",
            "ssh_user": "ssh_user",
            "key_name": "ssh_key",
            "image_id": "ami",
            "security_group_id": "security_group_id",
            "custom_ingress_ports": "custom_ingress_ports",
            "custom_egress_ports": "custom_egress_ports",
        }
 
        OPENSTACK_ALIASES = {
            "provider": "cloud",
            "image_id": "openstack_image_id",
            "instance_type": "openstack_flavor_id",
            "ssh_user": "ssh_user",
            "key_name": "ssh_key",
            "use_block_device": "use_block_device",
            "volume_size": "volume_size",
            "network_id": "network_id",
            "floating_ip_pool": "floating_ip_pool",
            "security_group_id": "security_group_id",
            "custom_ingress_ports": "custom_ingress_ports",
            "custom_egress_ports": "custom_egress_ports",
        }
 
        EDGE_ALIASES = {
            "provider": "cloud",
            "ssh_user": "ssh_user",
            "key_name": "ssh_key",
            "ssh_auth_method": "ssh_auth_method",
            "edge_device_ip": "edge_device_ip",
        }
 
        # Application alias
        APP_ALIASES = {
            "ports": "ports",
        }
 
        def flatten(val):
            if isinstance(val, dict):
                if "$primitive" in val:
                    return val["$primitive"]
                if "$list" in val:
                    return [flatten(v) for v in val["$list"]]
                if "$map" in val:
                    out = {}
                    for pair in val["$map"]:
                        key = flatten(pair.get("$key"))
                        value = flatten(pair)
                        out[key] = value
                    return out
                return {k: flatten(v) for k, v in val.items()}
            return val
 
        resource_suffix = (
            resource_suffix
            or os.getenv("TOSCA_RESOURCE_SUFFIX")
            or "::Resource"
        )
 
        resources = {}
 
        for name, node in self.nodeTemplates._to_dict().items():
            types = node.get("types", {})

            # Warning for abstract resource
            if "swch:AbstractResource" in types:
                print(
                    f"WARNING: Abstract resource '{name}' detected. "
                    f"Please provide concrete resource."
                )
 
            # Detect resource nodes
            is_resource = any(
                t.get("parent", "").endswith(resource_suffix) or k.endswith(resource_suffix)
                for k, t in types.items()
            )
 
            # Detect Application nodes
            is_application = any("Application" in k for k in types.keys())
 
            if not (is_resource or is_application):
                continue
 
            extracted = {}
 
            # Extract node properties
            def extract_properties(prop_dict):
                for k, v in prop_dict.items():
                    extracted[k] = flatten(v)
 
            extract_properties(node.get("properties", {}))
     
            # Extract capability properties
            def extract_cap_props(cap_dict):
                for cap in cap_dict.values():
                    extract_properties(cap.get("properties", {}))
                    if "capabilities" in cap:
                        extract_cap_props(cap["capabilities"])
 
            extract_cap_props(node.get("capabilities", {}))
 
            # Type-level defaults
            for type_def in types.values():
                for k, prop_def in type_def.get("properties", {}).items():
                    if k not in extracted and isinstance(prop_def, dict) and "default" in prop_def:
                        extracted[k] = flatten({"$primitive": prop_def["default"]})
 
                def extract_type_cap_defaults(cap_dict):
                    for cap in cap_dict.values():
                        for k, prop_def in cap.get("properties", {}).items():
                            if k not in extracted and isinstance(prop_def, dict) and "default" in prop_def:
                                extracted[k] = flatten({"$primitive": prop_def["default"]})
                        if "capabilities" in cap:
                            extract_type_cap_defaults(cap["capabilities"])
 
                for type_cap in type_def.get("capabilities", {}).values():
                    extract_type_cap_defaults(type_cap.get("capabilities", {}))
 
            # Select alias map
            provider = str(extracted.get("provider", "")).lower()
 
            if provider in ["aws", "amazon"]:
                ALIASES = AWS_ALIASES
            elif provider == "openstack":
                ALIASES = OPENSTACK_ALIASES
            elif provider == "edge":
                ALIASES = EDGE_ALIASES
            elif is_application:
                ALIASES = APP_ALIASES
            else:
                ALIASES = {}
 
            DIRECT = set(ALIASES.values())
 
            # Apply alias mapping
            final_extracted = {}
            for k, v in extracted.items():
                final_key = ALIASES.get(k, k)
                if final_key in DIRECT or k in ALIASES:
                    final_extracted[final_key] = v
            
            if is_application:
                final_extracted["_is_application"] = True
 
            resources[name] = final_extracted
 
        # Pass nodeport into custom ingress ports
        # collect all application ports
        app_ports = []
        for props in resources.values():
            if "ports" in props:
                app_ports.extend(props["ports"])
 
        # inject into each resource with custom_ingress_ports
        for props in resources.values():
            if "custom_ingress_ports" not in props:
                continue
 
            merged = []
 
            # keep original ingress ports
            orig = props["custom_ingress_ports"]
            if isinstance(orig, dict):
                merged.append(orig)
            elif isinstance(orig, list):
                merged.extend(orig)
 
            # add port + nodePort rules for each application port entry
            for p in app_ports:
                if "port" in p:
                    merged.append({
                        "from": str(p["port"]),
                        "to": str(p["port"]),
                        "protocol": "tcp",
                        "source": "0.0.0.0/0"
                    })
                if "nodePort" in p:
                    merged.append({
                        "from": str(p["nodePort"]),
                        "to": str(p["nodePort"]),
                        "protocol": "tcp",
                        "source": "0.0.0.0/0"
                    })
 
            props["custom_ingress_ports"] = merged
 
        # Remove application nodes
        apps_to_remove = []
 
        for name, props in resources.items():
            if props.get("_is_application", False):
                apps_to_remove.append(name)
 
        for app in apps_to_remove:
            resources.pop(app, None)
            
        for props in resources.values():
            props.pop("_is_application", None)
 
        return json.dumps(resources, indent=2)
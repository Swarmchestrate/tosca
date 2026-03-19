import json
import os


AWS_ALIASES = {
    "provider": "cloud",
    "instance_type": "instance_type",
    "ssh_user": "ssh_user",
    "key_name": "ssh_key",
    "image_id": "ami",
    "security_group_id": "security_group_id",
    "security_groups": "security_group_id",
    "custom_ingress_ports": "custom_ingress_ports",
    "custom_egress_ports": "custom_egress_ports",
}

OPENSTACK_ALIASES = {
    "provider": "cloud",
    "image_id": "openstack_image_id",
    "instance_type": "openstack_flavor_id",
    "flavor_name": "openstack_flavor_id",
    "ssh_user": "ssh_user",
    "key_name": "ssh_key",
    "use_block_device": "use_block_device",
    "volume_size": "volume_size",
    "network_id": "network_id",
    "floating_ip_pool": "floating_ip_pool",
    "security_group_id": "security_group_id",
    "security_groups": "security_group_id",
    "custom_ingress_ports": "custom_ingress_ports",
    "custom_egress_ports": "custom_egress_ports",
}

EDGE_ALIASES = {
    "provider": "cloud",
    "ssh_user": "ssh_user",
    "key_name": "ssh_key",
    "ssh_auth_method": "ssh_auth_method",
    "edge_device_ip": "edge_device_ip",
    "ip": "edge_device_ip",
}

APP_ALIASES = {
    "ports": "ports",
}


def get_cluster(rdt, resource_suffix=None):
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
        resource_suffix or os.getenv("TOSCA_RESOURCE_SUFFIX") or "::Capacity"
    )

    resources = {}

    for name, node in rdt.nodeTemplates._to_dict().items():
        types = node.get("types", {})

        if "swch:AbstractResource" in types:
            print(
                f"WARNING: Abstract resource '{name}' detected. "
                f"Please provide concrete resource."
            )

        is_resource = any(
            t.get("parent", "").endswith(resource_suffix)
            or k.endswith(resource_suffix)
            for k, t in types.items()
        )

        is_application = any("Application" in k for k in types.keys())
        is_edge = any("EdgeCapacity" in k for k in types.keys())

        if not (is_resource or is_application):
            continue

        extracted = {}

        def extract_properties(prop_dict):
            for k, v in prop_dict.items():
                meta = v.get("$meta", {}) if isinstance(v, dict) else {}
                alias = meta.get("metadata", {}).get("alias")
                extracted_key = alias if alias else k
                extracted[extracted_key] = flatten(v)

        extract_properties(node.get("properties", {}))

        def extract_cap_props(cap_dict):
            for cap in cap_dict.values():
                extract_properties(cap.get("properties", {}))
                if "capabilities" in cap:
                    extract_cap_props(cap["capabilities"])

        extract_cap_props(node.get("capabilities", {}))

        for type_def in types.values():
            for k, prop_def in type_def.get("properties", {}).items():
                if (
                    k not in extracted
                    and isinstance(prop_def, dict)
                    and "default" in prop_def
                ):
                    extracted[k] = flatten({"$primitive": prop_def["default"]})

            def extract_type_cap_defaults(cap_dict):
                for cap in cap_dict.values():
                    for k, prop_def in cap.get("properties", {}).items():
                        if (
                            k not in extracted
                            and isinstance(prop_def, dict)
                            and "default" in prop_def
                        ):
                            extracted[k] = flatten(
                                {"$primitive": prop_def["default"]}
                            )
                    if "capabilities" in cap:
                        extract_type_cap_defaults(cap["capabilities"])

            for type_cap in type_def.get("capabilities", {}).values():
                extract_type_cap_defaults(type_cap.get("capabilities", {}))

        provider = str(extracted.get("provider", "")).lower()
        compute = str(extracted.get("compute", "")).lower()

        if provider in ["aws", "amazon"] or compute == "ec2":
            ALIASES = AWS_ALIASES
        elif provider == "openstack" or compute == "nova":
            ALIASES = OPENSTACK_ALIASES
        elif is_edge:
            ALIASES = EDGE_ALIASES
        elif is_application:
            ALIASES = APP_ALIASES
        else:
            ALIASES = {}

        DIRECT = set(ALIASES.values())

        final_extracted = {}
        for k, v in extracted.items():
            final_key = ALIASES.get(k, k)
            if final_key in DIRECT or k in ALIASES:
                final_extracted[final_key] = v

        if is_application:
            final_extracted["_is_application"] = True

        resources[name] = final_extracted

    # Collect all application ports
    app_ports = []
    for props in resources.values():
        if "ports" in props:
            app_ports.extend(props["ports"])

    # Inject app ports into custom_ingress_ports
    for props in resources.values():
        if "custom_ingress_ports" not in props:
            continue

        merged = []
        orig = props["custom_ingress_ports"]
        if isinstance(orig, dict):
            merged.append(orig)
        elif isinstance(orig, list):
            merged.extend(orig)

        for p in app_ports:
            if "port" in p:
                merged.append({
                    "from": str(p["port"]),
                    "to": str(p["port"]),
                    "protocol": "tcp",
                    "source": "0.0.0.0/0",
                })
            if "nodePort" in p:
                merged.append({
                    "from": str(p["nodePort"]),
                    "to": str(p["nodePort"]),
                    "protocol": "tcp",
                    "source": "0.0.0.0/0",
                })

        props["custom_ingress_ports"] = merged

    # Remove application nodes
    for app in [n for n, p in resources.items() if p.get("_is_application")]:
        resources.pop(app)

    for props in resources.values():
        props.pop("_is_application", None)

    return json.dumps(resources, indent=2)
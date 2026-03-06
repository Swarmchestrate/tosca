from typing import Optional

from ruamel.yaml import YAML

from sardou import Sardou

# Read and update YAML using ruamel.yaml
yaml = YAML()


def get_kubernetes_manifest(
    tosca_yaml: str, image_pull_secret: Optional[str] = None
) -> list:
    """
    Convert a TOSCA template string into Kubernetes manifests (Deployment + Service).
    Always injects external imagePullSecret. Handles:
    - replicas
    - env
    - args
    - ports
    - volumes
    - nodeSelector
    - imagePullSecrets
    """

    # Load and validate TOSCA

    tosca = Sardou(tosca_yaml)
    node_templates = (
        tosca.raw._to_dict().get("service_template", {}).get("node_templates", {})
    )

    if not node_templates:
        raise ValueError("No node_templates found in TOSCA YAML")

    manifests = []
    # Iterate over nodes
    for name, node in node_templates.items():
        try:
            # Sanitize name for Kubernetes RFC 1123 compliance (replace underscores with hyphens)
            k3s_name = name.replace("_", "-")

            node_type = node.get("type", "")
            if not node_type.endswith("Microservice"):
                continue

            props = node.get("properties", {}) or {}
            requirements = node.get("requirements", []) or []

            # Basic fields
            image = props.get("image")
            if not image:
                raise ValueError(f"{name}: missing image")

            replicas = int(props.get("replicas", 1))
            args = props.get("args", []) or []

            # Environment variables
            env_list = []
            for e in props.get("env", []) or []:
                if isinstance(e, dict) and "name" in e:
                    env_list.append(
                        {"name": str(e["name"]), "value": str(e.get("value", ""))}
                    )

            # PORTS
            container_ports = []
            service_ports = []

            for p in props.get("ports", []) or []:
                port = int(p.get("port", p.get("targetPort")))
                target = int(p.get("targetPort", port))
                protocol = str(p.get("protocol", "TCP")).upper()
                node_port = p.get("nodePort")

                # Deployment container ports
                container_ports.append({"containerPort": target, "protocol": protocol})

                # Service ports
                sp = {
                    "name": p.get("name", f"port-{port}"),
                    "port": port,
                    "targetPort": target,
                    "protocol": protocol,
                }

                if node_port:
                    sp["nodePort"] = int(node_port)

                service_ports.append(sp)

            # Volumes
            volumes = []
            volume_mounts = []

            for r in requirements:
                if "volume" in r:
                    vol_name = r["volume"]
                    vol_def = node_templates.get(vol_name, {})
                    props_v = vol_def.get("properties", {})
                    path = props_v.get("path")

                    if path:
                        volumes.append(
                            {
                                "name": vol_name,
                                "hostPath": {"path": path, "type": "DirectoryOrCreate"},
                            }
                        )
                        volume_mounts.append({"name": vol_name, "mountPath": path})

            # Node labels / nodeSelector
            labels = {}

            for r in requirements:
                if "host" in r:
                    node_filter = r["host"].get("node_filter", {})

                    for cond in node_filter.get("$and", []):
                        if "$equal" in cond:
                            left, right = cond["$equal"]
                            if isinstance(left, dict) and "$get_property" in left:
                                path = left["$get_property"]
                                if (
                                    isinstance(path, list)
                                    and len(path) >= 6
                                    and path[:5]
                                    == [
                                        "SELF",
                                        "TARGET",
                                        "CAPABILITY",
                                        "resource",
                                        "labels",
                                    ]
                                ):
                                    key = path[5]
                                    value = right
                                    if value not in (None, "", []):
                                        labels[key] = value
            # Deployment (standard field order)
            deployment = {
                "apiVersion": "apps/v1",
                "kind": "Deployment",
                "metadata": {"name": k3s_name},
                "spec": {
                    "replicas": replicas,
                    "selector": {"matchLabels": {"app": k3s_name}},
                    "template": {
                        "metadata": {"labels": {"app": k3s_name}},
                        "spec": {
                            **(
                                {"imagePullSecrets": [{"name": image_pull_secret}]}
                                if image_pull_secret
                                else {}
                            ),
                            **({"nodeSelector": labels} if labels else {}),
                            "containers": [
                                {
                                    "name": k3s_name,
                                    "image": image,
                                    **({"args": args} if args else {}),
                                    **({"env": env_list} if env_list else {}),
                                    **(
                                        {"ports": container_ports}
                                        if container_ports
                                        else {}
                                    ),
                                    **(
                                        {"volumeMounts": volume_mounts}
                                        if volume_mounts
                                        else {}
                                    ),
                                }
                            ],
                            **({"volumes": volumes} if volumes else {}),
                        },
                    },
                },
            }

            manifests.append(deployment)

            # Service (only if ports are defined)
            if service_ports:
                svc_type = (
                    "NodePort"
                    if any("nodePort" in p for p in service_ports)
                    else "ClusterIP"
                )

                service = {
                    "apiVersion": "v1",
                    "kind": "Service",
                    "metadata": {"name": k3s_name},
                    "spec": {
                        "type": svc_type,
                        "selector": {"app": k3s_name},
                        "ports": service_ports,
                    },
                }

                manifests.append(service)
        except Exception as e:
            print(f"Skipping node '{name}' due to error: {e}")
            continue

    return manifests

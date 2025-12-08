from ruamel.yaml import YAML

# Read and update YAML using ruamel.yaml
yaml = YAML()

def get_kubernetes_manifest(tosca_yaml: str, image_pull_secret: str = "test") -> list:
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

    try:
        data = yaml.load(tosca_yaml)
    except Exception as e:
        raise ValueError(f"Failed to parse TOSCA YAML: {e}")

    node_templates = (
        data.get("service_template", {})
            .get("node_templates", {})
    )
    if not node_templates:
        print("Warning: No node_templates found in TOSCA YAML")

    manifests = []

    for name, node in node_templates.items():
        try:
            node_type = node.get("type", "")
            if not node_type.endswith("Application"):
                continue

            props = node.get("properties", {}) or {}
            requirements = node.get("requirements", []) or []

            # -----------------------------
            # Basic fields
            # -----------------------------
            image = props.get("image")
            if not image:
                raise ValueError(f"{name}: missing image")

            replicas = int(props.get("replicas", 1))
            args = props.get("args", []) or []

            # -----------------------------
            # ENV
            # -----------------------------
            env_list = []
            for e in props.get("env", []) or []:
                if isinstance(e, dict) and "name" in e:
                    env_list.append({
                        "name": str(e["name"]),
                        "value": str(e.get("value", ""))
                    })

            # -----------------------------
            # PORTS
            # -----------------------------
            container_ports = []
            service_ports = []

            for p in props.get("ports", []) or []:
                port = int(p.get("port", p.get("targetPort")))
                target = int(p.get("targetPort", port))
                protocol = str(p.get("protocol", "TCP")).upper()
                node_port = p.get("nodePort")

                # Deployment container ports
                container_ports.append({
                    "containerPort": target,
                    "protocol": protocol
                })

                # Service ports
                sp = {
                    "name": p.get("name", f"port-{port}"),
                    "port": port,
                    "targetPort": target,
                    "protocol": protocol
                }

                if node_port:
                    sp["nodePort"] = int(node_port)

                service_ports.append(sp)

            # -----------------------------
            # Volumes from requirements
            # -----------------------------
            volumes = []
            volume_mounts = []
            node_selector = {}

            for r in requirements:
                if "host" in r:
                    node_selector["kubernetes.io/hostname"] = r["host"]

                if "volume" in r:
                    vol_name = r["volume"]
                    vol_def = node_templates.get(vol_name, {})
                    props_v = vol_def.get("properties", {})
                    path = props_v.get("path")

                    if path:
                        volumes.append({
                            "name": vol_name,
                            "hostPath": {
                                "path": path,
                                "type": "DirectoryOrCreate"
                            }
                        })
                        volume_mounts.append({
                            "name": vol_name,
                            "mountPath": path
                        })

            # -----------------------------
            # imagePullSecrets (external always wins)
            # -----------------------------
            image_pull_secrets = [{"name": image_pull_secret}]

            # -----------------------------
            # Deployment (standard field order)
            # -----------------------------
            deployment = {
                "apiVersion": "apps/v1",
                "kind": "Deployment",
                "metadata": {
                    "name": name
                },
                "spec": {
                    "replicas": replicas,
                    "selector": {
                        "matchLabels": {
                            "app": name
                        }
                    },
                    "template": {
                        "metadata": {
                            "labels": {
                                "app": name
                            }
                        },
                        "spec": {
                            "imagePullSecrets": image_pull_secrets,
                            **({"nodeSelector": node_selector} if node_selector else {}),
                            "containers": [
                                {
                                    "name": name,
                                    "image": image,
                                    **({"args": args} if args else {}),
                                    **({"env": env_list} if env_list else {}),
                                    **({"ports": container_ports} if container_ports else {}),
                                    **({"volumeMounts": volume_mounts} if volume_mounts else {})
                                }
                            ],
                            **({"volumes": volumes} if volumes else {})
                        }
                    }
                }
            }

            manifests.append(deployment)

            # -----------------------------
            # Service
            # -----------------------------
            if service_ports:
                svc_type = "NodePort" if any("nodePort" in p for p in service_ports) else "ClusterIP"

                service = {
                    "apiVersion": "v1",
                    "kind": "Service",
                    "metadata": {
                        "name": name
                    },
                    "spec": {
                        "type": svc_type,
                        "selector": {
                            "app": name
                        },
                        "ports": service_ports
                    }
                }

                manifests.append(service)
        except Exception as e:
                print(f"Skipping node '{name}' due to error: {e}")
                continue

    return manifests

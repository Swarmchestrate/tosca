from .utils import extract_properties

_PREFIX = "eu.swarmchestrate"


def _get_policies(sat, suffix, incl_type=False):
    if not hasattr(sat, "policies"):
        return {}

    policies = sat.policies._to_dict()
    result = {}

    for name, policy in policies.items():
        types = policy.get("types", {})
        match = any(k.startswith(_PREFIX) and k.endswith(suffix) for k in types)
        if not match:
            continue

        policy_data = extract_properties(policy.get("properties", {}))

        if incl_type:
            policy_data["type"] = list(types.keys())[-1]

        raw_policies = sat.raw._to_dict()["service_template"]["policies"]
        for raw_policy in raw_policies:
            if name not in raw_policy:
                continue

            targets = raw_policy[name].get("targets")
            if targets:
                policy_data["targets"] = targets

        result[name] = policy_data

    return result


def get_qos(sat):
    return _get_policies(sat, "QoS", incl_type=True)


def get_reconfiguration(sat):
    return _get_policies(sat, "Reconfiguration")


def get_scheduling(sat):
    return _get_policies(sat, "Scheduling", incl_type=True)


def get_affinity(sat):
    if not hasattr(sat, "nodeTemplates"):
        return {}

    nodes = sat.nodeTemplates._to_dict()
    microservices = [
        name for name, node in nodes.items()
        if any(
            k.startswith(_PREFIX) and k.endswith("Microservice")
            for k in (node.get("types") or {})
        )
    ]

    affinity_label = {ms: ms for ms in microservices}

    colocation_policies = _get_policies(sat, "Scheduling.Colocation")
    for policy in colocation_policies.values():
        targets = policy.get("targets", [])
        if len(targets) < 2:
            continue
        anchor = targets[0]
        for target in targets:
            affinity_label[target] = anchor

    result = {}
    for ms in microservices:
        node_name = affinity_label[ms]
        result[ms] = {
            "requiredDuringSchedulingIgnoredDuringExecution": {
                "nodeSelectorTerms": [
                    {
                        "matchExpressions": [
                            {
                                "key": "labels.swarmchestrate.eu/ms_id",
                                "operator": "In",
                                "values": [node_name],
                            }
                        ]
                    }
                ]
            }
        }

    return result

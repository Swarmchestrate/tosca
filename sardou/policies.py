from .utils import extract_properties

_PREFIX = "eu.swarmchestrate"


def _get_policies(sat, suffix):
    if not hasattr(sat, "policies"):
        return {}

    policies = sat.policies._to_dict()
    result = {}

    for name, policy in policies.items():
        types = policy.get("types", {})
        match = any(
            k.startswith(_PREFIX) and k.endswith(suffix)
            for k in types
        )
        if not match:
            continue

        policy_data = extract_properties(policy.get("properties", {}))
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
    return _get_policies(sat, "QoS")


def get_reconfiguration(sat):
    return _get_policies(sat, "Reconfiguration")


def get_scheduling(sat):
    return _get_policies(sat, "Scheduling")

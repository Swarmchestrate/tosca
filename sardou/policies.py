from .utils import extract_properties


def get_qos(sat):
    if not hasattr(sat, "policies"):
        return {}

    policies = sat.policies._to_dict()
    result = {}

    for name, policy in policies.items():
        types = policy.get("types", {})
        is_qos = any(
            k.startswith("eu.swarmchestrate") and k.endswith("QoS")
            for k in types
        )
        if not is_qos:
            continue

        result[name] = extract_properties(policy.get("properties", {}))

    return result

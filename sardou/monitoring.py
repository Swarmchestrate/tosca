_MONITORING_KEYS = ("metrics", "slo-constraints")


def _extract_monitoring(capabilities: dict) -> dict:
    """Extract monitoring properties from a single node's capabilities.

    If either key is present, the other is included as an empty dict.
    """
    monitoring = {
        key: capabilities.get(key, {}).get("properties", {}) for key in _MONITORING_KEYS
    }
    if not any(monitoring.values()):
        return {}
    return monitoring


def extract_monitoring(node_templates: dict) -> dict:
    """Return monitoring info (metrics / slo-constraints) per node.

    Nodes that define neither capability are omitted from the result.
    """
    result = {}
    for name, node in node_templates.items():
        capabilities = node.get("capabilities", {}) or {}
        monitoring = _extract_monitoring(capabilities)
        if monitoring:
            result[name] = monitoring
    return result

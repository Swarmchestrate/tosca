from .monitoring import extract_monitoring
from .utils import extract_properties

_PREFIX = "eu.swarmchestrate"

# Retraining cadences the AI library's scheduler installs as a cron job.
_RETRAIN_MINUTES = (1, 2, 3, 5, 10, 15, 20, 30)


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


def _declared_metrics(sat, targets):
    """Return the metrics *targets* declare, grouped as raw and composite.

    Each group maps a metric name to its collection frequency in seconds. A
    metric declared by more than one target appears once.
    """
    if not hasattr(sat, "raw"):
        return {}, {}

    monitoring = extract_monitoring(
        sat.raw._to_dict().get("service_template", {}).get("node_templates", {})
    )

    raw, composite = {}, {}
    for target in targets:
        declarations = monitoring.get(target, {}).get("metrics", {}) or {}
        for group, collected in (("raw", raw), ("composite", composite)):
            for metric in declarations.get(group) or []:
                name = metric.get("name")
                if name:
                    collected[name] = _seconds(metric.get("collection_frequency"))

    return raw, composite


def _seconds(frequency):
    """Convert a declared collection frequency to whole seconds."""
    text = str(frequency).strip().lower()
    units = (
        (("s", "sec", "secs", "seconds"), 1),
        (("m", "min", "mins", "minutes"), 60),
    )
    for suffixes, multiplier in units:
        for suffix in suffixes:
            if text.endswith(suffix):
                value = text[: -len(suffix)].strip()
                if value.isdigit():
                    return int(value) * multiplier
    raise ValueError(f"Unrecognised collection frequency: {frequency!r}")


def _duration(seconds):
    """Render whole seconds as the duration string the library expects."""
    return f"{seconds // 60}m" if seconds % 60 == 0 else f"{seconds}s"


def _steps(duration, resolution):
    """Convert a duration in seconds to whole steps of *resolution* seconds."""
    return max(1, duration // resolution)


def _cadence(seconds):
    """Return the longest retraining cadence the library's scheduler accepts."""
    minutes = seconds // 60
    accepted = [value for value in _RETRAIN_MINUTES if value <= minutes]
    return f"{max(accepted) if accepted else _RETRAIN_MINUTES[0]}m"


def _raw_forecast(sat):
    """Return the Forecast policies as authored, before any conversion.

    Durations stay in seconds and coverage stays a proportion, so this is the
    view to use when the policy itself matters rather than what the AI library
    expects.
    """
    return _get_policies(sat, "Forecast")


def get_forecast(sat):
    """Return the forecasting requirements as AI library settings.

    The periods a policy declares are converted to the step counts, row counts
    and duration strings the library configures itself with, so a caller
    applies the result without further arithmetic. The metrics available as
    model input come from the monitoring declarations of the policy's targets.

    Step and row counts are floored and never fall below one. The retraining
    cadence is lowered to the longest interval the library's scheduler accepts.
    """
    result = {}

    for name, policy in _raw_forecast(sat).items():
        targets = policy.get("targets", [])
        raw, composite = _declared_metrics(sat, targets)

        predicted = policy["metrics"]
        available = {**raw, **composite}
        undeclared = sorted(set(predicted) - set(available))
        if undeclared:
            raise ValueError(
                f"Forecast policy '{name}' names metrics that its targets do "
                f"not declare: {undeclared}"
            )

        resolution = policy["resolution"]
        config = {
            "targets": targets,
            "prediction_target": list(predicted),
            "STANDARD_METRICS": sorted(available),
            "data_frequency": _duration(resolution),
            "poll_interval_seconds": float(
                min([resolution, *available.values()]) if available else resolution
            ),
            "horizon": _steps(policy["forecast_duration"], resolution),
        }

        if "lookback_duration" in policy:
            config["window"] = _steps(policy["lookback_duration"], resolution)
        if "history_duration" in policy:
            config["parquet_train_size"] = _steps(
                policy["history_duration"], resolution
            )
        if "retrain_interval" in policy:
            config["retrain_frequency"] = _cadence(policy["retrain_interval"])
        if "coverage" in policy:
            config["conf_q_alpha"] = round(1 - policy["coverage"], 10)
        if "pipeline" in policy:
            config["pipeline_type"] = policy["pipeline"]

        result[name] = config

    return result


def get_affinity(sat):
    if not hasattr(sat, "nodeTemplates"):
        return {}

    nodes = sat.nodeTemplates._to_dict()
    microservices = [
        name
        for name, node in nodes.items()
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

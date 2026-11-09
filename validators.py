"""validators.py - input validation for the metrics API."""

from scoring import METRIC_KEYS

# metric -> (min, max). None means "no upper limit".
LIMITS = {
    "merge_conflicts": (0, 10000),
    "integration_time_hours": (0, 100000),
    "commit_frequency": (0, 1000),
    "collaboration_efficiency": (0, 100),
    "deployment_failure_rate": (0, 100),
}


def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def validate_metric_payload(data, partial=False):
    """Return (clean_dict, errors_dict). `partial=True` is used for updates."""
    errors = {}
    if not isinstance(data, dict):
        return {}, {"body": "JSON object expected"}

    clean = {}
    for key in METRIC_KEYS:
        if key not in data:
            if not partial:
                errors[key] = "This field is required"
            continue
        value = data[key]
        low, high = LIMITS[key]
        if not _is_number(value):
            errors[key] = "Must be a number"
        elif value != value or value in (float("inf"), float("-inf")):
            errors[key] = "Must be a finite number"
        elif value < low or value > high:
            errors[key] = f"Must be between {low} and {high}"
        else:
            clean[key] = float(value)

    if partial and not clean and not errors:
        errors["body"] = "Provide at least one metric field to update"
    return clean, errors


def validate_workflow_id(data):
    value = data.get("workflow_id") if isinstance(data, dict) else None
    if isinstance(value, bool) or not isinstance(value, int):
        return None, {"workflow_id": "Must be an integer"}
    return value, {}

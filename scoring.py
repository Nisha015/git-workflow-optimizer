"""
scoring.py - Intelligent scoring engine for Git workflow comparison.

Steps
1. Min-max normalise every metric to a 0-100 scale where 100 is ALWAYS "best".
   - "lower is better" metrics are inverted:  (max - x) / (max - min)
   - "higher is better" metrics:               (x - min) / (max - min)
   - if every workflow has the same value, all of them get 100 (a tie).
2. Multiply each normalised value by its weight (weights sum to 1).
3. Overall score (0-100) = sum of weighted normalised values.
4. The recommendation is simply the highest overall score, plus an
   explanation generated from the numbers (nothing random).
"""

METRIC_KEYS = [
    "merge_conflicts",
    "integration_time_hours",
    "commit_frequency",
    "collaboration_efficiency",
    "deployment_failure_rate",
]

METRIC_DEFS = {
    "merge_conflicts": {
        "label": "Merge Conflicts",
        "unit": "conflicts / month",
        "direction": "lower",
    },
    "integration_time_hours": {
        "label": "Code Integration Time",
        "unit": "hours (branch to main)",
        "direction": "lower",
    },
    "commit_frequency": {
        "label": "Commit Frequency",
        "unit": "commits / developer / day",
        "direction": "higher",
    },
    "collaboration_efficiency": {
        "label": "Collaboration Efficiency",
        "unit": "score out of 100",
        "direction": "higher",
    },
    "deployment_failure_rate": {
        "label": "Deployment Failure Rate",
        "unit": "% of deployments",
        "direction": "lower",
    },
}

# Default weights (sum = 1.0). Rationale is documented in README / report.
DEFAULT_WEIGHTS = {
    "merge_conflicts": 0.20,
    "integration_time_hours": 0.25,
    "commit_frequency": 0.15,
    "collaboration_efficiency": 0.20,
    "deployment_failure_rate": 0.20,
}


class ScoringError(ValueError):
    """Raised when scoring cannot be performed (bad weights, too little data)."""


def normalize_weights(weights=None):
    """Validate weights and rescale them so they sum to exactly 1."""
    if weights is None:
        return dict(DEFAULT_WEIGHTS)
    if not isinstance(weights, dict):
        raise ScoringError("weights must be an object of metric -> number")

    unknown = set(weights) - set(METRIC_KEYS)
    if unknown:
        raise ScoringError("Unknown weight keys: " + ", ".join(sorted(unknown)))

    merged = dict(DEFAULT_WEIGHTS)
    merged.update(weights)
    for key, value in merged.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ScoringError(f"Weight '{key}' must be a number")
        if value < 0:
            raise ScoringError(f"Weight '{key}' cannot be negative")

    total = sum(merged.values())
    if total <= 0:
        raise ScoringError("At least one weight must be greater than 0")
    return {key: merged[key] / total for key in METRIC_KEYS}


def normalize_metric_values(values, direction):
    """Normalise a list of numbers to 0-100 (100 = best)."""
    low, high = min(values), max(values)
    if high == low:
        return [100.0 for _ in values]
    if direction == "lower":
        return [(high - v) / (high - low) * 100 for v in values]
    return [(v - low) / (high - low) * 100 for v in values]


def normalize_rows(rows):
    """rows: list of dicts with 'workflow_id' and the 5 metric keys.
    Returns {workflow_id: {metric: normalised 0-100}}."""
    result = {row["workflow_id"]: {} for row in rows}
    for key in METRIC_KEYS:
        values = [float(row[key]) for row in rows]
        normalised = normalize_metric_values(values, METRIC_DEFS[key]["direction"])
        for row, value in zip(rows, normalised):
            result[row["workflow_id"]][key] = value
    return result


def calculate_scores(rows, weights=None):
    """Return (scores, weights). `scores` is sorted best-first and ranked."""
    if len(rows) < 2:
        raise ScoringError("At least two workflows with metrics are needed to compare")
    used_weights = normalize_weights(weights)
    normalised = normalize_rows(rows)

    scores = []
    for row in rows:
        norm = normalised[row["workflow_id"]]
        contributions = {k: norm[k] * used_weights[k] for k in METRIC_KEYS}
        scores.append(
            {
                "workflow_id": row["workflow_id"],
                "name": row.get("name"),
                "slug": row.get("slug"),
                "overall_score": round(sum(contributions.values()), 2),
                "normalized": {k: round(v, 2) for k, v in norm.items()},
                "contributions": {k: round(v, 2) for k, v in contributions.items()},
                "raw": {k: row[k] for k in METRIC_KEYS},
            }
        )

    scores.sort(key=lambda s: (-s["overall_score"], s["name"] or ""))
    for position, item in enumerate(scores, start=1):
        item["rank"] = position
    return scores, used_weights


def _confidence(margin):
    if margin >= 15:
        return "High"
    if margin >= 5:
        return "Moderate"
    return "Low (close call)"


def _fmt(key, value):
    unit = METRIC_DEFS[key]["unit"]
    number = f"{value:g}"
    return f"{number} {unit}"


def build_recommendation(scores, weights):
    """Create a human-readable explanation from already-calculated scores."""
    winner, runner_up = scores[0], scores[1]
    margin = round(winner["overall_score"] - runner_up["overall_score"], 2)

    strengths, weaknesses = [], []
    for key in METRIC_KEYS:
        label = METRIC_DEFS[key]["label"]
        weight_pct = round(weights[key] * 100)
        if winner["normalized"][key] >= 99.99 and weights[key] > 0:
            strengths.append(
                f"Best in class for {label} ({_fmt(key, winner['raw'][key])}, weight {weight_pct}%)."
            )
        elif winner["normalized"][key] <= 50 and weights[key] > 0:
            weaknesses.append(
                f"Weaker on {label} ({_fmt(key, winner['raw'][key])}); "
                f"it scored {winner['normalized'][key]:.0f}/100 on this metric."
            )

    summary = (
        f"{winner['name']} is recommended with an overall score of "
        f"{winner['overall_score']}/100, {margin} points ahead of "
        f"{runner_up['name']} ({runner_up['overall_score']}/100)."
    )
    if not strengths:
        strengths.append("Best overall balance across all weighted metrics.")

    return {
        "winner": {
            "workflow_id": winner["workflow_id"],
            "name": winner["name"],
            "slug": winner["slug"],
            "overall_score": winner["overall_score"],
        },
        "runner_up": {
            "workflow_id": runner_up["workflow_id"],
            "name": runner_up["name"],
            "overall_score": runner_up["overall_score"],
        },
        "margin": margin,
        "confidence": _confidence(margin),
        "summary": summary,
        "strengths": strengths,
        "weaknesses": weaknesses,
    }

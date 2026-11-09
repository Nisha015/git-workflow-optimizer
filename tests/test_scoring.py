"""Unit tests for the scoring algorithm (no Flask, no database)."""
import pytest

from scoring import (
    DEFAULT_WEIGHTS,
    METRIC_KEYS,
    ScoringError,
    build_recommendation,
    calculate_scores,
    normalize_metric_values,
    normalize_weights,
)


def make_rows():
    """Same numbers as the seed data (simulated)."""
    data = [
        (1, "Git Flow", "git-flow", 18, 36.0, 2.1, 72, 4.8),
        (2, "GitHub Flow", "github-flow", 11, 14.0, 3.4, 85, 6.2),
        (3, "Trunk-Based Development", "trunk-based", 6, 3.0, 5.2, 70, 7.5),
    ]
    return [
        dict(workflow_id=i, name=n, slug=s, merge_conflicts=a, integration_time_hours=b,
             commit_frequency=c, collaboration_efficiency=d, deployment_failure_rate=e)
        for i, n, s, a, b, c, d, e in data
    ]


def test_default_weights_sum_to_one():
    assert sum(DEFAULT_WEIGHTS.values()) == pytest.approx(1.0)
    assert set(DEFAULT_WEIGHTS) == set(METRIC_KEYS)


def test_lower_is_better_is_inverted():
    assert normalize_metric_values([10, 20, 30], "lower") == [100.0, 50.0, 0.0]


def test_higher_is_better_is_not_inverted():
    assert normalize_metric_values([10, 20, 30], "higher") == [0.0, 50.0, 100.0]


def test_equal_values_are_a_tie():
    assert normalize_metric_values([5, 5, 5], "lower") == [100.0, 100.0, 100.0]


def test_custom_weights_are_rescaled():
    weights = normalize_weights({"merge_conflicts": 50, "integration_time_hours": 50,
                                 "commit_frequency": 0, "collaboration_efficiency": 0,
                                 "deployment_failure_rate": 0})
    assert weights["merge_conflicts"] == pytest.approx(0.5)
    assert sum(weights.values()) == pytest.approx(1.0)


def test_invalid_weights_rejected():
    for bad in ({"merge_conflicts": -1}, {"nonsense": 1}, {"merge_conflicts": "high"},
                {"merge_conflicts": True}, "text"):
        with pytest.raises(ScoringError):
            normalize_weights(bad)


def test_all_zero_weights_rejected():
    with pytest.raises(ScoringError):
        normalize_weights({k: 0 for k in METRIC_KEYS})


def test_scores_match_hand_calculation():
    """Hand-calculated: GitHub Flow 64.25, Trunk 60.00, Git Flow 22.67."""
    scores, _ = calculate_scores(make_rows())
    by_slug = {s["slug"]: s["overall_score"] for s in scores}
    assert by_slug["github-flow"] == pytest.approx(64.25, abs=0.01)
    assert by_slug["trunk-based"] == pytest.approx(60.00, abs=0.01)
    assert by_slug["git-flow"] == pytest.approx(22.67, abs=0.01)


def test_scores_sorted_and_ranked():
    scores, _ = calculate_scores(make_rows())
    assert [s["rank"] for s in scores] == [1, 2, 3]
    totals = [s["overall_score"] for s in scores]
    assert totals == sorted(totals, reverse=True)
    assert all(0 <= t <= 100 for t in totals)


def test_best_value_gets_100_on_each_metric():
    scores, _ = calculate_scores(make_rows())
    by_slug = {s["slug"]: s for s in scores}
    assert by_slug["trunk-based"]["normalized"]["merge_conflicts"] == 100
    assert by_slug["git-flow"]["normalized"]["deployment_failure_rate"] == 100
    assert by_slug["github-flow"]["normalized"]["collaboration_efficiency"] == 100


def test_winner_changes_with_weights():
    speed = {"integration_time_hours": 50, "commit_frequency": 30, "merge_conflicts": 20,
             "collaboration_efficiency": 0, "deployment_failure_rate": 0}
    stability = {"deployment_failure_rate": 80, "merge_conflicts": 5, "integration_time_hours": 5,
                 "commit_frequency": 5, "collaboration_efficiency": 5}
    s1, w1 = calculate_scores(make_rows(), speed)
    s2, w2 = calculate_scores(make_rows(), stability)
    assert build_recommendation(s1, w1)["winner"]["slug"] == "trunk-based"
    assert build_recommendation(s2, w2)["winner"]["slug"] == "git-flow"


def test_recommendation_is_highest_score_and_deterministic():
    scores, weights = calculate_scores(make_rows())
    first = build_recommendation(scores, weights)
    second = build_recommendation(scores, weights)
    assert first == second
    assert first["winner"]["slug"] == "github-flow"
    assert first["margin"] == pytest.approx(4.25, abs=0.01)
    assert first["confidence"].startswith("Low")
    assert "GitHub Flow" in first["summary"]


def test_needs_at_least_two_workflows():
    with pytest.raises(ScoringError):
        calculate_scores(make_rows()[:1])

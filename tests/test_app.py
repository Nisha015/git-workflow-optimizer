"""REST API tests using Flask's test client."""
import pytest

VALID = {"merge_conflicts": 7, "integration_time_hours": 5, "commit_frequency": 4,
         "collaboration_efficiency": 80, "deployment_failure_rate": 3}


def test_health(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.get_json() == {"status": "ok", "workflows": 3}


def test_index_page_served(client):
    res = client.get("/")
    assert res.status_code == 200
    assert b"Git Workflow" in res.data


def test_list_workflows(client):
    data = client.get("/api/workflows").get_json()["workflows"]
    assert [w["name"] for w in data] == ["Git Flow", "GitHub Flow", "Trunk-Based Development"]


def test_list_and_read_metrics(client):
    metrics = client.get("/api/metrics").get_json()["metrics"]
    assert len(metrics) == 3
    one = client.get(f"/api/metrics/{metrics[0]['id']}").get_json()["metric"]
    assert one["name"] == "Git Flow"


def test_read_missing_metric_is_404(client):
    res = client.get("/api/metrics/9999")
    assert res.status_code == 404
    assert "error" in res.get_json()


def test_create_metric_after_delete(client):
    first = client.get("/api/metrics").get_json()["metrics"][0]
    assert client.delete(f"/api/metrics/{first['id']}").status_code == 200
    res = client.post("/api/metrics", json={"workflow_id": first["workflow_id"], **VALID})
    assert res.status_code == 201
    assert res.get_json()["metric"]["merge_conflicts"] == 7


def test_create_duplicate_is_409(client):
    first = client.get("/api/metrics").get_json()["metrics"][0]
    res = client.post("/api/metrics", json={"workflow_id": first["workflow_id"], **VALID})
    assert res.status_code == 409


def test_create_unknown_workflow_is_404(client):
    assert client.post("/api/metrics", json={"workflow_id": 999, **VALID}).status_code == 404


def test_create_validation_errors(client):
    res = client.post("/api/metrics", json={"workflow_id": 1, "merge_conflicts": -5,
                                            "collaboration_efficiency": 120,
                                            "deployment_failure_rate": "high"})
    body = res.get_json()
    assert res.status_code == 400
    assert body["error"] == "Validation failed"
    for field in ("merge_conflicts", "integration_time_hours", "commit_frequency",
                  "collaboration_efficiency", "deployment_failure_rate"):
        assert field in body["details"]


def test_bad_json_body_is_400(client):
    res = client.post("/api/metrics", data="not json", content_type="application/json")
    assert res.status_code == 400


def test_boolean_is_not_a_number(client):
    res = client.post("/api/metrics", json={"workflow_id": 1, **VALID, "merge_conflicts": True})
    assert res.status_code == 400


def test_update_metric_partial(client):
    mid = client.get("/api/metrics").get_json()["metrics"][0]["id"]
    res = client.put(f"/api/metrics/{mid}", json={"merge_conflicts": 2})
    assert res.status_code == 200
    assert res.get_json()["metric"]["merge_conflicts"] == 2
    assert res.get_json()["metric"]["integration_time_hours"] == 36.0  # untouched


def test_update_rejects_invalid_and_empty(client):
    mid = client.get("/api/metrics").get_json()["metrics"][0]["id"]
    assert client.put(f"/api/metrics/{mid}", json={"deployment_failure_rate": 101}).status_code == 400
    assert client.put(f"/api/metrics/{mid}", json={}).status_code == 400
    assert client.put("/api/metrics/9999", json={"merge_conflicts": 1}).status_code == 404


def test_delete_metric(client):
    mid = client.get("/api/metrics").get_json()["metrics"][0]["id"]
    assert client.delete(f"/api/metrics/{mid}").status_code == 200
    assert client.delete(f"/api/metrics/{mid}").status_code == 404
    assert len(client.get("/api/metrics").get_json()["metrics"]) == 2


def test_comparison_structure(client):
    data = client.get("/api/comparison").get_json()
    assert "SIMULATED" in data["disclaimer"]
    assert len(data["workflows"]) == 3
    wf = data["workflows"][0]
    assert set(wf["metrics"]) == set(wf["normalized"])
    assert data["best_per_metric"]["merge_conflicts"]["workflow"] == "Trunk-Based Development"
    assert data["best_per_metric"]["collaboration_efficiency"]["workflow"] == "GitHub Flow"
    assert data["best_per_metric"]["deployment_failure_rate"]["workflow"] == "Git Flow"


def test_scores_default_and_custom_weights(client):
    default = client.get("/api/scores").get_json()
    assert default["scores"][0]["name"] == "GitHub Flow"
    assert sum(default["weights"].values()) == pytest.approx(1.0)
    custom = client.post("/api/scores", json={"weights": {
        "integration_time_hours": 100, "merge_conflicts": 0, "commit_frequency": 0,
        "collaboration_efficiency": 0, "deployment_failure_rate": 0}}).get_json()
    assert custom["scores"][0]["name"] == "Trunk-Based Development"
    assert custom["scores"][0]["overall_score"] == 100


def test_invalid_weights_return_422(client):
    res = client.post("/api/scores", json={"weights": {"merge_conflicts": -1}})
    assert res.status_code == 422
    assert client.post("/api/recommendation", json={"weights": {"bogus": 1}}).status_code == 422


def test_recommendation_get_does_not_save(client):
    body = client.get("/api/recommendation").get_json()
    assert body["recommendation"]["winner"]["name"] == "GitHub Flow"
    assert body["saved"] is False
    assert client.get("/api/history").get_json()["history"] == []


def test_recommendation_post_saves_history(client):
    res = client.post("/api/recommendation", json={})
    assert res.status_code == 201
    assert res.get_json()["saved"] is True
    history = client.get("/api/history").get_json()["history"]
    assert len(history) == 1
    assert history[0]["winner_name"] == "GitHub Flow"
    assert len(history[0]["results"]) == 3


def test_recommendation_follows_edited_data(client):
    """Make Git Flow clearly best -> recommendation must change (not hard-coded)."""
    mid = client.get("/api/metrics").get_json()["metrics"][0]["id"]
    client.put(f"/api/metrics/{mid}", json={
        "merge_conflicts": 0, "integration_time_hours": 0, "commit_frequency": 50,
        "collaboration_efficiency": 100, "deployment_failure_rate": 0})
    assert client.get("/api/recommendation").get_json()["recommendation"]["winner"]["name"] == "Git Flow"


def test_comparison_needs_two_workflows(client):
    for m in client.get("/api/metrics").get_json()["metrics"][:2]:
        client.delete(f"/api/metrics/{m['id']}")
    assert client.get("/api/comparison").status_code == 422
    assert client.get("/api/recommendation").status_code == 422


def test_history_limit_validation(client):
    assert client.get("/api/history?limit=abc").status_code == 400


def test_unknown_api_route_returns_json_404(client):
    res = client.get("/api/nope")
    assert res.status_code == 404
    assert res.get_json()["error"]


def test_wrong_method_returns_json_405(client):
    res = client.delete("/api/workflows")
    assert res.status_code == 405
    assert "error" in res.get_json()

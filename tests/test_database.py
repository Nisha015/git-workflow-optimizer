"""Database layer tests (real SQLite file in a temp folder)."""
import sqlite3

import pytest

import database as db


@pytest.fixture
def conn(tmp_path):
    path = tmp_path / "unit.db"
    db.init_db(path)
    return db.get_connection(path)


def test_tables_are_created(conn):
    names = {r["name"] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"workflows", "metrics", "recommendation_history", "comparison_results"} <= names


def test_seed_data_inserted(conn):
    assert [w["slug"] for w in db.list_workflows(conn)] == ["git-flow", "github-flow", "trunk-based"]
    assert len(db.list_metrics(conn)) == 3
    assert all(m["data_source"] == "simulated" for m in db.list_metrics(conn))


def test_init_is_idempotent(tmp_path):
    path = tmp_path / "again.db"
    db.init_db(path)
    db.init_db(path)
    c = db.get_connection(path)
    assert c.execute("SELECT COUNT(*) FROM workflows").fetchone()[0] == 3


def test_crud_roundtrip(conn):
    metric = db.list_metrics(conn)[0]
    db.update_metric(conn, metric["id"], {"merge_conflicts": 99.0})
    updated = db.get_metric(conn, metric["id"])
    assert updated["merge_conflicts"] == 99.0
    assert updated["data_source"] == "user-entered"
    assert db.delete_metric(conn, metric["id"]) is True
    assert db.get_metric(conn, metric["id"]) is None
    new_id = db.create_metric(conn, metric["workflow_id"], {
        "merge_conflicts": 1, "integration_time_hours": 2, "commit_frequency": 3,
        "collaboration_efficiency": 4, "deployment_failure_rate": 5})
    assert db.get_metric(conn, new_id)["workflow_id"] == metric["workflow_id"]


def test_one_metric_row_per_workflow(conn):
    wf = db.list_metrics(conn)[0]["workflow_id"]
    with pytest.raises(sqlite3.IntegrityError):
        db.create_metric(conn, wf, {"merge_conflicts": 1, "integration_time_hours": 1,
                                    "commit_frequency": 1, "collaboration_efficiency": 1,
                                    "deployment_failure_rate": 1})


def test_check_constraint_blocks_bad_percentage(conn):
    metric = db.list_metrics(conn)[0]
    with pytest.raises(sqlite3.IntegrityError):
        db.update_metric(conn, metric["id"], {"deployment_failure_rate": 150.0})


def test_foreign_key_cascade(conn):
    conn.execute("DELETE FROM workflows WHERE slug = 'git-flow'")
    conn.commit()
    assert len(db.list_metrics(conn)) == 2


def test_history_is_saved_with_results(conn):
    rec = {"winner": {"workflow_id": 2, "name": "GitHub Flow", "overall_score": 64.25},
           "summary": "test summary"}
    scores = [{"workflow_id": 2, "overall_score": 64.25, "rank": 1},
              {"workflow_id": 3, "overall_score": 60.0, "rank": 2}]
    rec_id = db.save_recommendation(conn, rec, scores, {"merge_conflicts": 1.0})
    history = db.list_history(conn)
    assert history[0]["id"] == rec_id
    assert history[0]["winner_name"] == "GitHub Flow"
    assert [r["rank"] for r in history[0]["results"]] == [1, 2]


def test_reset_db_restores_sample_data(tmp_path):
    path = tmp_path / "reset.db"
    db.init_db(path)
    c = db.get_connection(path)
    c.execute("DELETE FROM metrics")
    c.commit()
    c.close()
    db.reset_db(path)
    c = db.get_connection(path)
    assert c.execute("SELECT COUNT(*) FROM metrics").fetchone()[0] == 3

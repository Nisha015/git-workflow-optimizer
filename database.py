"""database.py - SQLite schema, seed data and data-access helpers."""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from scoring import METRIC_KEYS

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DB_PATH = BASE_DIR / "instance" / "database.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS workflows (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL UNIQUE,
    slug            TEXT NOT NULL UNIQUE,
    description     TEXT NOT NULL,
    branching_model TEXT NOT NULL,
    best_for        TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS metrics (
    id                       INTEGER PRIMARY KEY AUTOINCREMENT,
    workflow_id              INTEGER NOT NULL UNIQUE
                             REFERENCES workflows(id) ON DELETE CASCADE,
    merge_conflicts          REAL NOT NULL CHECK (merge_conflicts >= 0),
    integration_time_hours   REAL NOT NULL CHECK (integration_time_hours >= 0),
    commit_frequency         REAL NOT NULL CHECK (commit_frequency >= 0),
    collaboration_efficiency REAL NOT NULL CHECK (collaboration_efficiency BETWEEN 0 AND 100),
    deployment_failure_rate  REAL NOT NULL CHECK (deployment_failure_rate BETWEEN 0 AND 100),
    data_source              TEXT NOT NULL DEFAULT 'simulated',
    updated_at               TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS recommendation_history (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at         TEXT NOT NULL,
    winner_workflow_id INTEGER REFERENCES workflows(id) ON DELETE SET NULL,
    winner_name        TEXT NOT NULL,
    winner_score       REAL NOT NULL,
    weights_json       TEXT NOT NULL,
    summary            TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS comparison_results (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    recommendation_id INTEGER NOT NULL
                      REFERENCES recommendation_history(id) ON DELETE CASCADE,
    workflow_id       INTEGER NOT NULL REFERENCES workflows(id) ON DELETE CASCADE,
    overall_score     REAL NOT NULL,
    rank              INTEGER NOT NULL
);
"""

# ---- Simulated sample data (NOT real production measurements) -------------
SEED_WORKFLOWS = [
    (
        "Git Flow", "git-flow",
        "Long-lived main and develop branches with feature, release and hotfix branches.",
        "main + develop + feature/* + release/* + hotfix/*",
        "Scheduled releases, versioned products, large teams with QA gates.",
    ),
    (
        "GitHub Flow", "github-flow",
        "One main branch that is always deployable; short-lived feature branches merged by pull request.",
        "main + short-lived feature branches + pull requests",
        "Web apps and SaaS teams that deploy often and rely on code review.",
    ),
    (
        "Trunk-Based Development", "trunk-based",
        "Everyone integrates into a single trunk at least daily using tiny commits and feature flags.",
        "trunk (main) + very short-lived branches (< 1 day)",
        "Mature CI/CD teams with strong automated testing and continuous delivery.",
    ),
]

# slug -> (merge_conflicts/month, integration hours, commits/dev/day, collaboration 0-100, failure %)
SEED_METRICS = {
    "git-flow": (18, 36.0, 2.1, 72, 4.8),
    "github-flow": (11, 14.0, 3.4, 85, 6.2),
    "trunk-based": (6, 3.0, 5.2, 70, 7.5),
}


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def get_connection(db_path=DEFAULT_DB_PATH):
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path=DEFAULT_DB_PATH, seed=True):
    """Create tables and (optionally) insert sample data if the DB is empty."""
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = get_connection(db_path)
    try:
        conn.executescript(SCHEMA)
        if seed and conn.execute("SELECT COUNT(*) FROM workflows").fetchone()[0] == 0:
            seed_database(conn)
        conn.commit()
    finally:
        conn.close()


def seed_database(conn):
    conn.executemany(
        "INSERT INTO workflows (name, slug, description, branching_model, best_for) "
        "VALUES (?, ?, ?, ?, ?)",
        SEED_WORKFLOWS,
    )
    ids = {r["slug"]: r["id"] for r in conn.execute("SELECT id, slug FROM workflows")}
    for slug, values in SEED_METRICS.items():
        conn.execute(
            "INSERT INTO metrics (workflow_id, merge_conflicts, integration_time_hours, "
            "commit_frequency, collaboration_efficiency, deployment_failure_rate, "
            "data_source, updated_at) VALUES (?, ?, ?, ?, ?, ?, 'simulated', ?)",
            (ids[slug], *values, now_iso()),
        )


def reset_db(db_path=DEFAULT_DB_PATH):
    """Drop everything and recreate with sample data."""
    conn = get_connection(db_path)
    try:
        conn.executescript(
            "DROP TABLE IF EXISTS comparison_results;"
            "DROP TABLE IF EXISTS recommendation_history;"
            "DROP TABLE IF EXISTS metrics;"
            "DROP TABLE IF EXISTS workflows;"
        )
        conn.commit()
    finally:
        conn.close()
    init_db(db_path)


# ---------------------------- data access ---------------------------------
def row_to_dict(row):
    return dict(row) if row is not None else None


def list_workflows(conn):
    return [row_to_dict(r) for r in conn.execute("SELECT * FROM workflows ORDER BY id")]


def get_workflow(conn, workflow_id):
    return row_to_dict(conn.execute("SELECT * FROM workflows WHERE id = ?", (workflow_id,)).fetchone())


_METRIC_SELECT = (
    "SELECT m.*, w.name, w.slug FROM metrics m JOIN workflows w ON w.id = m.workflow_id"
)


def list_metrics(conn):
    return [row_to_dict(r) for r in conn.execute(_METRIC_SELECT + " ORDER BY m.id")]


def get_metric(conn, metric_id):
    return row_to_dict(conn.execute(_METRIC_SELECT + " WHERE m.id = ?", (metric_id,)).fetchone())


def create_metric(conn, workflow_id, values):
    cur = conn.execute(
        "INSERT INTO metrics (workflow_id, merge_conflicts, integration_time_hours, "
        "commit_frequency, collaboration_efficiency, deployment_failure_rate, "
        "data_source, updated_at) VALUES (?, ?, ?, ?, ?, ?, 'user-entered', ?)",
        (workflow_id, *[values[k] for k in METRIC_KEYS], now_iso()),
    )
    conn.commit()
    return cur.lastrowid


def update_metric(conn, metric_id, values):
    assignments = ", ".join(f"{k} = ?" for k in values)
    conn.execute(
        f"UPDATE metrics SET {assignments}, data_source = 'user-entered', updated_at = ? WHERE id = ?",
        (*values.values(), now_iso(), metric_id),
    )
    conn.commit()


def delete_metric(conn, metric_id):
    cur = conn.execute("DELETE FROM metrics WHERE id = ?", (metric_id,))
    conn.commit()
    return cur.rowcount > 0


def save_recommendation(conn, recommendation, scores, weights):
    cur = conn.execute(
        "INSERT INTO recommendation_history (created_at, winner_workflow_id, winner_name, "
        "winner_score, weights_json, summary) VALUES (?, ?, ?, ?, ?, ?)",
        (
            now_iso(),
            recommendation["winner"]["workflow_id"],
            recommendation["winner"]["name"],
            recommendation["winner"]["overall_score"],
            json.dumps(weights),
            recommendation["summary"],
        ),
    )
    rec_id = cur.lastrowid
    conn.executemany(
        "INSERT INTO comparison_results (recommendation_id, workflow_id, overall_score, rank) "
        "VALUES (?, ?, ?, ?)",
        [(rec_id, s["workflow_id"], s["overall_score"], s["rank"]) for s in scores],
    )
    conn.commit()
    return rec_id


def list_history(conn, limit=10):
    rows = conn.execute(
        "SELECT * FROM recommendation_history ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    history = []
    for row in rows:
        item = row_to_dict(row)
        item["weights"] = json.loads(item.pop("weights_json"))
        item["results"] = [
            row_to_dict(r)
            for r in conn.execute(
                "SELECT c.workflow_id, w.name, c.overall_score, c.rank "
                "FROM comparison_results c JOIN workflows w ON w.id = c.workflow_id "
                "WHERE c.recommendation_id = ? ORDER BY c.rank",
                (item["id"],),
            )
        ]
        history.append(item)
    return history


if __name__ == "__main__":
    init_db()
    print(f"Database ready at {DEFAULT_DB_PATH}")

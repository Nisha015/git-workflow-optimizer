"""app.py - Flask backend for the Intelligent Git Workflow Optimization System."""

import sqlite3

from flask import Flask, g, jsonify, render_template, request
from werkzeug.exceptions import HTTPException

import database as db
from scoring import (
    DEFAULT_WEIGHTS,
    METRIC_DEFS,
    METRIC_KEYS,
    ScoringError,
    build_recommendation,
    calculate_scores,
)
from validators import validate_metric_payload, validate_workflow_id

DISCLAIMER = (
    "All metric values are SIMULATED sample data created for academic demonstration. "
    "They are not measurements from real production projects."
)


def create_app(db_path=None):
    app = Flask(__name__)
    app.config["DATABASE"] = str(db_path or db.DEFAULT_DB_PATH)
    db.init_db(app.config["DATABASE"])

    # ------------------------------ helpers ------------------------------
    def conn():
        if "db" not in g:
            g.db = db.get_connection(app.config["DATABASE"])
        return g.db

    @app.teardown_appcontext
    def close_db(_exc):
        connection = g.pop("db", None)
        if connection is not None:
            connection.close()

    def error(message, status, details=None):
        body = {"error": message}
        if details:
            body["details"] = details
        return jsonify(body), status

    def json_body():
        data = request.get_json(silent=True)
        return data if isinstance(data, dict) else None

    def metric_rows():
        return db.list_metrics(conn())

    # ------------------------------ errors -------------------------------
    @app.errorhandler(HTTPException)
    def handle_http(exc):
        if request.path.startswith("/api/"):
            return error(exc.description or exc.name, exc.code)
        return exc

    @app.errorhandler(ScoringError)
    def handle_scoring(exc):
        return error(str(exc), 422)

    @app.errorhandler(sqlite3.Error)
    def handle_sqlite(exc):
        return error("Database error", 500, {"reason": str(exc)})

    # ------------------------------ pages --------------------------------
    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/api/health")
    def health():
        return jsonify({"status": "ok", "workflows": len(db.list_workflows(conn()))})

    # ----------------------------- workflows -----------------------------
    @app.route("/api/workflows")
    def get_workflows():
        return jsonify({"workflows": db.list_workflows(conn())})

    # ------------------------- metrics (CRUD) ----------------------------
    @app.route("/api/metrics", methods=["GET"])
    def list_metrics():
        return jsonify({"metrics": metric_rows()})

    @app.route("/api/metrics/<int:metric_id>", methods=["GET"])
    def read_metric(metric_id):
        metric = db.get_metric(conn(), metric_id)
        if metric is None:
            return error("Metric record not found", 404)
        return jsonify({"metric": metric})

    @app.route("/api/metrics", methods=["POST"])
    def create_metric():
        data = json_body()
        if data is None:
            return error("Request body must be a JSON object", 400)
        workflow_id, errors = validate_workflow_id(data)
        clean, metric_errors = validate_metric_payload(data)
        errors.update(metric_errors)
        if errors:
            return error("Validation failed", 400, errors)
        if db.get_workflow(conn(), workflow_id) is None:
            return error("Workflow not found", 404)
        try:
            new_id = db.create_metric(conn(), workflow_id, clean)
        except sqlite3.IntegrityError:
            return error("Metrics already exist for this workflow; use PUT to update", 409)
        return jsonify({"metric": db.get_metric(conn(), new_id)}), 201

    @app.route("/api/metrics/<int:metric_id>", methods=["PUT", "PATCH"])
    def update_metric(metric_id):
        if db.get_metric(conn(), metric_id) is None:
            return error("Metric record not found", 404)
        data = json_body()
        if data is None:
            return error("Request body must be a JSON object", 400)
        clean, errors = validate_metric_payload(data, partial=True)
        if errors:
            return error("Validation failed", 400, errors)
        db.update_metric(conn(), metric_id, clean)
        return jsonify({"metric": db.get_metric(conn(), metric_id)})

    @app.route("/api/metrics/<int:metric_id>", methods=["DELETE"])
    def delete_metric(metric_id):
        if not db.delete_metric(conn(), metric_id):
            return error("Metric record not found", 404)
        return jsonify({"deleted": metric_id})

    # --------------------- comparison / scores / advice -------------------
    def weights_from_request():
        data = request.get_json(silent=True) if request.method == "POST" else None
        if request.method == "POST" and data is not None and not isinstance(data, dict):
            raise ScoringError("Request body must be a JSON object")
        return (data or {}).get("weights")

    @app.route("/api/comparison")
    def comparison():
        rows = metric_rows()
        if len(rows) < 2:
            raise ScoringError("At least two workflows with metrics are needed to compare")
        scores, weights = calculate_scores(rows)
        by_id = {s["workflow_id"]: s for s in scores}
        workflows = []
        for row in rows:
            workflows.append(
                {
                    **{k: db.get_workflow(conn(), row["workflow_id"])[k]
                       for k in ("id", "name", "slug", "description", "branching_model", "best_for")},
                    "metrics": {k: row[k] for k in METRIC_KEYS},
                    "normalized": by_id[row["workflow_id"]]["normalized"],
                    "overall_score": by_id[row["workflow_id"]]["overall_score"],
                    "data_source": row["data_source"],
                }
            )
        best = {}
        for key in METRIC_KEYS:
            pick = min if METRIC_DEFS[key]["direction"] == "lower" else max
            winner = pick(workflows, key=lambda w: w["metrics"][key])
            best[key] = {"workflow": winner["name"], "value": winner["metrics"][key]}
        return jsonify(
            {
                "disclaimer": DISCLAIMER,
                "metric_definitions": METRIC_DEFS,
                "default_weights": DEFAULT_WEIGHTS,
                "best_per_metric": best,
                "workflows": workflows,
            }
        )

    @app.route("/api/scores", methods=["GET", "POST"])
    def scores_endpoint():
        scores, weights = calculate_scores(metric_rows(), weights_from_request())
        return jsonify({"weights": weights, "scores": scores})

    @app.route("/api/recommendation", methods=["GET", "POST"])
    def recommendation():
        """GET = calculate only. POST = calculate (optional custom weights) and save to history."""
        scores, weights = calculate_scores(metric_rows(), weights_from_request())
        rec = build_recommendation(scores, weights)
        body = {"recommendation": rec, "scores": scores, "weights": weights, "saved": False}
        status = 200
        if request.method == "POST":
            body["history_id"] = db.save_recommendation(conn(), rec, scores, weights)
            body["saved"] = True
            status = 201
        return jsonify(body), status

    @app.route("/api/history")
    def history():
        try:
            limit = max(1, min(int(request.args.get("limit", 10)), 50))
        except ValueError:
            return error("limit must be an integer", 400)
        return jsonify({"history": db.list_history(conn(), limit)})

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True, port=5000)

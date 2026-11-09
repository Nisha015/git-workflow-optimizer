# Intelligent Git Workflow Optimization for Full Stack Development

A DevOps mini project that compares **Git Flow**, **GitHub Flow** and **Trunk-Based Development**
on five parameters and recommends the best one using a transparent, weighted scoring algorithm.

> **Important:** all metric values in this project are **simulated sample data** for academic
> demonstration. They are *not* measurements from real production projects.

**Stack:** HTML5 · CSS3 · JavaScript · Bootstrap 5 · Chart.js · Python Flask · SQLite · pytest · GitHub Actions

## Quick start (Windows + VS Code)

```powershell
cd git-workflow-optimizer
python -m venv venv
venv\Scripts\activate          # PowerShell. If blocked, see Troubleshooting below
pip install -r requirements.txt
python app.py
```
Open **http://127.0.0.1:5000** in Chrome/Edge. The SQLite database (`instance/database.db`) is created and filled with sample data automatically on first run.

Run the tests: `python -m pytest -v`

> The page loads Bootstrap and Chart.js from a CDN (jsDelivr), so the **browser needs internet access** during the demo.

## Project structure

```
git-workflow-optimizer/
├── app.py                  Flask app factory + REST API
├── database.py             SQLite schema, seed data, data-access functions
├── scoring.py              Normalisation, weights, scoring, explanation
├── validators.py           Input validation for the API
├── requirements.txt
├── templates/index.html    Dashboard page
├── static/css/style.css    DevOps dark theme
├── static/js/script.js     fetch() calls, charts, CRUD UI
├── tests/                  pytest: scoring, database, API, frontend wiring
├── scripts/demo_merge_conflict.sh   Git branching / conflict demo
├── .github/workflows/ci.yml         GitHub Actions CI/CD
├── docs/                   Report, viva Q&A, presentation script, guides
└── instance/database.db    Created automatically
```

## Scoring algorithm

1. **Normalise** each metric across the workflows to 0-100 (min-max). 100 always means *best*.
   Lower-is-better metrics (conflicts, integration time, failure rate) are inverted.
2. **Weight** each normalised value. Default weights:

| Metric | Direction | Weight | Why |
|---|---|---|---|
| Code Integration Time | lower | 25% | Direct measure of delivery speed, the core goal of CI/CD |
| Merge Conflicts | lower | 20% | Conflicts cost developer time and cause risky manual merges |
| Collaboration Efficiency | higher | 20% | Review flow and teamwork quality |
| Deployment Failure Rate | lower | 20% | Release stability |
| Commit Frequency | higher | 15% | Useful signal of small batches, but "more commits" is not always better |

3. **Overall score** = sum(normalised x weight), out of 100. The highest score is recommended.
4. The explanation (strengths, trade-offs, margin, confidence) is generated from the numbers. Nothing is random.

Users can change the weights with sliders (e.g. "stability matters most") and the recommendation changes accordingly.

## REST API

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/health` | Health check |
| GET | `/api/workflows` | List the 3 workflows |
| GET | `/api/metrics` | List metric records |
| GET | `/api/metrics/<id>` | Read one record |
| POST | `/api/metrics` | Create (body: `workflow_id` + 5 metrics) → 201 |
| PUT | `/api/metrics/<id>` | Update (partial allowed) |
| DELETE | `/api/metrics/<id>` | Delete |
| GET | `/api/comparison` | Raw + normalised data, best per metric |
| GET / POST | `/api/scores` | Scores (POST accepts custom `weights`, not saved) |
| GET | `/api/recommendation` | Recommendation with default weights (not saved) |
| POST | `/api/recommendation` | Recommendation with optional `weights`; saved to history |
| GET | `/api/history?limit=10` | Saved recommendations |

Errors are JSON: `{"error": "...", "details": {...}}` with status 400 (validation), 404, 405, 409 (duplicate) or 422 (cannot score).

Example:
```powershell
curl http://127.0.0.1:5000/api/recommendation
```

## Manual frontend checklist (do this before your demo)

- [ ] Page opens, yellow "Simulated data" banner is visible
- [ ] 5 metric cards, 3 workflow cards (one has "Recommended" badge)
- [ ] Bar chart and radar chart show 3 coloured series with legend
- [ ] Move sliders → "Recalculate & save" → winner/score bars change, a row appears in History
- [ ] "Add metrics" is blocked when all 3 workflows have data; Edit a record → charts update
- [ ] Delete one record → "Comparison unavailable" is NOT shown (2 remain); delete two → friendly warning appears; Add metrics restores it
- [ ] Resize the browser narrow → layout stays readable (responsive)

## Troubleshooting

- **`venv\Scripts\activate` is blocked in PowerShell:** run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once, or use Command Prompt (`venv\Scripts\activate.bat`).
- **`python` not found:** reinstall Python from python.org and tick *Add Python to PATH*; try `py` instead of `python`.
- **Port 5000 busy:** change `port=5000` at the bottom of `app.py`.
- **Charts empty / unstyled:** no internet (CDN). Connect, or download Bootstrap/Chart.js into `static/` and change the `<script>`/`<link>` URLs.
- **Reset the data:** stop the server, delete `instance/database.db`, start again (or run `python -c "import database; database.reset_db()"`).

# How to Take Screenshots for Submission

**Tools:** Windows **Win + Shift + S** (Snipping Tool: drag to select, then save from the notification) or **PrtScn**. Use a **full-width browser window** (zoom 100%, or 90% to fit more). Save as PNG in a `screenshots/` folder with the names below.

| # | File name | What to capture | How |
|---|---|---|---|
| 1 | `01_vscode_structure.png` | VS Code Explorer showing the full folder structure | Open the project folder, expand all folders |
| 2 | `02_install_and_run.png` | Terminal: `pip install -r requirements.txt` finished and `python app.py` showing "Running on http://127.0.0.1:5000" | VS Code terminal |
| 3 | `03_dashboard_top.png` | Hero header with "Simulated data" banner + 5 metric cards | Browser at top of page |
| 4 | `04_workflow_cards.png` | Three workflow cards with "Recommended" badge | Scroll to *Workflow Comparison Cards* |
| 5 | `05_bar_radar_charts.png` | Both charts with legends | Scroll to *Interactive Charts*; zoom out to 80% if needed |
| 6 | `06_raw_table.png` | Raw metric table with green best values | Below the charts |
| 7 | `07_recommendation_default.png` | Recommendation box + score bars (default weights) | *Workflow Recommendation* |
| 8 | `08_recommendation_speed.png` | After setting Integration 50, Commits 30, Conflicts 20, others 0 → Recalculate (Trunk-Based wins) | Sliders + button |
| 9 | `09_history.png` | History table with at least 2 rows | Below score breakdown |
| 10 | `10_crud_edit_modal.png` | Edit modal open on one record | *Manage Data* → pencil icon |
| 11 | `11_api_json.png` | Browser tab at `http://127.0.0.1:5000/api/recommendation` showing JSON | Open in a new tab |
| 12 | `12_mobile_view.png` | Responsive layout | Press **F12** → toggle device toolbar (Ctrl+Shift+M) → choose iPhone/Pixel |
| 13 | `13_pytest_pass.png` | Terminal after `python -m pytest -v` showing **52 passed** | VS Code terminal (scroll so the final line is visible) |
| 14 | `14_git_log_graph.png` | Output of `git log --oneline --graph --all` | Terminal |
| 15 | `15_conflict_demo.png` | Output of `bash scripts/demo_merge_conflict.sh` showing the CONFLICT and the final graph | Git Bash terminal |
| 16 | `16_github_repo.png` | GitHub repository home page | Browser |
| 17 | `17_pull_request.png` | A pull request showing the passing checks | GitHub → Pull requests |
| 18 | `18_actions_green.png` | Actions tab: workflow run with green ticks for `test` (3 versions) and `smoke-test` | GitHub → Actions → open the run |
| 19 | `19_actions_failed_demo.png` *(optional)* | A deliberately failed run (red ✗) before you fix it | Shows CI catches errors |

**Tips**
- Take screenshots **after** loading finishes (charts animate for about a second).
- Hide personal information (email, tokens) before capturing.
- Put the screenshots in the report under "17. Testing and Results" with a one-line caption each.
- Number 13 and 18 are your real evidence for testing and CI; do not skip them, and use *your own* results, not anyone else's.

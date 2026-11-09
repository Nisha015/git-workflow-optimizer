# Presentation Script (about 6-7 minutes)

**Before you start:** server running, browser open on http://127.0.0.1:5000, VS Code open on the project, GitHub repo open in another tab.

**1. Introduction (30 s)**
"Good morning. My project is *Intelligent Git Workflow Optimization for Full Stack Development*. In DevOps, how a team uses Git, its branching workflow, affects speed, quality and stability. Teams usually choose by habit. My project compares three workflows with data and recommends one."

**2. Problem and approach (45 s)**
"I compare Git Flow, GitHub Flow and Trunk-Based Development on five parameters: merge conflicts, integration time, commit frequency, collaboration efficiency and deployment failure rate. Please note the data is simulated sample data, clearly labelled on the page, because I don't have real production measurements. The value of the project is the method."

**3. Architecture (45 s)**  *(show the architecture diagram from the report)*
"It is a three-tier application. The browser UI uses HTML, Bootstrap and Chart.js and calls a Flask REST API with fetch. The API uses a scoring module and stores data in SQLite. GitHub Actions tests everything on each push."

**4. Live demo of the dashboard (2 min)**
- Scroll the cards: "These show the best performer for each parameter."
- Workflow cards: "Each workflow has its metrics and an overall score out of 100. The green badge shows the recommendation."
- Charts: "Because units differ, charts use normalised scores, 100 meaning best. The bar chart compares parameters; the radar chart shows each workflow's overall shape. Trunk-Based is strongest on speed, Git Flow on stability, GitHub Flow is balanced."
- Recommendation: "GitHub Flow wins with 64.25 against 60.00, a close call, and the system tells me why and what the trade-offs are."
- Sliders: set **Integration 50, Commit freq 30, Conflicts 20, others 0** → Recalculate. "If my team cares about speed, Trunk-Based wins. It's not hard-coded; it follows the numbers and my priorities." Then set Deployment failures to the maximum, others low → "Git Flow wins when stability matters most." Show the History table.
- CRUD: Edit one record, change a value, save, show charts updating.

**5. Algorithm (45 s)**
"Step one: min-max normalise to 0-100, inverting lower-is-better metrics. Step two: multiply by weights; integration time has the highest default weight, 25%, because delivery speed is the core aim of CI/CD. Step three: sum to a score out of 100. I hand-calculated the example and my unit test checks the same numbers."

**6. DevOps practices (1 min)**
- In the terminal run `bash scripts/demo_merge_conflict.sh` (or show the GitHub repo): "This creates two branches editing the same line, produces a merge conflict, resolves it and shows the graph."
- Show a pull request on GitHub with the green CI check: "Every push and pull request runs 52 tests on three Python versions, then a smoke test starts the app."

**7. Testing (20 s)**
"There are 52 pytest tests covering scoring, database, API and frontend wiring. Visual behaviour was checked manually with a checklist."

**8. Limitations and future scope (30 s)**
"Limitations: simulated data and min-max normalisation exaggerates differences with only three workflows. Future work: import real metrics from the GitHub API, trends, authentication and automated deployment."

**9. Conclusion (20 s)**
"No workflow is best for everyone; the best choice depends on team priorities and maturity, and this tool makes that trade-off visible and measurable. Thank you. I'm happy to take questions."

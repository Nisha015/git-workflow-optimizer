# Viva Questions and Answers

**Project concept**

**1. What is your project about?**
It compares Git Flow, GitHub Flow and Trunk-Based Development on five parameters and recommends the best one using a weighted scoring algorithm, with a Flask + SQLite backend and a Bootstrap/Chart.js dashboard.

**2. Is your data real?**
No. It is simulated sample data, labelled as such everywhere. The project demonstrates the comparison method; with real team data entered through the CRUD screen, the same algorithm applies.

**3. What is DevOps?**
A culture and set of practices that unite development and operations to deliver software faster and more reliably through automation, CI/CD, monitoring and collaboration.

**4. Why does the Git branching strategy matter in DevOps?**
It controls how often code is integrated, how many conflicts occur and how safely releases happen, which directly affect lead time and failure rate.

**Git workflows**

**5. Explain Git Flow.**
Two long-lived branches (`main`, `develop`) plus `feature/*`, `release/*` and `hotfix/*` branches. Good for scheduled, versioned releases; heavier process and more merge conflicts.

**6. Explain GitHub Flow.**
One always-deployable `main`. Work happens on short-lived feature branches, merged through reviewed pull requests, then deployed.

**7. Explain Trunk-Based Development.**
Developers commit to one trunk at least daily with small changes; unfinished work is hidden behind feature flags. It needs strong automated tests and CI.

**8. What is a merge conflict and how do you resolve it?**
It happens when two branches change the same lines. Git marks the file with `<<<<<<<`, `=======`, `>>>>>>>`; you edit to the final content, `git add` the file and commit. My `demo_merge_conflict.sh` shows this.

**9. What is a pull request?**
A request to merge a branch into another on GitHub, giving a place for code review and automated checks before merging.

**10. Difference between `git merge` and `git rebase`?**
Merge keeps history and adds a merge commit; rebase replays commits on top of another branch for a linear history. I used merge in the demo.

**11. What are feature flags?**
Switches that enable or disable a feature at runtime so unfinished code can be merged to trunk without exposing it to users.

**Algorithm**

**12. Why normalise the metrics?**
The metrics have different units (hours, percent, counts). Normalising to 0-100 makes them comparable and addable.

**13. Which normalisation did you use?**
Min-max: `(x - min)/(max - min) x 100`, inverted for lower-is-better metrics, so 100 always means best.

**14. Why different weights?**
Metrics are not equally important. Integration time has the highest default weight (25%) because delivery speed is the core aim of CI/CD. The user can change weights.

**15. Is the recommendation random or hard-coded?**
No. It is the highest calculated overall score. A test edits the data so Git Flow becomes best and verifies the recommendation changes.

**16. What is a limitation of min-max normalisation?**
With only three workflows, the worst value always becomes 0 and differences are exaggerated, so scores are relative, not absolute. Alternatives: ratio to best, z-scores, TOPSIS.

**17. How is the "confidence" computed?**
From the margin between the first and second score: ≥ 15 points High, 5-15 Moderate, below 5 "Low (close call)".

**Technology**

**18. Why Flask and SQLite?**
Both are simple, need no extra installation or server setup, and are ideal for a beginner-level project. SQLite is a single file database.

**19. What is a REST API? Which HTTP methods did you use?**
An interface where resources are accessed by URLs and standard HTTP methods. I used GET (read), POST (create), PUT (update) and DELETE (remove), with JSON responses and status codes (200, 201, 400, 404, 409, 422).

**20. How does the frontend talk to the backend?**
JavaScript `fetch()` calls the API endpoints, receives JSON and updates the DOM and Chart.js charts.

**21. Why Chart.js? Why two chart types?**
It is easy and interactive. The bar chart compares the five parameters side by side; the radar chart shows each workflow's overall shape.

**22. How do you protect against bad input and SQL injection?**
`validators.py` checks type and range; the database has CHECK constraints; all SQL uses `?` parameters (never string concatenation); the UI escapes text before inserting it in HTML.

**Database**

**23. Describe your database design.**
Four tables: `workflows`, `metrics` (one row per workflow), `recommendation_history` and `comparison_results` (scores and ranks for each saved recommendation). Foreign keys link them, and deleting a workflow cascades to its metrics.

**Testing and CI/CD**

**24. What is CI/CD?**
Continuous Integration automatically builds and tests every change; Continuous Delivery/Deployment automatically prepares or releases it. My pipeline runs tests on Python 3.10-3.12, then a smoke test that starts the app.

**25. What does your GitHub Actions file do?**
Triggers on push and pull request, checks out code, installs dependencies, runs pytest in a matrix, and a second job starts the Flask app and calls `/api/health`.

**26. What did you test?**
52 tests: scoring logic (including a hand-calculated example), database operations and constraints, every API endpoint with success and error cases, and frontend wiring checks.

**27. What did you NOT test automatically?**
Visual browser behaviour (charts, layout). I checked it manually with a checklist. A future improvement is Playwright or Selenium end-to-end tests.

**Critical thinking**

**28. Which workflow is best?**
None universally. With my simulated data and default weights GitHub Flow wins narrowly; if speed matters most, Trunk-Based wins; if stability matters most, Git Flow wins. The result depends on team priorities and maturity.

**29. What would you change to use this in a real company?**
Collect real metrics from the GitHub API, add authentication, per-team data and trends, and deploy it with Docker to a cloud host.

**30. Why was a database used instead of a JSON file?**
It gives structured storage, constraints, relationships and safe concurrent access, and demonstrates database integration.

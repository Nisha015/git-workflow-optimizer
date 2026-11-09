# Git & GitHub Guide (DevOps demonstration)

## A. Create the local repository and first commit
```powershell
cd git-workflow-optimizer
git init -b main
git add .
git commit -m "feat: initial version of Git Workflow Optimizer"
```
If Git asks who you are (first time only):
```powershell
git config --global user.name  "Your Name"
git config --global user.email "you@example.com"
```

## B. Create the GitHub repository
1. github.com → **New repository** → name `git-workflow-optimizer` → leave README/.gitignore **unchecked** → Create.
2. Connect and push:
```powershell
git remote add origin https://github.com/<your-username>/git-workflow-optimizer.git
git push -u origin main
```
3. Open the **Actions** tab: the workflow `CI/CD Pipeline` starts automatically (this is your first CI run).

## C. Feature branch → Pull Request → Merge (GitHub Flow demo)
```powershell
git switch -c feature/add-weight-explanation
# make a small change, e.g. edit a sentence in README.md
git add .
git commit -m "docs: explain scoring weights"
git push -u origin feature/add-weight-explanation
```
1. On GitHub click **Compare & pull request** → write a title → **Create pull request**.
2. Show that the **CI checks run on the pull request** (tests must pass).
3. Click **Merge pull request** → **Confirm merge** → *Delete branch*.
4. Locally: `git switch main` then `git pull`.

Optional hardening: *Settings → Branches → Add rule* for `main` → "Require status checks to pass before merging".

## D. Merge conflict demonstration
Fastest, safe and repeatable (works in Git Bash, which comes with Git for Windows):
```bash
bash scripts/demo_merge_conflict.sh
```
It initialises a temporary repo, creates two feature branches that edit the same line, merges them, shows the `<<<<<<<` conflict markers, resolves it and prints the commit graph.

Manual version (to do live in VS Code):
```powershell
git switch -c feature/a ; # edit line 1 of README.md ; git commit -am "change A"
git switch main ; git switch -c feature/b ; # edit the SAME line differently ; git commit -am "change B"
git switch main ; git merge feature/a ; git merge feature/b     # CONFLICT
# VS Code shows "Accept Current / Accept Incoming / Accept Both" above the markers. Choose one, save, then:
git add README.md
git commit -m "merge: resolve conflict"
```

## E. Compare the three strategies using Git commands
```powershell
git log --oneline --graph --all          # shape of history
git branch -a                            # branches that exist
```
| Strategy | Branches you would create | Typical history shape |
|---|---|---|
| Git Flow | `main`, `develop`, `feature/*`, `release/*`, `hotfix/*` | Many merge commits, long-lived branches |
| GitHub Flow | `main`, `feature/*` (merged via PR) | One merge per PR, shallow graph |
| Trunk-Based | `main` only (+ branches shorter than a day) | Almost linear history |

## F. CI/CD pipeline (`.github/workflows/ci.yml`)
- **Triggers:** push to `main`/`develop`, pull requests to `main`.
- **Job `test`:** matrix of Python 3.10 / 3.11 / 3.12 → install → `python -m pytest -v`.
- **Job `smoke-test`** (only if `test` passes): starts the Flask app and calls `/api/health` and `/api/recommendation`. This is the "delivery-ready" gate that represents the CD step. Real deployment (Render, Azure, etc.) is listed as future scope.

To prove CI works in your demo, push a branch that deliberately breaks a test (e.g. change `64.25` to `65` in `tests/test_scoring.py`) and show the red ✗ on the pull request, then fix it and show the green ✓.

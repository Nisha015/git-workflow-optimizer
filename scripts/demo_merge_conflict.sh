#!/usr/bin/env bash
# Demonstrates: repo init, feature branches, a merge conflict, resolution, merge.
# Run from Git Bash on Windows (installed with Git) or any Linux/macOS terminal:
#   bash scripts/demo_merge_conflict.sh
# It works in a temporary folder, so it never touches your real project.
set -e
DEMO_DIR="$(mktemp -d)/git-demo"
mkdir -p "$DEMO_DIR" && cd "$DEMO_DIR"

git init -q -b main
git config user.name  "Demo Student"
git config user.email "student@example.com"

echo "== 1. Initial commit on main =="
printf 'workflow = "GitHub Flow"\ndeploy = "manual"\n' > config.txt
git add . && git commit -q -m "chore: initial commit"
git log --oneline

echo; echo "== 2. Two developers branch from the same commit =="
git switch -q -c feature/alice-auto-deploy
sed -i 's/deploy = "manual"/deploy = "automatic"/' config.txt
git commit -q -am "feat: enable automatic deploy (Alice)"

git switch -q main
git switch -q -c feature/bob-staged-deploy
sed -i 's/deploy = "manual"/deploy = "staged"/' config.txt
git commit -q -am "feat: use staged deploy (Bob)"

echo; echo "== 3. Merge Alice's branch into main (fast-forward, no problem) =="
git switch -q main
git merge --no-edit feature/alice-auto-deploy

echo; echo "== 4. Merge Bob's branch -> CONFLICT (both changed the same line) =="
if git merge --no-edit feature/bob-staged-deploy; then
  echo "Unexpected: no conflict"; exit 1
fi
echo "--- conflicted file content ---"; cat config.txt
echo "--- git status ---"; git status --short

echo; echo "== 5. Resolve: team agrees on 'staged' =="
printf 'workflow = "GitHub Flow"\ndeploy = "staged"\n' > config.txt
git add config.txt
git commit -q -m "merge: resolve deploy-mode conflict (staged)"

echo; echo "== 6. Final history =="
git log --oneline --graph --all
echo; echo "Demo finished successfully. Folder: $DEMO_DIR"

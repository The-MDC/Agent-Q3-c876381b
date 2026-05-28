---
name: debug-github
description: Troubleshoot GitHub Actions CI failures, push errors, token issues, and PR workflows
triggers: [github, ci failed, github actions, workflow failed, ruff failed, mypy failed, push rejected, github token, pr check, ci debug, bandit, lint failed, actions]
roles: [reasoner, tandem, coder]
---

## Agent-Q3 GitHub setup
- **Repo:** https://github.com/MADdegen/Agent-Q3 (private)
- **CI:** Ruff Lint + Format · Mypy Type Check · Bandit SAST + Safety · build-push
- **Auto-deploy:** push to `main` → HF Space `MADdegens/Agent-Q3` (via workflow `5-hf-spaces-deploy.yml`)

## Reproduce CI failures locally
```bash
# Ruff (lint + format)
pip install ruff
ruff check .               # lint
ruff format --check .      # format check
ruff check --fix . && ruff format .   # auto-fix all

# Mypy
pip install mypy && mypy orchestrator/ --ignore-missing-imports

# Bandit SAST
pip install bandit && bandit -r orchestrator/ -ll

# Safety
pip install safety && safety check -r requirements.txt
```

## Common Ruff fixes
| Code | Issue | Fix |
|---|---|---|
| `I001` | Unsorted imports | `ruff check --fix .` |
| `F401` | Unused import | Remove the import |
| `E501` | Line too long | Break line or `# noqa: E501` |
| `Would reformat` | Formatting | `ruff format .` |

## Token issues
```bash
# Test token
curl -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/user
```
Two tokens in Easter Bunny. Required scopes: `repo` (full) + `workflow`.

## HF Space deploy not triggering
1. Check `HF_TOKEN` secret is set: GitHub repo → Settings → Secrets → Actions
2. Verify workflow file: `.github/workflows/5-hf-spaces-deploy.yml`
3. Push must be to `main` branch to trigger deploy

## Current open PR
- **PR #15** — `claude/sleepy-ritchie-4LrMB` → `main`
- Failing: Ruff (unused imports + formatting in `orchestrator/main.py` and 5 other files)
- Fix: `ruff check --fix . && ruff format .` then commit + push

## Branch push
```bash
git add -A && git commit -m "fix: ruff lint and format"
git push -u origin claude/sleepy-ritchie-4LrMB
```

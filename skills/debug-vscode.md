---
name: debug-vscode
description: Troubleshoot VS Code, dev containers, Python interpreter, Ruff extension, and Docker integration
triggers: [vscode, vs code, devcontainer, dev container, python interpreter, extension error, vscode debug, launch.json, intellisense broken, pylance, remote container]
roles: [reasoner, coder]
---

## Agent-Q3 VS Code setup
- Dev container: `.devcontainer/` (Python 3.11, Docker-based)
- Extensions: Pylance · Ruff · Docker · GitLens
- Settings: `.vscode/settings.json`

## Python interpreter not resolving
```
Ctrl+Shift+P → "Python: Select Interpreter"
→ /usr/local/bin/python3  (devcontainer)
→ or ./venv/bin/python
```
If red underlines persist after selecting: `Ctrl+Shift+P → "Developer: Reload Window"`

## Dev container won't start
```bash
docker info   # verify Docker daemon running

# Rebuild without cache
Ctrl+Shift+P → "Dev Containers: Rebuild Container Without Cache"

# Check for port conflicts (Agent-Q3 uses 8000-8004)
lsof -i :8000,8001,8002,8003,8004
```

## Ruff not formatting on save
`.vscode/settings.json` should contain:
```json
{
  "[python]": {
    "editor.defaultFormatter": "charliermarsh.ruff",
    "editor.formatOnSave": true
  },
  "ruff.fixAll": true,
  "ruff.organizeImports": true
}
```

## Debug FastAPI (launch.json)
```json
{
  "version": "0.2.0",
  "configurations": [{
    "name": "FastAPI: orchestrator",
    "type": "python",
    "request": "launch",
    "module": "uvicorn",
    "args": ["orchestrator.main:app","--reload","--port","8000"],
    "envFile": "${workspaceFolder}/.env"
  }]
}
```

## Docker socket permission error
```bash
sudo chmod 666 /var/run/docker.sock
```

## Useful shortcuts
| Action | Key |
|---|---|
| Ruff fix all | `Ctrl+Shift+P` → "Ruff: Fix all" |
| Toggle terminal | `` Ctrl+` `` |
| Reopen in container | `Ctrl+Shift+P` → "Reopen in Container" |
| Format file | `Shift+Alt+F` |
| Attach to container | Docker sidebar → container → right-click → "Attach VS Code" |

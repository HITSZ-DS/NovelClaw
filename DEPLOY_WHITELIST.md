# Minimal Whitelist

This is the smallest recommended whitelist for syncing the project to GitHub or packaging a clean runtime snapshot.

## Keep

```text
agents/
docs/
local_web_portal/
rag/
utils/
workflow/

.gitignore
config.py
main.py
requirements.txt
README.md
README.en.md
README.zh-CN.md
DEPLOY_WHITELIST.md
RUN_LOCAL_WEB.md
start_local.ps1
start_local.cmd
```

## Exclude

```text
.env
.venv/
venv/
__pycache__/
.pytest_cache/
*.pyc

runs/
vector_db/
vector_db_tmp/
tmp_memory_smoke/

local_web_portal/.env
local_web_portal/data/
```

## Rule

If a path is generated at runtime, contains secrets, stores local state, or can be rebuilt from source, do not upload it.

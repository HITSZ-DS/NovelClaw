# Run Local Web Portal

Recommended entrypoints on Windows:

```powershell
.\start_local.ps1
```

or:

```cmd
start_local.cmd
```

Notes:

- No manual `.env` setup is required for local startup.
- The launcher auto-creates `.venv` when needed.
- The launcher installs both root and web-portal requirements.
- The launcher checks that `local_web_portal.app.main:app` imports successfully before starting Uvicorn.
- Embedding downloads are disabled by default during local startup.

Supported Python versions:

- `3.10+`

If you already have an old `.venv` created by Python `<3.10`, the launcher will recreate it automatically.

Optional flags:

```powershell
.\start_local.ps1 -Host 0.0.0.0 -Port 8010
.\start_local.ps1 -Reload
```

Manual startup is not recommended, because users often run the wrong global Python or a mismatched `uvicorn`.

## Troubleshooting

### 1. `python -m uvicorn ...` fails but the repository launcher works

Use:

```powershell
.\start_local.ps1
```

Do not use a random global `uvicorn` from another Python installation.

### 2. `.env` is missing

That is not a blocker for local startup. The launcher and the web portal can run without manually creating `local_web_portal/.env`.

### 3. Existing `.venv` was created by the wrong Python version

Delete `.venv` and run the launcher again, or just rerun the launcher and let it recreate unsupported environments automatically.

### 4. `ModuleNotFoundError` or import failure at startup

Run the launcher again. It reinstalls:

- `requirements.txt`
- `local_web_portal/requirements.txt`

and checks that `local_web_portal.app.main:app` can be imported before starting the server.

### 5. Port `8010` is already in use

Start the portal with another port:

```powershell
.\start_local.ps1 -Port 8011
```

### 6. PowerShell execution policy blocks `.ps1`

Use:

```cmd
start_local.cmd
```

This wrapper starts the PowerShell launcher with `ExecutionPolicy Bypass`.

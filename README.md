# CoLong Idea Studio

<div align="center">
  <h3>Turn rough story ideas into chaptered, memory-aware long-form fiction.</h3>
  <p>
    Collaborative ideation, dynamic memory, chapter planning, and observable generation in one workflow.
  </p>

  <p>
    <a href="https://colong-idea-studio.cloud"><img src="https://img.shields.io/badge/Live%20Portal-Open%20Now-0f766e?style=for-the-badge&logo=googlechrome&logoColor=white" alt="Live Portal"></a>
    <a href="https://xiao-zi-chen.github.io/CoLong-Idea-Studio/"><img src="https://img.shields.io/badge/Project%20Page-Research%20Showcase-1d4ed8?style=for-the-badge&logo=githubpages&logoColor=white" alt="Project Page"></a>
    <a href="README.zh-CN.md"><img src="https://img.shields.io/badge/CN%20Docs-Read%20in%20Chinese-d946ef?style=for-the-badge" alt="Chinese Docs"></a>
    <a href="RUN_LOCAL_WEB.md"><img src="https://img.shields.io/badge/Local%20Web-Startup%20Guide-f59e0b?style=for-the-badge&logo=readthedocs&logoColor=white" alt="Local Web Guide"></a>
  </p>

  <p>
    <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python 3.10+">
    <img src="https://img.shields.io/badge/FastAPI-Web%20Portal-009688?style=flat-square&logo=fastapi&logoColor=white" alt="FastAPI">
    <img src="https://img.shields.io/badge/VectorDB-ChromaDB-F97316?style=flat-square" alt="ChromaDB">
    <img src="https://img.shields.io/badge/Mode-Dynamic%20Memory%20First-16a34a?style=flat-square" alt="Dynamic Memory First">
    <img src="https://img.shields.io/badge/Workflow-Chaptered%20Generation-7c3aed?style=flat-square" alt="Chaptered Generation">
    <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-111827?style=flat-square" alt="MIT License"></a>
  </p>

  <p>
    <a href="#why-it-feels-different">Why It Feels Different</a> |
    <a href="#quick-start">Quick Start</a> |
    <a href="#architecture">Architecture</a> |
    <a href="#runtime-artifacts">Runtime Artifacts</a>
  </p>
</div>

## At A Glance

`CoLong Idea Studio` is not a one-shot "write me a novel" prompt wrapper. It is a structured story-generation workflow that helps you clarify the idea first, plan chapters, write with dynamic memory, and inspect the system while it runs.

That makes it better suited for:

- long-form fiction and serialized stories
- worldbuilding-heavy projects
- human-in-the-loop co-writing
- experiments on memory-aware, agentic long-text generation

<table>
  <tr>
    <td width="33%" valign="top">
      <h3>Idea Copilot</h3>
      <p>Before drafting starts, the system keeps asking targeted questions until the premise is strong enough to write from.</p>
    </td>
    <td width="33%" valign="top">
      <h3>Dynamic Memory</h3>
      <p>Outlines, summaries, facts, characters, and world settings are written back and reused across later chapters.</p>
    </td>
    <td width="33%" valign="top">
      <h3>Observable Runs</h3>
      <p>You can inspect progress logs, chapter outputs, and memory artifacts instead of treating generation like a black box.</p>
    </td>
  </tr>
</table>

## Why It Feels Different

| Typical long-text setup | CoLong Idea Studio |
|---|---|
| Starts drafting from a vague prompt | Uses a collaborative `Idea Copilot` loop first |
| Context is mostly whatever fits into one prompt | Builds context from typed dynamic memory and recent artifacts |
| Later chapters drift or contradict earlier ones | Re-injects summaries, fact cards, outlines, characters, and world settings |
| Hard to know what happened during generation | Exposes `progress.log`, chapter files, and memory index data |
| Output feels "one pass" | Feels more like an iterative writing pipeline |

## Flow

<table>
  <tr>
    <td width="25%" valign="top">
      <h4>1. Clarify</h4>
      <p>Start from a premise, theme, setting, or plot seed.</p>
    </td>
    <td width="25%" valign="top">
      <h4>2. Plan</h4>
      <p>Generate a global outline plus chapter-level plans.</p>
    </td>
    <td width="25%" valign="top">
      <h4>3. Write</h4>
      <p>Draft each chapter with dynamic memory context assembled from typed artifacts.</p>
    </td>
    <td width="25%" valign="top">
      <h4>4. Reinforce</h4>
      <p>Write summaries and fact cards back into memory for later chapters.</p>
    </td>
  </tr>
</table>

## Quick Start

<details open>
<summary><b>Option A: Local Web Portal</b></summary>

Recommended on Windows:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt
python -m pip install -r local_web_portal\requirements.txt
.\start_local.ps1
```

Open:

```text
http://127.0.0.1:8010
```

Why this path is recommended:

- checks Python compatibility (`3.10+`)
- verifies `local_web_portal.app.main:app` before boot
- avoids wrong global Python or wrong `uvicorn`
- disables embedding downloads by default during local startup

Optional flags:

```powershell
.\start_local.ps1 -BindHost 0.0.0.0 -Port 8010
.\start_local.ps1 -Reload
```

</details>

<details>
<summary><b>Option B: CLI</b></summary>

Create a root `.env` or export environment variables:

```text
LLM_API_KEY=your_api_key
LLM_PROVIDER=deepseek
MODEL_NAME=deepseek-chat
```

Accepted key aliases:

- `DEEPSEEK_API_KEY`
- `OPENAI_API_KEY`
- `CODEX_API_KEY`

Then run:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python main_cli.py
```

</details>

## What You Actually Get

<table>
  <tr>
    <td width="50%" valign="top">
      <h3>Creative Workflow</h3>
      <ul>
        <li>Collaborative idea refinement</li>
        <li>Global outline generation</li>
        <li>Chapter-level planning</li>
        <li>Long-form story drafting</li>
      </ul>
    </td>
    <td width="50%" valign="top">
      <h3>System Visibility</h3>
      <ul>
        <li>Progress logs during runtime</li>
        <li>Chapter output files per run</li>
        <li>Dynamic memory index per run</li>
        <li>Inspectable planning and setting artifacts</li>
      </ul>
    </td>
  </tr>
</table>

## Architecture

<div align="center">
  <img src="docs/workflow-diagram-colong-idea-studio.png" alt="CoLong Idea Studio workflow diagram" width="94%">
</div>

The workflow closes the loop between planning, writing, retrieval, storage, and reinjection so later chapters stay grounded in earlier narrative commitments.

## Runtime Artifacts

These are the most useful files when you want to inspect or debug a run:

```text
runs/<run_id>/progress.log
runs/<run_id>/output.txt
runs/<run_id>/chapters/
vector_db/memory/run_<run_id>/memory_index.json
```

Representative `progress.log` events:

| Event | Meaning |
|---|---|
| `global_outline` | Global outline persisted |
| `chapter_outline_ready` | Chapter outlines prepared |
| `chapter_plan` | Current chapter writing plan |
| `chapter_length_plan` | Chapter target and inferred source |
| `memory_snapshot` | Dynamic-memory snapshot |
| `character_setting` / `world_setting` | Setting memory written back |

<details>
<summary><b>Repository Layout</b></summary>

```text
.
|-- agents/                # writing, retrieval, and collaborative ideation agents
|-- workflow/              # analyzer / organizer / executor
|-- rag/                   # dynamic memory and retrieval logic
|-- utils/                 # LLM client and shared utilities
|-- local_web_portal/      # local multi-user FastAPI portal
|-- docs/                  # diagrams, screenshots, and project-page assets
|-- config.py              # configuration center
|-- main_cli.py            # CLI entry
`-- main.py                # Desktop Launcher and Management UI entry
```

</details>

<details>
<summary><b>Deployment Notes</b></summary>

- Upload source code and required docs only.
- Do not deploy historical runtime data such as `runs/*`, `vector_db/*`, `.venv/*`, or `__pycache__/*`.
- Keep secrets in the real deployment environment.
- Put the public web portal behind HTTPS and a reverse proxy.

See [DEPLOY_WHITELIST.md](DEPLOY_WHITELIST.md) and [RUN_LOCAL_WEB.md](RUN_LOCAL_WEB.md) for operator-focused details.

</details>

## Documentation

- Chinese docs: [README.zh-CN.md](README.zh-CN.md)
- Research-style project page: [xiao-zi-chen.github.io/CoLong-Idea-Studio](https://xiao-zi-chen.github.io/CoLong-Idea-Studio/)
- Local portal guide: [RUN_LOCAL_WEB.md](RUN_LOCAL_WEB.md)
- License: [MIT](LICENSE)

## License

This project is released under the [MIT License](LICENSE).

## Acknowledgements 👏

Special thanks to **sirvffg冷月笙寒** for their contributions to this project.

## Citation

```bibtex
@software{colong_idea_studio_2026,
  title        = {CoLong Idea Studio: A Dynamic-Memory-First Collaborative Agent Framework for Long-Form Creative Ideation and Story Generation},
  author       = {xiao-zi-chen and contributors},
  year         = {2026},
  url          = {https://github.com/HITSZ-DS/CoLong-Idea-Studio}
}
```

# CoLong Idea Studio

<div align="center">
  <p>
    <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.10+">
    <img src="https://img.shields.io/badge/FastAPI-Local%20Portal-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI portal">
    <img src="https://img.shields.io/badge/VectorDB-ChromaDB-F97316?style=for-the-badge" alt="ChromaDB">
    <img src="https://img.shields.io/badge/Mode-Dynamic%20Memory%20First-0f766e?style=for-the-badge" alt="Dynamic memory first">
    <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-111827?style=for-the-badge" alt="MIT License"></a>
  </p>

  <h3>Structured long-form story generation with collaborative ideation, chapter planning, and dynamic memory reinjection.</h3>

  <p>
    CoLong Idea Studio turns rough ideas into inspectable, chaptered fiction pipelines instead of one-shot prompt outputs.
  </p>

  <p>
    <a href="https://colong-idea-studio.cloud"><img src="https://img.shields.io/badge/Live%20Portal-Open%20Now-0f766e?style=flat-square&logo=googlechrome&logoColor=white" alt="Live Portal"></a>
    <a href="https://xiao-zi-chen.github.io/CoLong-Idea-Studio/"><img src="https://img.shields.io/badge/Project%20Page-Research%20Showcase-1d4ed8?style=flat-square&logo=githubpages&logoColor=white" alt="Project Page"></a>
    <a href="README.zh-CN.md"><img src="https://img.shields.io/badge/Chinese-README-ef4444?style=flat-square" alt="Chinese README"></a>
    <a href="RUN_LOCAL_WEB.md"><img src="https://img.shields.io/badge/Local%20Web-Startup%20Guide-f59e0b?style=flat-square&logo=readthedocs&logoColor=white" alt="Local Web Guide"></a>
  </p>

  <p>
    <a href="#overview">Overview</a> |
    <a href="#visual-tour">Visual Tour</a> |
    <a href="#why-it-stands-out">Why It Stands Out</a> |
    <a href="#quick-start">Quick Start</a> |
    <a href="#architecture">Architecture</a> |
    <a href="#runtime-artifacts">Runtime Artifacts</a>
  </p>
</div>

<p align="center">
  <img src="docs/hero.png" alt="CoLong Idea Studio hero image" width="100%">
</p>

## Overview

`CoLong Idea Studio` is a dynamic-memory-first workflow for long-form fiction generation. Instead of asking an LLM to write everything in one pass, it separates the process into collaborative ideation, global planning, chapter planning, chapter drafting, and memory write-back.

That makes it a better fit for:

- long novels and serialized fiction
- worldbuilding-heavy stories with recurring facts and constraints
- human-in-the-loop co-writing workflows
- experiments on memory-aware and agentic long-text generation

<table>
  <tr>
    <td width="33%" valign="top">
      <h3>Idea Copilot</h3>
      <p>The system keeps asking targeted questions until the premise is specific enough to support a stable writing plan.</p>
    </td>
    <td width="33%" valign="top">
      <h3>Dynamic Memory</h3>
      <p>Summaries, fact cards, characters, world settings, and plot anchors are stored, recalled, and reinjected across chapters.</p>
    </td>
    <td width="33%" valign="top">
      <h3>Observable Runs</h3>
      <p>You can inspect progress logs, chapter files, and memory artifacts instead of treating generation like a black box.</p>
    </td>
  </tr>
</table>

## Visual Tour

<p align="center">
  <img src="docs/readme-triptych-en.png" alt="From creative overload to structured collaboration to stable narratives" width="100%">
</p>

CoLong is designed around a simple claim: long-form writing quality improves when the system helps you move from raw creative overload to structured collaboration and then to stable narratives.

## Why It Stands Out

<p align="center">
  <img src="docs/dynamic-memory.png" alt="Dynamic memory flow across summaries, fact cards, profiles, and chapter outputs" width="100%">
</p>

| Typical long-text setup | CoLong Idea Studio |
|---|---|
| Starts drafting from a vague prompt | Uses a collaborative `Idea Copilot` loop first |
| Relies on whatever fits into a single prompt window | Builds context from typed memory artifacts and recent chapter outputs |
| Later chapters drift or contradict earlier material | Reinjects summaries, fact cards, character profiles, and world rules |
| Generation is hard to inspect | Exposes `progress.log`, chapter files, and memory index data |
| Feels like one-pass prompting | Feels like a staged narrative production pipeline |

### Dynamic-Memory-First, In Practice

- chapter summaries become reusable memory for later chapters
- fact cards preserve concrete story commitments
- character and world settings are written back as separate typed artifacts
- chapter drafting pulls from recent outputs plus structured memory, not just the latest prompt

## Workflow

<table>
  <tr>
    <td width="25%" valign="top">
      <h4>1. Clarify</h4>
      <p>Start from a premise, theme, setting, or plot seed and refine it through collaborative questioning.</p>
    </td>
    <td width="25%" valign="top">
      <h4>2. Plan</h4>
      <p>Generate a global outline and chapter-level plans that shape the full writing arc.</p>
    </td>
    <td width="25%" valign="top">
      <h4>3. Write</h4>
      <p>Draft each chapter with context assembled from recent outputs and typed dynamic memory.</p>
    </td>
    <td width="25%" valign="top">
      <h4>4. Reinforce</h4>
      <p>Write summaries and settings back into memory so later chapters stay grounded in earlier commitments.</p>
    </td>
  </tr>
</table>

## Best Use Cases

- serialized web fiction
- long-form sci-fi or fantasy with dense world rules
- collaborative authoring workflows where humans steer the premise and chapters
- research and engineering work on narrative memory, chapter coherence, and agentic generation

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

Optional flags:

```powershell
.\start_local.ps1 -BindHost 0.0.0.0 -Port 8010
.\start_local.ps1 -Reload
```

Why this path is recommended:

- checks Python compatibility before boot
- validates the local FastAPI app entry before startup
- avoids common wrong-interpreter and wrong-`uvicorn` issues
- keeps local startup behavior more predictable

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
python main.py
```

</details>

## What You Get

<table>
  <tr>
    <td width="50%" valign="top">
      <h3>Creative Workflow</h3>
      <ul>
        <li>Collaborative idea refinement</li>
        <li>Global outline generation</li>
        <li>Chapter-level planning</li>
        <li>Long-form chapter drafting</li>
      </ul>
    </td>
    <td width="50%" valign="top">
      <h3>Inspectable System Output</h3>
      <ul>
        <li>Progress logs during runtime</li>
        <li>Chapter output files per run</li>
        <li>Dynamic memory index per run</li>
        <li>Persisted planning and setting artifacts</li>
      </ul>
    </td>
  </tr>
</table>

## Architecture

<p align="center">
  <img src="docs/workflow-diagram-colong-idea-studio.png" alt="CoLong Idea Studio workflow diagram" width="94%">
</p>

The architecture closes the loop between planning, writing, retrieval, storage, and reinjection so later chapters inherit earlier narrative commitments instead of drifting away from them.

## Runtime Artifacts

These are the most useful files when inspecting or debugging a run:

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
|-- agents/                # writing, retrieval, and ideation agents
|-- workflow/              # analyzer / organizer / executor
|-- rag/                   # dynamic memory and retrieval logic
|-- utils/                 # LLM client and shared utilities
|-- local_web_portal/      # local multi-user FastAPI portal
|-- docs/                  # diagrams, screenshots, and project assets
|-- config.py              # configuration center
`-- main.py                # CLI entry
```

</details>

<details>
<summary><b>Deployment Notes</b></summary>

- upload source code and required docs only
- do not deploy historical runtime data such as `runs/*`, `vector_db/*`, `.venv/*`, or `__pycache__/*`
- keep secrets in the real deployment environment
- place public web access behind HTTPS and a reverse proxy

See [DEPLOY_WHITELIST.md](DEPLOY_WHITELIST.md) and [RUN_LOCAL_WEB.md](RUN_LOCAL_WEB.md) for operator-focused details.

</details>

## Documentation

- Chinese docs: [README.zh-CN.md](README.zh-CN.md)
- Research-style project page: [xiao-zi-chen.github.io/CoLong-Idea-Studio](https://xiao-zi-chen.github.io/CoLong-Idea-Studio/)
- Local portal guide: [RUN_LOCAL_WEB.md](RUN_LOCAL_WEB.md)
- License: [MIT](LICENSE)

## Citation

```bibtex
@software{colong_idea_studio_2026,
  title        = {CoLong Idea Studio: A Dynamic-Memory-First Collaborative Agent Framework for Long-Form Creative Ideation and Story Generation},
  author       = {xiao-zi-chen and contributors},
  year         = {2026},
  url          = {https://github.com/HITSZ-DS/CoLong-Idea-Studio}
}
```

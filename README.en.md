# CoLong Idea Studio

<div align="center">

**A Collaborative Agent Framework for Long-Form Novel Generation with Dynamic Memory**

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-Web%20Portal-009688)
![ChromaDB](https://img.shields.io/badge/VectorDB-ChromaDB-orange)
![Mode](https://img.shields.io/badge/Runtime-Memory--Only-success)
![Language](https://img.shields.io/badge/Language-Simplified%20Chinese-red)

</div>

## Abstract

`CoLong Idea Studio` targets long-form, chaptered, high-consistency novel generation and adopts a **dynamic-memory-first** paradigm.  
During generation, the system continuously executes a closed loop of writing, retrieval, storage, and feedback injection in order to maintain cross-chapter consistency.

## System Architecture

![Workflow Diagram for CoLong Idea Studio](docs/workflow-diagram-colong-idea-studio.png)

> Use the provided workflow figure as the architecture diagram. Place the image at `docs/workflow-diagram-colong-idea-studio.png` to enable rendering on GitHub.

## Methodology

### 1) Chapter Length Bound Inference

The priority for chapter `t` length bounds is:

1. Parse explicit ranges from the chapter outline.
2. Otherwise parse explicit ranges from the global outline.
3. Otherwise fall back to `0.9 * chapter_target` to `1.12 * chapter_target`.

### 2) Dynamic Memory Context Construction

The writing prompt context is composed from:

1. Fixed injection: rolling summary, recent chapter summaries, and recent fact cards.
2. Semantic retrieval: relevant entries retrieved from the dynamic memory vector store.
3. Type aggregation: grouped information for characters, outlines, world settings, plot points, and facts.

---

## Progress Log Protocol

Path:

```text
runs/<run_id>/progress.log
```

Event line format:

```text
[event] YYYY-MM-DD HH:MM:SS | <event_name> | chapter <n> | <detail>
```

Structured chapter line:

```text
chapter=<n>, words=<w>, planned_total=<p>, target=<t>, min=<l>, max=<u>, topic=<topic>
```

Representative events:

| Event | Meaning |
|---|---|
| `global_outline` | global outline persisted |
| `chapter_outline_ready` | chapter outline set is ready |
| `chapter_plan` | current chapter plan |
| `chapter_outline` | current chapter outline summary |
| `chapter_length_plan` | chapter target and source |
| `chapter_length_warning` | actual length deviates from expected range |
| `character_setting` | character setting stored |
| `world_setting` | world setting stored |
| `memory_snapshot` | memory snapshot |
| `outline_character/world/retrieval` | outline-stage writes |

---

## Dynamic Memory Model

`memory_index.json` maintains the following buckets:

- `texts`
- `outlines`
- `characters`
- `world_settings`
- `plot_points`
- `fact_cards`

Notes:

1. `texts` store chapter prose and stage-level texts.
2. `outlines` store the global outline, chapter plans, chapter summaries, and the rolling summary.
3. `fact_cards` provide lightweight factual constraints to reduce cross-chapter drift.

## Repository Structure

```text
.
├─ agents/                  # writing and collaborative agents
├─ workflow/                # analyzer / organizer / executor
├─ rag/                     # dynamic memory and retrieval
├─ utils/                   # llm client and utilities
├─ local_web_portal/        # multi-user FastAPI portal
├─ config.py                # configuration center
└─ main.py                  # CLI entry
```

---

## Quick Start

### CLI

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/macOS
# source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python main.py
```

### Web Portal

```bash
python -m pip install -r requirements.txt
python -m pip install -r local_web_portal/requirements.txt
# Windows
copy local_web_portal\.env.example local_web_portal\.env
# Linux/macOS
# cp local_web_portal/.env.example local_web_portal/.env
python -m uvicorn local_web_portal.app.main:app --host 0.0.0.0 --port 8010
```

Visit: `http://127.0.0.1:8010`

---

## Strict Whitelist Deployment Principle

Upload only runtime-required files and exclude:

1. historical outputs: `runs/*`
2. historical vector stores: `vector_db/*`, `vector_db_tmp/*`
3. local state: `local_web_portal/data/*`
4. cache and environments: `.venv/*`, `__pycache__/*`, `*.pyc`

This strategy reduces package size, simplifies cold start, and lowers leakage risk.

## Citation

```bibtex
@software{colong_idea_studio_2026,
  title        = {CoLong Idea Studio: A Collaborative Agent Framework for Long-Form Novel Generation with Dynamic Memory},
  author       = {xiao-zi-chen and contributors},
  year         = {2026},
  url          = {https://github.com/xiao-zi-chen/CoLong-Idea-Studio}
}
```

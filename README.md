# CoLong Idea Studio

<div align="center">

**A Dynamic-Memory-First Collaborative Agent Framework for Long-Form Creative Ideation and Story Generation**

[Live Web Portal / 在线使用](https://colong-idea-studio.cloud) | [Project Page / Paper Showcase](https://xiao-zi-chen.github.io/CoLong-Idea-Studio/) | [Chinese Documentation / 中文文档](README.zh-CN.md)

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-Web%20Portal-009688)
![ChromaDB](https://img.shields.io/badge/VectorDB-ChromaDB-orange)
![Mode](https://img.shields.io/badge/Runtime-Dynamic%20Memory--First-success)
![Language](https://img.shields.io/badge/Default-English-red)

**✦ Research-oriented, collaboration-ready, and deployment-conscious**  
**✧ Built for long-form, chaptered, and high-consistency writing tasks (*`-`*)**

**🧠 Dynamic Memory First**  |  **🤝 Collaborative Ideation**  |  **📝 Observable Logs**  |  **📚 Long-Form Story Generation**

</div>

## ✦ Abstract

`CoLong Idea Studio` is designed for long-form, chaptered, and high-consistency creative writing tasks, following a **dynamic-memory-first** paradigm.  
The system is organized around a closed loop of **planning -> writing -> retrieval -> storage -> reinjection**, allowing later chapters to remain aligned with previously established characters, settings, facts, and narrative commitments.

Compared with workflows that rely heavily on static knowledge bases, this framework places stronger emphasis on:

1. **🤝 Collaborative ideation**: before formal writing begins, the agent keeps asking targeted questions to refine the user's idea.
2. **🧠 Dynamic-memory-driven generation**: outlines, facts, character settings, world settings, and chapter summaries are continuously written back and retrieved during generation.

## 🌐 Online Access

- Live Web Portal: [https://colong-idea-studio.cloud](https://colong-idea-studio.cloud)
- Academic Project Page: [https://xiao-zi-chen.github.io/CoLong-Idea-Studio/](https://xiao-zi-chen.github.io/CoLong-Idea-Studio/)

## 🏛️ Project Page

For a more academic, paper-style showcase page including system overview, workflow figure, evaluation snapshot, and repository links, please visit:

- [CoLong Idea Studio Project Page](https://xiao-zi-chen.github.io/CoLong-Idea-Studio/)

## 🧩 Architecture

![CoLong Idea Studio Workflow Diagram](docs/workflow-diagram-colong-idea-studio.png)

The current repository uses the provided workflow figure as the system architecture diagram, illustrating the full path from collaborative ideation to dynamic-memory-guided story generation.

## ✍️ Methodology

### 🧠 2) Dynamic Memory Context Construction

The writing prompt context is composed of three parts:

1. Fixed injections: rolling summary, recent chapter summaries, and recent fact cards.
2. Semantic retrieval: relevant entries recalled from the dynamic-memory vector store.
3. Type-aware grouping: characters, outlines, world settings, plot points, and fact cards are grouped before prompt assembly.

### 🤝 3) Collaborative Ideation as an Agent Procedure

The ideation stage is implemented as an **agent-level collaborative loop**, rather than a simple frontend Q&A helper. The `Idea Copilot Agent` continues asking questions until the user explicitly confirms that the idea is mature enough to proceed into formal writing.

A typical collaborative trajectory is:

1. The user provides an initial premise, setting, theme, or plot seed.
2. The agent asks targeted questions about conflict, setting, character motivation, narrative tone, structure, and audience expectation.
3. The user iteratively supplements and refines the idea.
4. Once the user explicitly confirms readiness, the system consolidates the ideation result into a more stable writing brief and enters the outline-generation stage.

✧ This design substantially reduces downstream drift caused by underspecified creative input, and better matches the research positioning of collaborative long-form generation systems (o^_^o)

---

## 📝 Progress Log Protocol

Path:

```text
runs/<run_id>/progress.log
```

Event-line format:

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
| `global_outline` | Global outline persisted |
| `chapter_outline_ready` | Chapter outlines prepared |
| `chapter_plan` | Current chapter writing plan |
| `chapter_outline` | Current chapter outline excerpt |
| `chapter_length_plan` | Chapter target and inferred source |
| `chapter_length_warning` | Actual chapter length deviates from expectation |
| `character_setting` | Character-setting memory written |
| `world_setting` | World-setting memory written |
| `memory_snapshot` | Dynamic-memory snapshot |
| `outline_character/world/retrieval` | Outline-stage artifact logs |

✦ The Progress Log is intentionally designed as a rich and transparent observation layer, so users can inspect not only final generation results but also the hidden outline, planning, memory, and setting-level signals behind them (=^.^=)

---

## 🧠 Dynamic Memory Model

`memory_index.json` maintains the following buckets:

- `texts`
- `outlines`
- `characters`
- `world_settings`
- `plot_points`
- `fact_cards`

Notes:

1. `texts` store chapter bodies and intermediate-stage outputs.
2. `outlines` store the global outline, chapter plans, chapter summaries, and rolling summaries.
3. `fact_cards` act as lightweight factual constraints to reduce cross-chapter drift.

Under the current configuration philosophy, the project is best suited to run in a **dynamic-memory-priority mode**, where static RAG and static knowledge components can be weakened or disabled whenever they do not help long-form creative generation.

## 📁 Repository Structure

```text
.
├─ agents/                  # writing, retrieval, and collaborative ideation agents
├─ workflow/                # analyzer / organizer / executor
├─ rag/                     # dynamic memory and retrieval logic
├─ utils/                   # LLM client and utility modules
├─ local_web_portal/        # multi-user FastAPI portal
├─ docs/                    # figures and documentation assets
├─ config.py                # configuration center
└─ main.py                  # CLI entry
```

---

## 🚀 Quick Start

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

### 🌐 Web Portal

```bash
python -m pip install -r requirements.txt
python -m pip install -r local_web_portal/requirements.txt
# Windows
copy local_web_portal\.env.example local_web_portal\.env
# Linux/macOS
# cp local_web_portal/.env.example local_web_portal/.env
python -m uvicorn local_web_portal.app.main:app --host 0.0.0.0 --port 8010
```

Access:

```text
http://127.0.0.1:8010
```

---

## 📦 Deployment Principle

For server deployment, it is recommended to upload only runtime-required files and exclude the following whenever possible:

1. Historical outputs: `runs/*`
2. Historical vector databases: `vector_db/*`, `vector_db_tmp/*`
3. Local state: `local_web_portal/data/*`
4. Caches and environments: `.venv/*`, `__pycache__/*`, `*.pyc`

This whitelist-oriented deployment strategy reduces repository noise, lowers cold-start complexity, and minimizes the risk of unintentionally exposing local runtime artifacts.

## 🌐 Documentation Entry

The default GitHub landing page is intentionally presented in English for broader public visibility.  
For the full Simplified Chinese documentation, please visit:

- [README.zh-CN.md](README.zh-CN.md)

## 📚 Citation

```bibtex
@software{colong_idea_studio_2026,
  title        = {CoLong Idea Studio: A Dynamic-Memory-First Collaborative Agent Framework for Long-Form Creative Ideation and Story Generation},
  author       = {xiao-zi-chen and contributors},
  year         = {2026},
  url          = {https://github.com/HITSZ-DS/CoLong-Idea-Studio}
}
```

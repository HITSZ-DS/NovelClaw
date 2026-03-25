# CoLong Idea Studio

<div align="center">
  <p>
    <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.10+">
    <img src="https://img.shields.io/badge/FastAPI-本地门户-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI 本地门户">
    <img src="https://img.shields.io/badge/VectorDB-ChromaDB-F97316?style=for-the-badge" alt="ChromaDB">
    <img src="https://img.shields.io/badge/模式-动态记忆优先-0f766e?style=for-the-badge" alt="动态记忆优先">
    <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-111827?style=for-the-badge" alt="MIT License"></a>
  </p>

  <h3>✨ 面向长篇叙事生成的结构化工作流：协同构思、分章规划、动态记忆回注。</h3>

  <p>
    💡 CoLong Idea Studio 不是一次性写完的提示词封装，而是把粗糙想法整理成可检查、可追踪、可持续扩写的长篇创作流程。😊
  </p>

  <p>
    <b>🚀 线上体验入口：</b><a href="https://colong-idea-studio.cloud">colong-idea-studio.cloud</a> 🚀✨🌐
  </p>

  <p>
    <a href="https://colong-idea-studio.cloud"><img src="https://img.shields.io/badge/在线门户-立即体验-0f766e?style=flat-square&logo=googlechrome&logoColor=white" alt="在线门户"></a>
    <a href="https://xiao-zi-chen.github.io/CoLong-Idea-Studio/"><img src="https://img.shields.io/badge/项目页-研究展示-1d4ed8?style=flat-square&logo=githubpages&logoColor=white" alt="项目页"></a>
    <a href="README.md"><img src="https://img.shields.io/badge/English-README-ef4444?style=flat-square" alt="English README"></a>
    <a href="RUN_LOCAL_WEB.md"><img src="https://img.shields.io/badge/本地%20Web-启动说明-f59e0b?style=flat-square&logo=readthedocs&logoColor=white" alt="本地 Web 启动说明"></a>
  </p>

  <p>
    <a href="#概览">概览</a> |
    <a href="#视觉预览">视觉预览</a> |
    <a href="#为什么它更特别">为什么它更特别</a> |
    <a href="#快速开始">快速开始</a> |
    <a href="#架构">架构</a> |
    <a href="#运行产物">运行产物</a>
  </p>
</div>

<p align="center">
  <img src="docs/hero.png" alt="CoLong Idea Studio 主视觉图" width="100%">
</p>

> 🚀 **在线体验**
> 👀 直接访问 **[colong-idea-studio.cloud](https://colong-idea-studio.cloud)**，这是最快上手 CoLong 的方式，不容易错过。

## 🌟 概览

`CoLong Idea Studio` 是一个以动态记忆为核心的长篇故事生成工作流。它不会让模型直接“一口气写完整本书”，而是把过程拆成协同构思、全局规划、章节规划、章节写作和记忆回写几个阶段。

它尤其适合更想要控制力和一致性的创作者与研究者。🎯

- 📚 长篇小说和连载式叙事
- 🌍 世界观复杂、约束多、角色关系重的故事
- 🤝 人机协同创作流程
- 🧪 面向长文本一致性、记忆机制、Agent 写作的实验和研究

<table>
  <tr>
    <td width="33%" valign="top">
      <h3>🤝 Idea Copilot</h3>
      <p>系统会持续追问关键问题，直到创意清晰到足以支撑稳定的章节规划和写作。</p>
    </td>
    <td width="33%" valign="top">
      <h3>🧠 动态记忆</h3>
      <p>章节摘要、事实卡片、人物设定、世界规则和情节锚点会被存储、召回，并在后续章节中重新注入。</p>
    </td>
    <td width="33%" valign="top">
      <h3>👀 可观测运行</h3>
      <p>你可以检查进度日志、章节文件和记忆索引，而不是把生成过程当成黑箱。</p>
    </td>
  </tr>
</table>

## 👀 视觉预览

<p align="center">
  <img src="docs/readme-triptych-en.png" alt="从创意过载到结构化协作再到稳定叙事" width="100%">
</p>

CoLong 的核心观点很直接：长篇创作质量不只是靠模型“会写”，而是靠系统能否把创意过载转化为结构化协作，再沉淀成稳定叙事。✨

## ✨ 为什么它更特别

<p align="center">
  <img src="docs/dynamic-memory.png" alt="动态记忆在摘要、事实卡片、人物档案和章节输出之间流动" width="100%">
</p>

| 常见长文本生成方式 | CoLong Idea Studio |
|---|---|
| 从模糊想法直接开写 | 先通过 `Idea Copilot` 反复澄清思路 |
| 依赖一次 prompt 能装下多少上下文 | 使用类型化记忆产物和近期章节输出组装上下文 |
| 后续章节容易漂移、打架、遗忘前文承诺 | 回注摘要、事实卡片、人物档案和世界规则 |
| 生成过程难以解释 | 暴露 `progress.log`、章节文件和记忆索引 |
| 更像一次性提示词输出 | 更像分阶段推进的叙事生产流水线 |

### 🧠 动态记忆优先，具体体现在哪

- 📝 每章摘要会变成后续章节可复用的记忆
- 📌 事实卡片用于固定关键设定和剧情承诺
- 👤 人物设定与世界观设定会作为独立类型写回记忆
- 🔁 写新章节时拉取的是“近期输出 + 结构化记忆”，不是只依赖最后一轮 prompt

## 🔄 工作流

<table>
  <tr>
    <td width="25%" valign="top">
      <h4>1. 澄清</h4>
      <p>从题材、主题、设定或情节种子出发，通过协同追问把创意补完整。</p>
    </td>
    <td width="25%" valign="top">
      <h4>2. 规划</h4>
      <p>生成全局大纲和章节级计划，先把长篇写作的骨架搭起来。</p>
    </td>
    <td width="25%" valign="top">
      <h4>3. 写作</h4>
      <p>每一章都从近期输出和类型化动态记忆中拼装上下文，再进行草稿生成。</p>
    </td>
    <td width="25%" valign="top">
      <h4>4. 强化</h4>
      <p>把新摘要、新设定和关键事实写回记忆，让后续章节继续继承前文约束。</p>
    </td>
  </tr>
</table>

## 🎯 适合的场景

- 📖 网络连载和章节化长篇创作
- 🚀 科幻、奇幻等高世界观密度叙事
- 🤝 需要作者持续介入控制方向的人机协同写作
- 🧪 研究叙事记忆、章节一致性和 Agent 生成流程的工程实验

## 🚀 快速开始

<details open>
<summary><b>🌐 方案 A：本地 Web 门户</b></summary>

💻 Windows 下推荐这样启动：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt
python -m pip install -r local_web_portal\requirements.txt
.\start_local.ps1
```

🌐 启动后访问：

```text
http://127.0.0.1:8010
```

⚡ 如果你想直接在线试用，也可以访问：

```text
https://colong-idea-studio.cloud
```

🛠️ 可选参数：

```powershell
.\start_local.ps1 -BindHost 0.0.0.0 -Port 8010
.\start_local.ps1 -Reload
```

✅ 为什么推荐这个入口：

- ✅ 启动前会检查 Python 版本
- ✅ 会先验证本地 FastAPI 入口是否可导入
- ✅ 能减少解释器或 `uvicorn` 指向错误带来的问题
- ✅ 本地体验更稳定，排错路径也更清晰

</details>

<details>
<summary><b>⌨️ 方案 B：CLI</b></summary>

🔐 先在项目根目录创建 `.env`，或直接配置环境变量：

```text
LLM_API_KEY=your_api_key
LLM_PROVIDER=deepseek
MODEL_NAME=deepseek-chat
```

🗝️ 也兼容这些 API Key 变量名：

- `DEEPSEEK_API_KEY`
- `OPENAI_API_KEY`
- `CODEX_API_KEY`

▶️ 然后执行：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python main_cli.py
```

</details>

## 🎁 你会得到什么

<table>
  <tr>
    <td width="50%" valign="top">
      <h3>🎨 创作流程能力</h3>
      <ul>
        <li>协同式创意澄清</li>
        <li>全局大纲生成</li>
        <li>章节级规划</li>
        <li>长篇章节写作</li>
      </ul>
    </td>
    <td width="50%" valign="top">
      <h3>🔍 可检查系统输出</h3>
      <ul>
        <li>运行中的进度日志</li>
        <li>按 run 保存的章节产物</li>
        <li>按 run 保存的动态记忆索引</li>
        <li>持久化的规划和设定类产物</li>
      </ul>
    </td>
  </tr>
</table>

## 🧠 架构

<p align="center">
  <img src="docs/workflow-diagram-colong-idea-studio.png" alt="CoLong Idea Studio 工作流图" width="94%">
</p>

整个架构把规划、写作、检索、存储和回注闭环连接起来，让后续章节持续继承前文已经形成的叙事承诺，而不是越写越散。

## 📦 运行产物

调试或理解一次运行时，最值得看的文件通常是：

```text
runs/<run_id>/progress.log
runs/<run_id>/output.txt
runs/<run_id>/chapters/
vector_db/memory/run_<run_id>/memory_index.json
```

`progress.log` 中比较关键的事件包括：

| 事件 | 含义 |
|---|---|
| `global_outline` | 全局大纲已落盘 |
| `chapter_outline_ready` | 章节大纲已准备完成 |
| `chapter_plan` | 当前章节写作计划 |
| `chapter_length_plan` | 当前章节目标长度及其来源 |
| `memory_snapshot` | 动态记忆快照 |
| `character_setting` / `world_setting` | 人物设定或世界观设定已写回记忆 |

<details>
<summary><b>仓库结构</b></summary>

```text
.
|-- agents/                # 写作、检索、创意协同相关 Agent
|-- workflow/              # analyzer / organizer / executor
|-- rag/                   # 动态记忆与检索逻辑
|-- utils/                 # LLM 客户端与通用工具
|-- local_web_portal/      # 本地多用户 FastAPI 门户
|-- docs/                  # 图示、截图和项目素材
|-- config.py              # 配置中心
|-- main_cli.py            # CLI 纯终端运行入口
`-- main.py                # 桌面端启动器与管理界面入口
```

</details>

<details>
<summary><b>部署建议</b></summary>

- 只上传源码和必要文档
- 不要部署历史运行产物，例如 `runs/*`、`vector_db/*`、`.venv/*`、`__pycache__/*`
- 密钥应保存在真实部署环境中，不要直接提交到仓库
- 如果要公开 Web 门户，建议放在 HTTPS 和反向代理之后

详见 [DEPLOY_WHITELIST.md](DEPLOY_WHITELIST.md) 和 [RUN_LOCAL_WEB.md](RUN_LOCAL_WEB.md)。

</details>

## 📚 更多文档

- 🇬🇧 英文 README: [README.md](README.md)
- 🖼️ 项目展示页: [xiao-zi-chen.github.io/CoLong-Idea-Studio](https://xiao-zi-chen.github.io/CoLong-Idea-Studio/)
- 🌐 本地门户启动说明: [RUN_LOCAL_WEB.md](RUN_LOCAL_WEB.md)
- ⚖️ 许可证: [MIT](LICENSE)

## 致谢 👏

特别感谢 **sirvffg冷月笙寒** 对本项目的贡献。

## Star 增长趋势 📈

这里可以直接看到仓库的 Star 增长曲线：

[![Star History Chart](https://api.star-history.com/svg?repos=HITSZ-DS/CoLong-Idea-Studio&type=Date)](https://star-history.com/#HITSZ-DS/CoLong-Idea-Studio&Date)

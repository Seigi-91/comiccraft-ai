# ComicCraft AI · An editable comic creation workspace

[简体中文](README.md) · **English**

[![CI](https://github.com/Seigi-91/comiccraft-ai/actions/workflows/ci.yml/badge.svg)](https://github.com/Seigi-91/comiccraft-ai/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/code-MIT-blue.svg)](LICENSE)

Turn a story into panels you can keep editing: scripts, character outfits, dialogue bubbles, masked repairs and chapter versions. Built with React, FastAPI, LangGraph, SQLite and Pillow.

**[Try the bubble editor — no install or API key](https://seigi-91.github.io/comiccraft-ai/demo.html)** · [Showcase](https://seigi-91.github.io/comiccraft-ai/) · [Video & editable project](https://github.com/Seigi-91/comiccraft-ai/releases) · [Roadmap](docs/ROADMAP.md)

![Rain Night, One Light — example comic](docs/images/comic.jpg)

## What makes this useful

- Six role-specific agents coordinate planning, storyboards, dialogue, artwork, review and layout.
- Edit the outline, panel descriptions and dialogue rather than restarting the whole chapter.
- Move/resize bubbles, edit their text, drag tail tips, and switch speech/thought/narration.
- Select a damaged region for repair, compare the result and explicitly adopt it. Compositing retains original source-panel pixels outside the mask.
- Keep character profiles and outfits, attach references, inspect per-panel request snapshots and restore chapter versions.
- Configure text/vision and image providers independently. Use your own API services, the official Codex connector, or a combination.

These features support control and review; they do not guarantee visual consistency or make the project unique among comic tools.

## Choose how models run

Open **Creative Team & Settings** (the application UI currently uses Chinese labels: **创作团队与设置**).

| Setup | Text & vision panel | Image panel | What you do |
|---|---|---|---|
| Official Codex connector | Codex | Codex | Sign in to ChatGPT, verify capabilities, and enable automatic calls |
| Automated providers | API | API | Supply separate base URLs, model names and your own keys |
| Mixed | Either | Either | Use an API for writing and ChatGPT for images, or the reverse |

Text/vision uses OpenAI-compatible `/chat/completions`; visual review needs an image-capable model. Image generation uses `/images/generations`, reference-based generation uses multipart `/images/edits`. Masked editing also needs an editing-capable service. Native vendor-specific protocols need separate adapters.

Keys stay in the backend computer's `.env` and are not returned by the configuration endpoint. Settings writes are restricted to local access. You can keep an existing key by leaving its field empty, or explicitly clear it. Saving settings does **not** send a paid test or verify your provider's quota.

**Manual generation handoffs are retired in v2.5.1.** Existing tasks can migrate to an automatic provider; editorial approval is still available. This project does not extract session credentials or provide model access/credits. The GitHub Pages demo uses pre-generated artwork and makes no AI calls. The complete app runs locally.

## Run locally

Requirements: Python 3.11+, Node.js 20+, Git. No GPU is required by the orchestration/editor itself; external or locally hosted models have their own requirements.

Windows one-click bootstrap: download the [installer ZIP](https://github.com/Seigi-91/comiccraft-ai/releases/download/v2.5.1/ComicCraft-AI-Windows-Installer.zip), extract it, then run `Install-ComicCraft-Auto.cmd` for the official connector setup, or `Install-ComicCraft.cmd` for the website only. It downloads tagged source and can install missing Python/Node through winget. Internet and any OS permission prompts still apply. It preserves existing local work. [Details and limitations](docs/INSTALL.md).

Or use Git on Windows:

```powershell
git clone https://github.com/Seigi-91/comiccraft-ai.git
cd comiccraft-ai
powershell -ExecutionPolicy Bypass -File .\start.ps1
```

Open **http://127.0.0.1:8000**. The script creates a venv, copies `.env.example` if needed, installs dependencies and builds the frontend.

macOS / Linux:

```bash
git clone https://github.com/Seigi-91/comiccraft-ai.git
cd comiccraft-ai
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
cp .env.example .env # only for a fresh installation; preserve an existing .env
npm --prefix frontend ci
npm --prefix frontend run build
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Install a Chinese-capable font, such as Noto Sans CJK, and set `COMIC_FONT_PATH` if needed. A fresh install starts with an empty database. Click the home screen’s sample-import button to load an editable six-panel example without model calls. Re-import opens it without overwriting edits. Environment diagnostics are available there too.

## Professional knowledge and production controls

Each agent has four original knowledge cards (24 total), including directing/storyboard grammar, continuity, dialogue, anatomy checks and lettering. Role-filtered local lexical retrieval adds relevant cards to real prompts and records their IDs/hashes. This is not vector RAG, model training, or a redistribution of textbooks. [Knowledge guide](knowledge/README.md).

Approve and lock character assets; draft edits stay separate until re-approved. The workbench includes a human six-axis consistency rubric bound to panel and lettering state. Explicit cost-consented probes test five provider capabilities. Persistent request caps and numerical usage records help bound API attempts; currency costs remain unknown. Database leases/heartbeats reduce duplicate runner entry in the supported single-instance deployment. They do not promise exactly-once provider billing.

## Limits and validation

- This is an early local-first app, **not a public multi-user SaaS**. There is no login, tenant isolation or per-user secret vault. Keep the full backend on loopback; set `ENABLE_LOCAL_SETTINGS=false` for administrator-managed remote installations and add appropriate security before exposing it.
- Character continuity uses profiles and reference images, not a newly trained consistency model. Face/hand/prop protection depends on visual-model judgment and may miss objects.
- ChatGPT style/size instructions are prompt constraints, not guaranteed inference seeds or sampling steps.
- Batch processing uses a local single-process scheduler. It is not a distributed production queue.
- Protocol tests use mock HTTP and deterministic handoff data. They do not prove image quality, real provider availability or successful paid generation.
- There is no full vector RAG; recent outlines and character records supply context.

```bash
python -m pip install -e '.[dev]'
python -m pytest -q
npm --prefix frontend ci
npm --prefix frontend run build
```

## Learn more / contribute

Most detailed guides are currently in Chinese: [model connections](docs/MODEL_CONNECTIONS.md), [setup](docs/SETUP.md), [user guide](docs/USER_GUIDE.md), [architecture](docs/ARCHITECTURE.md), [comparison](docs/COMPETITIVE_ANALYSIS.md), [contributing](CONTRIBUTING.md).

Use [issue templates](https://github.com/Seigi-91/comiccraft-ai/issues/new/choose) for bugs, provider compatibility or feature proposals. Include redacted reproduction steps; never attach API keys or private projects. Small contributions to documentation, reproducible samples and compatibility reports are welcome. English UI localization and real provider verification are still open work.

If the workflow helps you, a voluntary GitHub Star makes it easier to find again. Successful installs and specific feedback are just as valuable.

## License

Original code/docs: [MIT](LICENSE). Third-party skills, fonts, music and components retain their own licenses; see [THIRD_PARTY_NOTICES](THIRD_PARTY_NOTICES.md). Fictional AI-generated example images illustrate the workflow and are not a promise of exclusive rights or guaranteed model output.

## v2.2: traceable knowledge and manual ChatGPT ablations

The 24 role cards distinguish 16 educational/practitioner principles, 2 engineering precedents and 6 project policies. Each includes located evidence, applicability, limitations, original positive/negative examples and checks. See the [research ledger](knowledge/RESEARCH.md) and [card catalog](knowledge/CARD_CATALOG.md).

Role-filtered weighted lexical retrieval preserves one core card and adds only relevant specialist cards. Each generation task freezes the complete corpus; resuming that task retains its snapshot. This is local retrieval, not vector RAG or model training.

The [retrieval regression](benchmarks/KNOWLEDGE_EVALUATION.md) improved top-three hits from 21/24 to 24/24 on maintainer-written queries and removed irrelevant specialist filler on 6 negative queries. Small, non-independent cases do not establish comic quality gains.

Each agent's settings page now provides paired manual ChatGPT tasks, frozen prompts and diffs, JSON reply validation, per-dimension observations and delayed condition reveal. Use two fresh chats with the same displayed model; identity remains operator-declared. Download a separate reviewer bundle for limited blinding. No model API is called. [Protocol and limits](benchmarks/CHATGPT_AB_PROTOCOL.md). Real generation-effect evaluation remains pending.

Image consistency scores now require specific observations and bind to the final rendered image as well as panel/dialogue/effect state. Legacy numeric-only reviews are incomplete. [Peer research and adoption boundaries](docs/UPSTREAM_RESEARCH_2026-11-02.md).

## Novel adaptation and storyboard review

1. Open **小说改编 · 导入原著**, import TXT or Markdown, and select the excerpt, fidelity mode, panel count, and required facts. Import and chapter creation make no model calls.
2. Generate source-grounded character cards and review the outline. The workflow then prepares the storyboard and dialogue and pauses before image generation.
3. In **视觉参考与分镜草图**, lock character, scene, and prop references and attach up to three per panel. Review the action, inset shots, dialogue, and balloon positions, then confirm rendering.
4. Revise selected panels or adjust lettering separately. Later chapters from the same imported novel can carry over character settings and the preceding completed chapter’s final shot.

This workflow is available on `main`. The linked v2.5.1 installer downloads the tagged release. In the live *Wizard of Oz* trial, only the two selected panels changed. A subsequent lettering save took about 1.9 seconds and added no model calls. See the [validation record](benchmarks/VISUAL_WORKFLOW_VALIDATION.md).

Original text and provenance stay separate from existing chapters. Bubble editing, masked repair, production tools and chapter rollback remain available. Each task retains its source/settings snapshot. Limits: 300,000 characters per import, 2MB files, 8,000 characters per excerpt and 200 excerpts. This is a per-excerpt workflow, not automatic whole-book adaptation or a guarantee of fidelity. [Detailed guide](docs/NOVEL_ADAPTATION.md).

## Automatic ChatGPT connection (v2.5)

Use `Install-ComicCraft-Auto.cmd`, complete your own official ChatGPT sign-in, then verify and enable text/vision/images in Settings. The official Codex App Server returns structured results and native image artifacts automatically; API providers remain available. Existing handoff jobs can explicitly continue with an automatic provider.

**Live local setup: text, attached-image recognition and real image generation all passed.** This corrects v2.4's fixed-filename image check; the older failure record remains historical. Account access, limits and real artwork still need per-user checks. This is a cloud model connection, not an offline model or shared account.

Panels are checkpointed as they complete. Resume reuses only matching inputs/references; passed visual reviews are reused only while all evidence remains unchanged. No blind parallelization of sequential reference-dependent panels. [Setup and exact limits](docs/CODEX_CONNECTION.md) · [Peer/primary research](docs/AUTOMATION_RESEARCH_2026-11-02.md) · [Synthetic efficiency regression](benchmarks/AUTOMATION_EFFICIENCY.md).

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
- Configure text/vision and image providers independently. Use your own API services, ChatGPT handoff, or a combination.

These features support control and review; they do not guarantee visual consistency or make the project unique among comic tools.

## Choose how models run

Open **Creative Team & Settings** (the application UI currently uses Chinese labels: **创作团队与设置**).

| Setup | Text & vision panel | Image panel | What you do |
|---|---|---|---|
| ChatGPT handoff | ChatGPT | ChatGPT | Copy tasks/references to your own ChatGPT, paste JSON or upload images, then resume |
| Automated providers | API | API | Supply separate base URLs, model names and your own keys |
| Mixed | Either | Either | Use an API for writing and ChatGPT for images, or the reverse |

Text/vision uses OpenAI-compatible `/chat/completions`; visual review needs an image-capable model. Image generation uses `/images/generations`, reference-based generation uses multipart `/images/edits`. Masked editing also needs an editing-capable service. Native vendor-specific protocols need separate adapters.

Keys stay in the backend computer's `.env` and are not returned by the configuration endpoint. Settings writes are restricted to local access. You can keep an existing key by leaving its field empty, or explicitly clear it. Saving settings does **not** send a paid test or verify your provider's quota.

**ChatGPT handoff is manual collaboration, not a desktop-control API.** This project does not extract session credentials or provide model access/credits. The GitHub Pages demo uses pre-generated artwork and makes no AI calls. The complete app runs locally.

## Run locally

Requirements: Python 3.11+, Node.js 20+, Git. No GPU is required by the orchestration/editor itself; external or locally hosted models have their own requirements.

Windows:

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

Install a Chinese-capable font, such as Noto Sans CJK, and set `COMIC_FONT_PATH` if needed. A fresh install starts with an empty database. Example images are available in `outputs/rain-night-light/`; there is not yet a one-click import into the full editor.

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

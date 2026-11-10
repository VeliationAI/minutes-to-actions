# Minutes to Actions

**Paste a meeting transcript. Walk out with decisions, action items, and who owns what.**

Open-source meeting follow-through. Everyone takes notes — this extracts the actions.

Built & maintained by [Veliation AI](https://github.com/VeliationAI).

[![Live Demo](https://img.shields.io/badge/Live%20Demo-onrender-E8A838?style=flat-square)](https://minutes-to-actions-1z5n.onrender.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg?style=flat-square)](LICENSE)
[![CI](https://github.com/VeliationAI/minutes-to-actions/actions/workflows/ci.yml/badge.svg)](https://github.com/VeliationAI/minutes-to-actions/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-3776AB?style=flat-square)](https://www.python.org/downloads/)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg?style=flat-square)](CONTRIBUTING.md)

## Live demo

**https://minutes-to-actions-1z5n.onrender.com**

Hosted on Render in the **open-source** workspace. No install required.  
Free instances may sleep after idle (~30s cold start).

## Why this exists

Meetings produce walls of text. The useful residue is small:

- what was **decided**
- who **owns** the next step
- when it’s **due**
- what’s still **open**

Minutes to Actions turns transcripts into that residue — via CLI or a tiny web UI.

## Features

- **LLM extraction** — OpenAI-compatible APIs (`gpt-4o-mini` by default)
- **Offline mode** — heuristics when no API key (demos never break)
- **CLI + web** — same core extractor
- **Take it forward** — remind everyone, schedule a follow-up, save notes, or email the team (plus per-action quick actions)
- **Self-host ready** — `render.yaml` included

## Quick start

```bash
git clone https://github.com/VeliationAI/minutes-to-actions.git
cd minutes-to-actions
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

### Demo (no API key)

```bash
minutes demo
```

### CLI

```bash
minutes extract -f notes.txt
minutes extract -f notes.txt -F markdown -o actions.md
minutes extract -f notes.txt -F json
```

### Web

```bash
minutes serve
```

Open [http://127.0.0.1:8766](http://127.0.0.1:8766) → **Try sample** → **Extract actions**.

## Configuration

```bash
cp .env.example .env
```

| Variable | Default | Purpose |
|----------|---------|---------|
| `OPENAI_API_KEY` / `MINUTES_API_KEY` | — | API auth |
| `MINUTES_MODEL` | `gpt-4o-mini` | Chat model |
| `MINUTES_BASE_URL` | `https://api.openai.com/v1` | Compatible gateway |

## Deploy

Public Render blueprint in `render.yaml` (workspace: **open-source**):

```bash
uvicorn minutes.server:create_app --factory --host 0.0.0.0 --port $PORT
```

## Contributing

PRs welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) and the [Code of Conduct](CODE_OF_CONDUCT.md).

- Bug reports & ideas → [Issues](https://github.com/VeliationAI/minutes-to-actions/issues)
- Security → [SECURITY.md](SECURITY.md)
- Changelog → [CHANGELOG.md](CHANGELOG.md)

## License

[MIT](LICENSE) © Veliation AI

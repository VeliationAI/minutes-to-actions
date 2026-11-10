# Contributing to Minutes to Actions

Thanks for helping people leave meetings with clear next steps.

## Ways to contribute

- **Bugs** — open an issue with steps, expected vs actual, OS, and CLI vs web
- **Features** — open an issue first for non-trivial ideas
- **Docs** — clearer quick starts, screenshots, translations
- **Extraction** — better heuristics, prompts, or output formats
- **UI/UX** — keep the loop simple: paste → extract → take it forward

## Development setup

```bash
git clone https://github.com/VeliationAI/minutes-to-actions.git
cd minutes-to-actions
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

Smoke checks:

```bash
minutes version
minutes extract -f minutes/sample_transcript.txt --heuristic -F json
minutes demo
minutes serve   # http://127.0.0.1:8766
```

## Pull request guidelines

1. Keep PRs focused — one idea per PR when possible
2. Match existing style (ink/amber UI, typed Python, clipboard-first takeaways)
3. Don’t commit secrets or `.venv/`
4. Update `CHANGELOG.md` under **Unreleased** for user-facing changes
5. Link related issues

## Code of Conduct

Participation is governed by our [Code of Conduct](CODE_OF_CONDUCT.md).

## Questions

Open a [GitHub Issue](https://github.com/VeliationAI/minutes-to-actions/issues) — maintainers watch the tracker.

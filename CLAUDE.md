# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project does

An automated SEO content agent for a web agency. For each client site it pulls 90 days of Google Search Console query data, has Claude (Anthropic API) write an ~800-word Hebrew SEO blog post based on top queries and low-CTR opportunities, and saves the post as a Google Doc in a Drive folder. It runs nightly at 02:00 Israel time on Railway.

## Running

There is no build step, linter, or test suite. Plain Python 3 with four dependencies.

```bash
pip install -r requirements.txt
python agent.py       # run the full agent once, over all clients
python scheduler.py   # runs immediately, then daily at 02:00 Asia/Jerusalem
```

`agent.py` requires these environment variables (it crashes at import time if any is missing):

- `ANTHROPIC_API_KEY`
- `GOOGLE_REFRESH_TOKEN`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` — OAuth refresh-token flow for Search Console + Drive
- `DRIVE_FOLDER_ID` — destination Drive folder for generated docs

Deployment is Railway (`railway.json`, Nixpacks builder), start command `python scheduler.py`, restart on failure. Pushing to `main` is effectively deploying.

## Architecture

Two independent implementations of the same workflow — keep them in sync when changing clients or prompts:

1. **Backend (`agent.py` + `scheduler.py`)** — the production path. `agent.py` is a single-file pipeline: `get_token()` (OAuth refresh) → per client: `fetch_sc()` (Search Console top-50 queries by impressions) → `write_post()` (two Claude calls: one short call to pick a topic, one to write the post) → `save_drive()` (Drive **v2** multipart upload with `convert=true`, which converts plain text to a Google Doc). Errors are caught per client so one failing site doesn't stop the run. `scheduler.py` just wraps `run_agent()` with the `schedule` library.

2. **Frontend (`index.html`)** — a self-contained, zero-backend RTL Hebrew single-page tool that performs the same pipeline (Search Console → Claude → Drive) directly from the browser for a single, manually chosen client. Credentials are stored in `localStorage` under `aca_cfg`. It calls `api.anthropic.com` directly with an `x-api-key` header. `indexold.html` is a leftover stub; ignore it.

The **client list is duplicated** — `CLIENTS` in `agent.py` and the `<select id="cl">` options in `index.html` (which additionally carry a category key used for the seasonal-context `CTX` map). Adding/removing a client means editing both files.

## Key conventions

- **All generated content is Hebrew.** Prompts, niches, and UI text are Hebrew; the UI is RTL (`dir="rtl"`).
- `WRITING_RULES` in `agent.py` encodes hard content requirements (proper native Hebrew, no em-dashes, short sentences, exact word count). Don't weaken these when editing prompts; the frontend prompt in `runAll()` should stay consistent with them.
- Prompts embed a "current context" line (season/market conditions, e.g. "קיץ 2026"). This is hardcoded and goes stale — update it in both `agent.py` and the `BASE`/`CTX` arrays in `index.html` when touching prompt logic.
- The Claude model is pinned by string (`claude-sonnet-4-20250514`) in both `agent.py` and `index.html`.
- Drive upload deliberately uses the v2 upload API with `convert=true` and strips Markdown markers before saving, since the doc is created from plain text.
- Code style is intentionally terse/compact (single-file scripts, minimal abstraction, string concatenation over f-strings in `agent.py`). Match it rather than restructuring.

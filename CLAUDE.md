# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

Velho do Rio NG is a personal autonomous AI agent ("cyber-shaman" persona) for a single user. It runs in two independent modes:

- **SQS consumer** (`velhodorio.py`) — polls AWS SQS, processes WhatsApp and Telegram messages through the multi-agent team, replies back
- **AgentOS REST API** (`app.py`) — exposes the same team as a FastAPI server on port 7777 with SSE streaming

## Running the Project

All secrets are managed by Infisical — there is no `.env` file. Prefix every run with `infisical run --`:

```bash
# SQS consumer
infisical run -- python velhodorio.py

# REST API (AgentOS, port 7777)
infisical run -- python app.py

# Drain SQS queue (dev utility)
python limpa_fila.py
```

**Setup:**
```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
# For a new server, use the install scripts instead:
./setup_velhodorio.sh      # Python agent + systemd
./setup_mcp_reclaim.sh     # Node.js Reclaim MCP server
```

**Production (systemd):**
```bash
journalctl -u velhodorio -f
journalctl -u velhodorio-agentos -f
```

There are no tests, no linter config, and no CI.

## Architecture

### Agent Team (Agno v2 framework)

The orchestrator is `Velho do Rio` (Team leader), defined in `velhodorio.py` and `app.py`. It delegates to four specialist agents:

| Agent | File | Domain | External Tools |
|---|---|---|---|
| Agendador | `agents/agendador.py` | Calendar, tasks, Jira | MCP_AGENDADOR (SSE), RECLAIM_URL (streamable-http), GoogleCalendarTools |
| Financas | `agents/financas.py` | Crypto, CoinMarketCap | MCP_FINANCEIRO (SSE) |
| Pesquisador | `agents/pesquisador.py` | Web search | MCP_ESCAVADOR (SSE), DuckDuckGoTools |
| Terapeuta | `agents/terapeuta.py` | Emotional support | Qdrant RAG via Gemini embeddings (collection: `rag_terapeuta`) |

The orchestrator's own tools (not delegated):
- `tools/music_tools.py` — fuzzy query against MongoDB Discogs collection at `192.168.68.38:27017`
- `tools/hackernews.py` — Hacker News Firebase API
- `tools/ponto.py` — POST to n8n webhook to register work clock-in/out

All agents use `openai/gpt-4o-mini` via OpenRouter, defined in `agents/models.py`.

### MCP Servers

MCPs are connected individually at startup via a `_connect()` helper. If any MCP is offline, that agent gets `None` for that tool and the team still starts (graceful degradation).

- All MCPs use SSE transport **except** Reclaim, which uses `streamable-http`
- The n8n MCP workflows are exported in `mcpvelhodoriong.json`

### Messaging

`tools/messenger.py` routes replies:
- `send_evolution()` / `send_audio_evolution()` — WhatsApp via Evolution API
- `send_telegram()` / `send_audio_telegram()` — Telegram Bot API
- `dispatch()` — prefers audio when available, falls back to text

### Persistence

At startup, if `POSTGRES_URL + POSTGRES_USER + POSTGRES_PASS` are present in Infisical, PostgreSQL is used. Otherwise falls back to SQLite (`velho_rio.db`). Credentials are injected into the URL at runtime to avoid log exposure.

## Key Gotchas

- **No `reload=True` with AgentOS** — `app.py` explicitly forbids it; it breaks the MCP lifespan management
- **Timestamp threading in ponto.py** — uses `ContextVar` (`CURRENT_MESSAGE_DATE_TIME`). Call `set_current_message_date_time()` before `arun()` and `reset_current_message_date_time()` in a `finally` block
- **Hardcoded internal addresses** — MongoDB (`192.168.68.38:27017`) and the n8n webhook URL (`automation.cybernetus.com/webhook/registrar_ponto`) are hardcoded; only their credentials come from env vars
- **Google Calendar OAuth** — requires `credentials.json` and `token.json` in the project root (both gitignored); must be set up manually before the Agendador agent can use Google Calendar
- **PostgreSQL scheme coercion** — the connection string is forced to `postgresql+psycopg://` in code regardless of the value in `POSTGRES_URL`

# Vaca Muerta Dashboard

Interactive analytics dashboard for Argentina's **Vaca Muerta** shale formation — drilling, completions, frac treatments, and production data, with an AI-powered SQL copilot.

Built with [Taipy](https://taipy.io), pandas, and Python 3.12.

## Features

- **Overview** — KPIs for production, drilling, and frac activity with interactive filters
- **Geology** — Depth distributions and stratigraphic context
- **Drilling** — Wells and meters drilled by year and company
- **Frac Diagnostics** — Treatment intensity vs. production crossplots
- **Production** — Monthly time series, top wells by cumulative volume
- **Map** — Spatial scatter plot of wells, color-coded by oil/gas metric
- **Well Explorer** — Single-well deep dive (production history + frac details)
- **Data Explorer** — Filtered data tables with CSV download
- **Chat (SQL Copilot)** — LLM-powered assistant with read-only SQL, schema-aware RAG, and web search

## Quick Start

### Local (uv)

```bash
# Install uv (if needed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync

# Run the app
uv run app.py
```

Open `http://localhost:5000`. Change the port with `PORT=8080 uv run app.py`.

### Docker

```bash
docker build -t vm-app .
docker run --rm -p 5000:5000 \
  -e OPENROUTER_API_KEY="your_key" \
  vm-app
```

## Configuration

All settings are via environment variables — no secrets in code or config files.

| Variable | Default | Description |
| --- | --- | --- |
| `PORT` | `5000` | Server port |
| `OPENROUTER_API_KEY` | — | Required for chat. Can also be set in the UI |
| `OPENROUTER_MODEL` | `openai/gpt-4.1-mini` | LLM model for chat |
| `TAVILY_API_KEY` | — | Optional. Enables web search in chat |
| `VM_CHAT_DEBUG` | off | Set to `1` for verbose chat logging |
| `LOG_LEVEL` | `WARNING` | Python log level |
| `VM_OPENROUTER_TIMEOUT_SECONDS` | `25` | LLM request timeout |
| `VM_OPENROUTER_MAX_TOKENS` | `1024` | Max LLM output tokens |
| `VM_MAX_SQL_TOOL_LOOPS` | `3` | Max tool-calling iterations per chat turn |
| `VM_WEB_SEARCH_TIMEOUT_SECONDS` | `12` | Web search timeout |
| `VM_WEB_SEARCH_MAX_RESULTS` | `5` | Number of web search results |

## Chat / SQL Copilot

The **Chat** page provides an LLM assistant (via [OpenRouter](https://openrouter.ai)) that can:

- Execute read-only SQL against local tables (`prod`, `frac`, `drill`, `completion`)
- Retrieve schema and domain context via RAG
- Search the web via [Tavily](https://tavily.com) (optional)

API keys can be set as environment variables or pasted directly in the chat panel (session-only, never stored to disk).

## Data Refresh

Source data comes from Argentina's [Energy Ministry open data portal](http://datos.energia.gob.ar). The refresh script downloads raw CSVs, applies transformations (column mapping, unit conversion, filtering to Vaca Muerta), and writes the processed files used by the dashboard.

```bash
# Full refresh (download + transform)
uv run python scripts/refresh_data.py

# Download raw files only
uv run python scripts/refresh_data.py --download-only

# Rebuild processed CSVs from existing raw files
uv run python scripts/refresh_data.py --transform-only
```

To automate, add a cron job (e.g., daily at 06:00):

```bash
0 6 * * * cd /path/to/vm_app && uv run python scripts/refresh_data.py >> /tmp/vm_app_refresh.log 2>&1
```

If CSVs are refreshed while the app is running, open the **Data Explorer** page and click **Reload Data & SQL Cache** to pick up the new data without restarting.

## Debugging

Verbose chat logs:

```bash
VM_CHAT_DEBUG=1 LOG_LEVEL=INFO uv run app.py
```

CLI chat (no UI):

```bash
uv run python scripts/debug_chat.py --debug "count rows in prod"
```

## Data Sources

All data is sourced from Argentina's Secretary of Energy open datasets at [datos.energia.gob.ar](http://datos.energia.gob.ar). The dashboard processes five raw datasets into four app-ready CSVs covering production, frac treatments, drilling activity, and well completions for the Vaca Muerta formation.

## License

This project is for educational and analytical purposes. Data is publicly available from the Argentine government.

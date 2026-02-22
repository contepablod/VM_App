# Vaca Muerta Dashboard

## Run with uv (recommended)

1. Install `uv`:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

2. Sync dependencies:

```bash
uv sync
```

If you previously created a Python 3.13 virtual environment, recreate with 3.12:

```bash
rm -rf .venv
uv venv --python 3.12
uv sync
```

3. Run the app:

```bash
uv run app.py
```

The app is available at `http://localhost:5000`.

## Optional: custom port

```bash
PORT=8080 uv run app.py
```

Then open `http://localhost:8080`.

## SQL Copilot Chat (OpenRouter + SQL tools)

The app now includes a **Chat** page that can query the local SQLite cache with read-only SQL tool calling.
You can paste your OpenRouter API key directly in the chat panel (`OpenRouter API Key` field).

Set your OpenRouter key before running:

```bash
export OPENROUTER_API_KEY="your_key_here"
```

Optional model override:

```bash
export OPENROUTER_MODEL="openai/gpt-4.1-mini"
```

Then run the app and open the **🤖 CHAT** page from the sidebar.

## Chat debugging (Docker + CLI)

Enable verbose chat logs:

```bash
VM_CHAT_DEBUG=1 LOG_LEVEL=INFO uv run app.py
```

Run one chat question directly from CLI (no UI):

```bash
OPENROUTER_API_KEY="your_key_here" uv run python scripts/debug_chat.py --debug "count rows in prod"
```

Docker with verbose logs:

```bash
docker build -t vm-app .
docker run --rm -p 5000:5000 \
  -e OPENROUTER_API_KEY="your_key_here" \
  -e VM_CHAT_DEBUG=1 \
  -e LOG_LEVEL=INFO \
  -e VM_OPENROUTER_MAX_TOKENS=512 \
  -e VM_OPENROUTER_TIMEOUT_SECONDS=15 \
  -e VM_MAX_SQL_TOOL_LOOPS=1 \
  vm-app
```

## Docker

```bash
docker build -t vm-app .
docker run --rm -p 5000:5000 vm-app
```

## Refresh datasets automatically

The script below downloads the latest raw CSV files from:
- `http://datos.energia.gob.ar/dataset/c846e79c-026c-4040-897f-1ad3543b407c/resource/b5b58cdc-9e07-41f9-b392-fb9ec68b0725/download/produccin-de-pozos-de-gas-y-petrleo-no-convencional.csv`
- `http://datos.energia.gob.ar/dataset/71fa2e84-0316-4a1b-af68-7f35e41f58d7/resource/2280ad92-6ed3-403e-a095-50139863ab0d/download/datos-de-fractura-de-pozos-de-hidrocarburos-adjunto-iv-actualizacin-diaria.csv`
- `http://datos.energia.gob.ar/dataset/7ea2ac77-d7a0-4129-9fbf-6f1a25d94e21/resource/712805f3-35d4-4825-93c6-98d03aeca203/download/metros-perforados.csv`
- `http://datos.energia.gob.ar/dataset/7ea2ac77-d7a0-4129-9fbf-6f1a25d94e21/resource/af6838ef-f675-4409-ac6a-e7c391a5dbab/download/pozos-en-perforacin.csv`
- `http://datos.energia.gob.ar/dataset/7ea2ac77-d7a0-4129-9fbf-6f1a25d94e21/resource/a2ce14af-5c56-45c2-9b9c-c7a1e5156dff/download/pozos-terminados.csv`

Then it rebuilds:
- `data/well_prod_data.csv`
- `data/well_frac_data.csv`
- `data/drill_data.csv`
- `data/completion_data.csv`

For `--transform-only`, it expects these local raw files for drilling/completion transformations:
- `data/pozos-en-perforacin.csv`
- `data/metros-perforados.csv`
- `data/pozos-terminados.csv`

Run full refresh:

```bash
uv run python scripts/refresh_data.py
```

Only download raw files:

```bash
uv run python scripts/refresh_data.py --download-only
```

Only rebuild processed files from local raw files:

```bash
uv run python scripts/refresh_data.py --transform-only
```

Optional automation with cron (daily at 06:00):

```bash
0 6 * * * cd /home/pdconte/Desktop/vm_app && /usr/bin/env UV_CACHE_DIR=/tmp/uv-cache uv run python scripts/refresh_data.py >> /tmp/vm_app_refresh.log 2>&1
```

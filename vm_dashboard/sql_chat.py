import json
import logging
import os
import re
import sqlite3
import time
from pathlib import Path
from urllib import error as urlerror
from urllib import request as urlrequest

import pandas as pd

from . import state_data
from .state_data import (
    CHAT_WELCOME_TEXT,
    DATA_PATH_COMP,
    DATA_PATH_DRILL,
    DATA_PATH_FRAC,
    DATA_PATH_PROD,
    MAX_AGENT_HISTORY,
    MAX_SQL_RESULT_ROWS,
    MAX_SQL_TOOL_LOOPS,
    OPENROUTER_API_URL,
    OPENROUTER_DEFAULT_MODEL,
    OPENROUTER_MAX_TOKENS,
    OPENROUTER_TIMEOUT_SECONDS,
    SQLITE_DB_PATH,
    TAVILY_SEARCH_API_URL,
    WEB_SEARCH_MAX_RESULTS,
    WEB_SEARCH_TIMEOUT_SECONDS,
)

_sql_db_status = "SQLite not initialized"
_LOGGER = logging.getLogger("vm_dashboard.chat")


def _chat_welcome_message():
    return CHAT_WELCOME_TEXT


def _chat_debug_enabled():
    return os.getenv("VM_CHAT_DEBUG", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _debug(msg, *args):
    if _chat_debug_enabled():
        _LOGGER.info(msg, *args)


def _mask_secret(value):
    value = str(value or "")
    if len(value) <= 8:
        return "***"
    return f"{value[:4]}...{value[-4:]}"


def _tokenize(text):
    return set(re.findall(r"[a-zA-Z_]{2,}", str(text).lower()))


def _build_rag_docs():
    return [
        (
            "Table `prod` has monthly production metrics by well. Key columns: year, month, "
            "well_id, well_name, company, field, well_type, oil_prod_m3, gas_prod_km3, "
            "water_prod_m3, oil_cum_m3, gas_cum_km3, water_prod_cum_m3, depth, Xcoor, Ycoor."
        ),
        (
            "Table `frac` has completion/fracture treatment attributes by well. Key columns: "
            "well_id, well_name, company, field, year, month, frac_start_date, frac_end_date, "
            "lateral_length_ft, number_stages, proppant_pumped_lb, fluid_pumped_bbl, "
            "maximum_pressure_psi, horse_power_hp."
        ),
        (
            "Table `drill` has drilling activity by company and field. Key columns: year, month, "
            "company, field, basin, location, concept, wells, meters."
        ),
        (
            "Table `completion` has well completion counts by company and field. Key columns: "
            "year, month, company, field, basin, location, concept, completion."
        ),
        (
            "Join guidance: use `well_id` for prod-frac joins; use `company`, `field`, `year`, "
            "and optionally `month` for drill/completion rollups."
        ),
        (
            "Units: oil is m3 in prod and cumulative m3 in oil_cum_m3; gas is km3 in prod and "
            "gas_cum_km3; drill meters are in `meters`; frac lateral length is in feet."
        ),
    ]


RAG_DOCS = _build_rag_docs()


def _retrieve_context(query, top_k=4):
    try:
        top_k = int(top_k)
    except (TypeError, ValueError):
        top_k = 4
    top_k = max(1, min(top_k, 8))
    q_tokens = _tokenize(query)
    scored = []
    for doc in RAG_DOCS:
        overlap = len(q_tokens & _tokenize(doc))
        scored.append((overlap, doc))
    scored.sort(key=lambda x: x[0], reverse=True)
    selected = [doc for _, doc in scored[:top_k]]
    return "\n\n".join(f"[Context {i + 1}] {doc}" for i, doc in enumerate(selected))


def _build_sqlite_db():
    state_data.ensure_data_loaded()
    db_path = Path(SQLITE_DB_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(db_path) as conn:
        state_data.prod.to_sql("prod", conn, if_exists="replace", index=False)
        state_data.frac.to_sql("frac", conn, if_exists="replace", index=False)
        state_data.drill.to_sql("drill", conn, if_exists="replace", index=False)
        state_data.comp.to_sql("completion", conn, if_exists="replace", index=False)

        conn.execute("CREATE INDEX IF NOT EXISTS idx_prod_well_id ON prod(well_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_prod_year ON prod(year)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_prod_company ON prod(company)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_frac_well_id ON frac(well_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_frac_year ON frac(year)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_frac_company ON frac(company)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_drill_year ON drill(year)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_drill_company ON drill(company)")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_completion_year ON completion(year)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_completion_company ON completion(company)"
        )


def _sqlite_is_stale():
    db_path = Path(SQLITE_DB_PATH)
    if not db_path.exists():
        return True
    db_mtime_ns = db_path.stat().st_mtime_ns
    source_paths = [DATA_PATH_PROD, DATA_PATH_FRAC, DATA_PATH_DRILL, DATA_PATH_COMP]
    for source in source_paths:
        p = Path(source)
        if p.exists() and p.stat().st_mtime_ns > db_mtime_ns:
            return True
    return False


def ensure_sqlite_db(force=False):
    global _sql_db_status
    try:
        state_data.ensure_data_loaded(force=force)
        if force or _sqlite_is_stale():
            _debug("Rebuilding SQLite cache at %s (force=%s)", SQLITE_DB_PATH, force)
            _build_sqlite_db()
        _sql_db_status = f"SQLite ready ({SQLITE_DB_PATH})"
        _debug("SQLite cache ready: %s", SQLITE_DB_PATH)
        return True
    except Exception as exc:
        _sql_db_status = f"SQLite error: {exc}"
        _LOGGER.exception("SQLite cache error")
        return False


def get_sqlite_db_status():
    return _sql_db_status


def _validate_read_only_sql(query):
    if query is None:
        return False, "SQL query is missing."

    q = str(query).strip()
    if not q:
        return False, "SQL query is empty."

    if ";" in q.rstrip(";"):
        return False, "Multiple SQL statements are not allowed."

    q_no_semicolon = q.rstrip(";").strip()
    lowered = q_no_semicolon.lower()

    if re.search(
        r"\b(insert|update|delete|drop|alter|create|replace|attach|detach|vacuum|truncate|reindex)\b",
        lowered,
    ):
        return False, "Only read-only SQL is allowed."

    if not (
        lowered.startswith("select")
        or lowered.startswith("with")
        or lowered.startswith("pragma table_info")
    ):
        return False, "Only SELECT/CTE/PRAGMA table_info queries are allowed."

    return True, q_no_semicolon


def _execute_read_only_sql(query):
    ok, payload = _validate_read_only_sql(query)
    if not ok:
        return {"ok": False, "error": payload}

    user_query = payload
    lowered = user_query.lower()
    execute_query = user_query

    if not lowered.startswith("pragma table_info"):
        execute_query = f"SELECT * FROM ({user_query}) AS _q LIMIT {MAX_SQL_RESULT_ROWS}"

    try:
        with sqlite3.connect(SQLITE_DB_PATH) as conn:
            df = pd.read_sql_query(execute_query, conn)
    except Exception as exc:
        return {"ok": False, "error": str(exc), "query": user_query}

    rows = df.to_dict(orient="records")
    return {
        "ok": True,
        "query": user_query,
        "executed_query": execute_query,
        "row_count": len(df),
        "columns": df.columns.tolist(),
        "rows": rows,
        "truncated": len(df) >= MAX_SQL_RESULT_ROWS,
    }


def _tool_search_knowledge(query, top_k=4):
    return {"ok": True, "context": _retrieve_context(query, top_k=top_k)}


def _resolve_openrouter_api_key(state):
    ui_key = str(getattr(state, "openrouter_api_key_input", "") or "").strip()
    if ui_key:
        return ui_key, "UI input"

    env_value = os.getenv("OPENROUTER_API_KEY", "").strip()
    if env_value:
        return env_value, "env var"

    return "", "missing"


def _resolve_web_search_api_key(state):
    ui_key = str(getattr(state, "web_search_api_key_input", "") or "").strip()
    if ui_key:
        return ui_key, "UI input"

    env_value = os.getenv("TAVILY_API_KEY", "").strip()
    if env_value:
        return env_value, "env var"

    return "", "missing"


def _tool_web_search(query, api_key, max_results=WEB_SEARCH_MAX_RESULTS):
    if not api_key:
        return {
            "ok": False,
            "error": "Web search API key is missing. Set TAVILY_API_KEY or provide it in Chat.",
        }

    q = str(query or "").strip()
    if not q:
        return {"ok": False, "error": "Search query is empty."}

    try:
        max_results = int(max_results)
    except (TypeError, ValueError):
        max_results = WEB_SEARCH_MAX_RESULTS
    max_results = max(1, min(max_results, 10))

    payload = {
        "api_key": api_key,
        "query": q,
        "search_depth": "basic",
        "max_results": max_results,
        "include_answer": False,
        "include_raw_content": False,
    }
    request = urlrequest.Request(
        TAVILY_SEARCH_API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urlrequest.urlopen(request, timeout=WEB_SEARCH_TIMEOUT_SECONDS) as response:
            body = response.read().decode("utf-8")
            parsed = json.loads(body)
    except urlerror.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="ignore")
        return {"ok": False, "error": f"Web search HTTP {exc.code}: {details[:500]}"}
    except urlerror.URLError as exc:
        return {"ok": False, "error": f"Web search connection error: {exc.reason}"}
    except Exception as exc:
        return {"ok": False, "error": f"Web search error: {exc}"}

    results = []
    for item in parsed.get("results", [])[:max_results]:
        title = str(item.get("title", "") or "").strip()
        url = str(item.get("url", "") or "").strip()
        content = str(item.get("content", "") or "").strip()
        if content:
            content = content[:500]
        if not (title or url or content):
            continue
        results.append(
            {
                "title": title,
                "url": url,
                "snippet": content,
                "score": item.get("score"),
                "published_date": item.get("published_date"),
            }
        )

    return {
        "ok": True,
        "query": q,
        "source_count": len(results),
        "sources": results,
    }


def _openrouter_headers(api_key):
    if not api_key:
        raise RuntimeError("OpenRouter API key is not set.")

    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": os.getenv("OPENROUTER_HTTP_REFERER", "http://localhost"),
        "X-Title": "Vaca Muerta SQL Copilot",
    }


def _call_openrouter(messages, tools, model_name, api_key):
    payload = {
        "model": model_name,
        "messages": messages,
        "tools": tools,
        "tool_choice": "auto",
        "temperature": 0.1,
        "max_tokens": OPENROUTER_MAX_TOKENS,
    }
    start_time = time.perf_counter()
    _debug(
        "OpenRouter request start model=%s messages=%s tools=%s timeout=%ss max_tokens=%s key=%s",
        model_name,
        len(messages),
        len(tools),
        OPENROUTER_TIMEOUT_SECONDS,
        OPENROUTER_MAX_TOKENS,
        _mask_secret(api_key),
    )

    request = urlrequest.Request(
        OPENROUTER_API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers=_openrouter_headers(api_key),
        method="POST",
    )

    try:
        with urlrequest.urlopen(request, timeout=OPENROUTER_TIMEOUT_SECONDS) as response:
            body = response.read().decode("utf-8")
            parsed = json.loads(body)
            _debug(
                "OpenRouter response ok elapsed=%.2fs choices=%s",
                time.perf_counter() - start_time,
                len(parsed.get("choices", [])),
            )
            return parsed
    except urlerror.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="ignore")
        _LOGGER.error(
            "OpenRouter HTTP error status=%s elapsed=%.2fs body=%s",
            exc.code,
            time.perf_counter() - start_time,
            details[:500],
        )
        raise RuntimeError(f"OpenRouter HTTP {exc.code}: {details}") from exc
    except urlerror.URLError as exc:
        _LOGGER.error(
            "OpenRouter URL error elapsed=%.2fs reason=%s",
            time.perf_counter() - start_time,
            exc.reason,
        )
        raise RuntimeError(f"OpenRouter connection error: {exc.reason}") from exc


def _parse_tool_args(raw_args):
    if isinstance(raw_args, dict):
        return raw_args
    if not raw_args:
        return {}
    try:
        return json.loads(raw_args)
    except json.JSONDecodeError:
        return {}


def _sql_agent_system_prompt():
    return (
        "You are a SQL analytics copilot for a Vaca Muerta dashboard. "
        "Use tools to answer with verified numbers. "
        "When a question needs data, call `run_sql`. "
        "For schema/domain understanding, call `search_knowledge`. "
        "For current events, external context, or anything outside local tables, call `web_search`. "
        "Never invent values. If data is unavailable, say so clearly. "
        "Keep answers concise and include units when relevant. "
        "When using web_search, cite source URLs."
    )


def _run_sql_agent(question, model_name, api_key, history=None, web_search_api_key=""):
    _debug(
        "SQL agent start model=%s question_len=%s history_len=%s",
        model_name,
        len(str(question)),
        len(history or []),
    )
    if not ensure_sqlite_db():
        return {
            "ok": False,
            "answer": "SQLite database is not available. Please rebuild the SQL cache.",
            "last_sql_query": "",
            "last_sql_rows": [],
            "history": list(history or []),
        }

    model_name = (model_name or OPENROUTER_DEFAULT_MODEL).strip() or OPENROUTER_DEFAULT_MODEL
    context = _retrieve_context(question, top_k=4)
    history = list(history or [])[-MAX_AGENT_HISTORY:]

    messages = [{"role": "system", "content": _sql_agent_system_prompt()}]
    messages.extend(history)
    messages.append(
        {
            "role": "user",
            "content": f"Question:\n{question}\n\nRetrieved context:\n{context}",
        }
    )

    tools = [
        {
            "type": "function",
            "function": {
                "name": "search_knowledge",
                "description": "Retrieve schema/domain context for the Vaca Muerta tables.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "top_k": {"type": "integer", "minimum": 1, "maximum": 8},
                    },
                    "required": ["query"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "run_sql",
                "description": (
                    "Execute read-only SQL on local SQLite tables: prod, frac, drill, completion."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                    "required": ["query"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "web_search",
                "description": (
                    "Search the public web for recent/external information and return source URLs."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "max_results": {"type": "integer", "minimum": 1, "maximum": 10},
                    },
                    "required": ["query"],
                },
            },
        },
    ]

    final_answer = None
    last_sql_query = ""
    last_sql_rows = []

    loop_limit = max(2, int(MAX_SQL_TOOL_LOOPS))
    if loop_limit != MAX_SQL_TOOL_LOOPS:
        _LOGGER.warning(
            "MAX_SQL_TOOL_LOOPS=%s is too low for tool-calling; using %s instead.",
            MAX_SQL_TOOL_LOOPS,
            loop_limit,
        )

    for loop_idx in range(loop_limit):
        response = _call_openrouter(messages, tools, model_name, api_key)
        assistant = response.get("choices", [{}])[0].get("message", {})
        assistant_content = assistant.get("content")
        tool_calls = assistant.get("tool_calls") or []
        _debug(
            "SQL agent loop=%s tool_calls=%s content_len=%s",
            loop_idx + 1,
            len(tool_calls),
            len(str(assistant_content or "")),
        )

        if tool_calls:
            messages.append(
                {
                    "role": "assistant",
                    "content": assistant_content or "",
                    "tool_calls": tool_calls,
                }
            )
            for tool_call in tool_calls:
                fn = tool_call.get("function", {})
                tool_name = fn.get("name", "")
                args = _parse_tool_args(fn.get("arguments", "{}"))

                if tool_name == "run_sql":
                    _debug("Tool run_sql called")
                    tool_result = _execute_read_only_sql(args.get("query"))
                    if tool_result.get("ok"):
                        last_sql_query = tool_result.get("query", "")
                        last_sql_rows = tool_result.get("rows", [])
                        _debug(
                            "run_sql ok rows=%s query=%s",
                            tool_result.get("row_count", 0),
                            str(last_sql_query)[:300],
                        )
                    else:
                        _LOGGER.warning(
                            "run_sql failed error=%s query=%s",
                            tool_result.get("error"),
                            str(tool_result.get("query", ""))[:300],
                        )
                elif tool_name == "search_knowledge":
                    _debug("Tool search_knowledge called")
                    tool_result = _tool_search_knowledge(
                        args.get("query", question),
                        top_k=args.get("top_k", 4),
                    )
                elif tool_name == "web_search":
                    _debug("Tool web_search called")
                    tool_result = _tool_web_search(
                        args.get("query", question),
                        api_key=web_search_api_key,
                        max_results=args.get("max_results", WEB_SEARCH_MAX_RESULTS),
                    )
                else:
                    _LOGGER.warning("Unknown tool requested by model: %s", tool_name)
                    tool_result = {"ok": False, "error": f"Unknown tool: {tool_name}"}

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.get("id", "tool_call"),
                        "name": tool_name or "unknown_tool",
                        "content": json.dumps(tool_result, ensure_ascii=False)[:8000],
                    }
                )
            continue

        final_answer = (
            assistant_content
            if isinstance(assistant_content, str)
            else str(assistant_content or "No answer was generated.")
        )
        messages.append({"role": "assistant", "content": final_answer})
        break

    if not final_answer:
        final_answer = "I could not complete the tool-calling loop. Try a simpler question."
        _LOGGER.warning("SQL agent finished without final answer after tool loops")

    new_history = (
        history
        + [{"role": "user", "content": question}]
        + [{"role": "assistant", "content": final_answer}]
    )[-MAX_AGENT_HISTORY:]
    return {
        "ok": True,
        "answer": final_answer,
        "last_sql_query": last_sql_query,
        "last_sql_rows": last_sql_rows,
        "history": new_history,
    }


def _run_sql_agent_job(question, model_name, api_key, history, web_search_api_key):
    try:
        return _run_sql_agent(
            question,
            model_name,
            api_key,
            history,
            web_search_api_key=web_search_api_key,
        )
    except Exception as exc:
        _LOGGER.exception("SQL agent job crashed")
        return {
            "ok": False,
            "answer": f"SQL copilot error: `{exc}`",
            "last_sql_query": "",
            "last_sql_rows": [],
            "history": list(history or []),
        }


def _append_chat_message(state, message, sender):
    messages = list(getattr(state, "chat_messages", []))
    message_id = f"m{int(time.time() * 1000)}_{len(messages)}"
    messages.append([message_id, str(message), sender])
    state.chat_messages = messages


def _normalize_message_text(value):
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        for key in ("text", "message", "content", "value", "prompt", "question"):
            v = value.get(key)
            if isinstance(v, str) and v.strip():
                return v.strip()
        return ""
    if value is None:
        return ""
    return str(value).strip()


def _extract_user_message(state, payload):
    if isinstance(payload, dict):
        args = payload.get("args", [])
        if isinstance(args, (list, tuple)):
            if len(args) > 2:
                msg = _normalize_message_text(args[2])
                if msg:
                    return msg
            for idx in (1, 0, 3):
                if len(args) > idx:
                    msg = _normalize_message_text(args[idx])
                    if msg:
                        return msg
        for key in ("message", "text", "content", "value", "prompt", "question"):
            msg = _normalize_message_text(payload.get(key))
            if msg:
                return msg

    messages = list(getattr(state, "chat_messages", []))
    if messages:
        last = messages[-1]
        if isinstance(last, (list, tuple)) and len(last) >= 3:
            sender = str(last[2])
            sender_id = str(getattr(state, "chat_sender_id", "user"))
            msg = _normalize_message_text(last[1])
            if msg and sender in ("user", sender_id):
                return msg

    return ""


def _is_latest_user_message(state, message):
    messages = list(getattr(state, "chat_messages", []))
    if not messages:
        return False
    last = messages[-1]
    if not isinstance(last, (list, tuple)) or len(last) < 3:
        return False
    sender = str(last[2])
    sender_id = str(getattr(state, "chat_sender_id", "user"))
    return sender in ("user", sender_id) and _normalize_message_text(last[1]) == message


def _update_chat_runtime_status(state):
    _, source = _resolve_openrouter_api_key(state)
    state.openrouter_key_status = (
        f"Configured ({source})" if source != "missing" else "Missing"
    )
    state.chat_input_active = not bool(getattr(state, "chat_busy", False))
    state.chat_runtime_status = "Running" if getattr(state, "chat_busy", False) else "Ready"
    state.sql_cache_status = get_sqlite_db_status()
    state.data_runtime_status = state_data.data_runtime_status


def on_chat_settings_change(state, var_name, var_value):
    if var_name in [
        "openrouter_api_key_input",
        "openrouter_model",
        "web_search_api_key_input",
    ]:
        _update_chat_runtime_status(state)


def on_chat_action(state, var_name, payload):
    _debug(
        "Chat action received var_name=%s payload_keys=%s",
        var_name,
        sorted(payload.keys()) if isinstance(payload, dict) else "n/a",
    )
    user_message = _extract_user_message(state, payload)
    if not user_message:
        _LOGGER.warning("Chat message extraction failed payload=%s", str(payload)[:500])
        _append_chat_message(
            state,
            "I could not read your message payload. Please retry.",
            "assistant",
        )
        return

    if getattr(state, "chat_busy", False):
        _LOGGER.warning("Chat request ignored because previous request is still running")
        _append_chat_message(
            state,
            "A previous request is still running. Please wait a few seconds.",
            "assistant",
        )
        return

    if not _is_latest_user_message(state, user_message):
        _append_chat_message(state, user_message, "user")
    _update_chat_runtime_status(state)

    api_key, api_key_source = _resolve_openrouter_api_key(state)
    if not api_key:
        _LOGGER.warning("Chat request rejected: OpenRouter API key missing")
        _append_chat_message(
            state,
            "Missing OpenRouter API key. Add it in the chat panel input and retry.",
            "assistant",
        )
        return

    model_name = (
        (state.openrouter_model or OPENROUTER_DEFAULT_MODEL).strip()
        or OPENROUTER_DEFAULT_MODEL
    )
    history = list(getattr(state, "sql_agent_history", []))[-MAX_AGENT_HISTORY:]
    web_search_api_key, web_search_key_source = _resolve_web_search_api_key(state)
    state.chat_busy = True
    _update_chat_runtime_status(state)
    _debug(
        "Chat request start model=%s key_source=%s web_key_source=%s key=%s question_len=%s history_len=%s",
        model_name,
        api_key_source,
        web_search_key_source,
        _mask_secret(api_key),
        len(user_message),
        len(history),
    )
    try:
        start_time = time.perf_counter()
        result = _run_sql_agent_job(
            user_message, model_name, api_key, history, web_search_api_key
        )
        _debug(
            "Chat request end elapsed=%.2fs ok=%s answer_len=%s",
            time.perf_counter() - start_time,
            bool(result.get("ok")) if isinstance(result, dict) else False,
            len(str(result.get("answer", ""))) if isinstance(result, dict) else 0,
        )
        on_chat_agent_done(state, True, result)
    except Exception as exc:
        state.chat_busy = False
        _LOGGER.exception("Chat execution failed")
        _append_chat_message(
            state,
            f"Chat execution failed: `{exc}`",
            "assistant",
        )
        _update_chat_runtime_status(state)


def on_chat_agent_done(state, status, result=None):
    # In Python, bool is a subclass of int. We only want periodic integer ticks.
    if isinstance(status, int) and not isinstance(status, bool):
        return

    state.chat_busy = False

    if status is True and isinstance(result, dict):
        answer = str(result.get("answer", "No answer was generated."))
        _debug(
            "Chat callback done status=%s answer_len=%s last_sql_len=%s",
            status,
            len(answer),
            len(str(result.get("last_sql_query", "") or "")),
        )
        _append_chat_message(state, answer, "assistant")
        state.sql_last_query = str(result.get("last_sql_query", "") or "")
        state.sql_last_result = pd.DataFrame(result.get("last_sql_rows", []) or [])
        history = result.get("history")
        if isinstance(history, list):
            state.sql_agent_history = history[-MAX_AGENT_HISTORY:]
    else:
        _LOGGER.warning("Chat callback failed status=%s result_type=%s", status, type(result))
        _append_chat_message(
            state,
            "SQL copilot failed due to a background callback error.",
            "assistant",
        )

    _update_chat_runtime_status(state)


def clear_chat(state):
    state.chat_messages = [["m0", _chat_welcome_message(), "assistant"]]
    state.sql_agent_history = []
    state.sql_last_query = ""
    state.sql_last_result = pd.DataFrame()
    state.chat_busy = False
    _update_chat_runtime_status(state)


def rebuild_sql_cache(state):
    state_data.ensure_data_loaded(force=True)
    ensure_sqlite_db(force=True)
    _update_chat_runtime_status(state)

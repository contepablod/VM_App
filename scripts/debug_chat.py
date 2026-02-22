import argparse
import logging
import os
import sys
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run one SQL chat request from CLI for debugging."
    )
    parser.add_argument(
        "question",
        nargs="+",
        help="Question to ask the SQL assistant.",
    )
    parser.add_argument(
        "--model",
        default=os.getenv("OPENROUTER_MODEL", "openai/gpt-4.1-mini"),
        help="OpenRouter model name.",
    )
    parser.add_argument(
        "--api-key",
        default="",
        help="OpenRouter API key (fallback: OPENROUTER_API_KEY env var).",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable verbose VM chat debug logs.",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    logging.basicConfig(
        level=logging.INFO if args.debug else logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    if args.debug:
        os.environ["VM_CHAT_DEBUG"] = "1"

    from vm_dashboard.sql_chat import _run_sql_agent_job, ensure_sqlite_db

    question = " ".join(args.question).strip()
    api_key = (args.api_key or os.getenv("OPENROUTER_API_KEY", "")).strip()

    if not question:
        print("error: question is empty", file=sys.stderr)
        return 2

    if not api_key:
        print("error: OPENROUTER_API_KEY is missing", file=sys.stderr)
        return 2

    print("[debug-chat] building/verifying sqlite cache...")
    if not ensure_sqlite_db():
        print("[debug-chat] sqlite cache failed to initialize", file=sys.stderr)
        return 3

    print(f"[debug-chat] model={args.model}")
    print(f"[debug-chat] question={question}")

    start = time.perf_counter()
    result = _run_sql_agent_job(question, args.model, api_key, history=[])
    elapsed = time.perf_counter() - start

    print(f"[debug-chat] elapsed={elapsed:.2f}s")
    print(f"[debug-chat] ok={result.get('ok')}")

    answer = str(result.get("answer", ""))
    last_sql = str(result.get("last_sql_query", "") or "")
    rows = result.get("last_sql_rows", []) or []

    print("\n=== ANSWER ===")
    print(answer)

    if last_sql:
        print("\n=== LAST SQL ===")
        print(last_sql)
        print(f"\n=== ROWS RETURNED ===\n{len(rows)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

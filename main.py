import asyncio
import json
import os
import sys
from dataclasses import dataclass
from typing import List
from rich.console import Console
from module.monitoring import start_monitoring, Settings, Account
from module.add_account import main as add_account_main


CONFIG_DIR = "config"
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
SEEN_FILE = os.path.join(CONFIG_DIR, "seen_users.json")
ACCOUNTS_FILE = os.path.join(CONFIG_DIR, "accounts.json")
PHRASES_FILE = os.path.join(CONFIG_DIR, "phrases.json")
STOP_WORDS_FILE = os.path.join(CONFIG_DIR, "stop_words.json")
WATCHLIST_FILE = os.path.join(CONFIG_DIR, "watchlist.json")


console = Console(width=80)

def load_json(path: str, default):
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def load_settings() -> Settings:
    raw = load_json(CONFIG_FILE, {})
    accounts_raw = load_json(ACCOUNTS_FILE, [])
    phrases_raw = load_json(PHRASES_FILE, {})
    stop_words_raw = load_json(STOP_WORDS_FILE, {})
    watchlist_raw = load_json(WATCHLIST_FILE, {})
    accounts = [Account(name=acc["name"], session_str=acc["session_str"]) for acc in accounts_raw]
    return Settings(
        bot_token=raw.get("bot_token", ""),
        admin_chat_id=raw.get("admin_chat_id", []),
        keywords=phrases_raw.get("keywords", []),
        stop_words=stop_words_raw.get("stop_words", []),
        watchlist=watchlist_raw.get("watchlist", []),
        accounts=accounts,
        api_id=raw.get("api_id", 0),
        api_hash=raw.get("api_hash", "")
    )

async def main():
    cfg = load_settings()
    
    if len(sys.argv) > 1 and sys.argv[1] == "add-account":
        await add_account_main(cfg.api_id, cfg.api_hash, ACCOUNTS_FILE)
    else:
        await start_monitoring(cfg, console, SEEN_FILE)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[bold yellow]Программа остановлена[/bold yellow]")
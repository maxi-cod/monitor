import asyncio
import html
import json
import logging
import os
import time
import requests
from dataclasses import dataclass, field
from typing import List, Optional, Set
from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.spinner import Spinner
from rich.text import Text
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.errors import SessionRevokedError, PhoneNumberBannedError
from telethon.tl.types import User


if os.name == "nt":
    console = Console(force_terminal=True, legacy_windows=True, width=80)
else:
    console = Console(width=80)


logging.getLogger("telethon").setLevel(logging.CRITICAL)


last_clear_time = time.time()


@dataclass
class Account:
    name: str
    session_str: str
    client: TelegramClient = field(init=False, default=None)

    async def connect(self, console, api_id: int, api_hash: str, account_number: int):
        try:
            self.client = TelegramClient(StringSession(self.session_str), api_id, api_hash)
            await self.client.start()
            me = await self.client.get_me()
            if me is None:
                console.log(f"[red]✗[/red] Аккаунт #{account_number} ({self.name}) не авторизован")
                return False
            username = f"@{me.username}" if me.username else "Нет юзернейма"
            console.log(f"[green]✓[/green] Аккаунт #{account_number}: {me.first_name or self.name} ({username})")
            return True
        except SessionRevokedError:
            console.log(f"[red]✗[/red] Сессия аккаунта #{account_number} ({self.name}) отозвана")
            return False
        except PhoneNumberBannedError:
            console.log(f"[red]✗[/red] Аккаунт #{account_number} ({self.name}) заблокирован")
            return False
        except Exception as e:
            console.log(f"[red]✗[/red] Ошибка авторизации аккаунта #{account_number} ({self.name}): {e}")
            return False

@dataclass
class Settings:
    bot_token: str
    admin_chat_id: List[int]
    keywords: List[str]
    stop_words: List[str]
    watchlist: List[int]
    accounts: List[Account]
    api_id: int
    api_hash: str


def load_json(path: str, default):
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def already_seen(uid: int, seen_file: str) -> bool:
    seen_cache = set(load_json(seen_file, []))
    return uid in seen_cache

def mark_seen(uid: int, seen_file: str):
    seen_cache = set(load_json(seen_file, []))
    if uid not in seen_cache:
        seen_cache.add(uid)
        with open(seen_file, "w", encoding="utf-8") as f:
            json.dump(list(seen_cache), f)

async def clear_seen_users_daily(console: Console, seen_file: str):
    global last_clear_time
    while True:
        current_time = time.time()
        if current_time - last_clear_time >= 86400:  
            with open(seen_file, "w", encoding="utf-8") as f:
                json.dump([], f)
            last_clear_time = current_time
            console.log("[green]Кэш seen_users очищен[/green]")
        await asyncio.sleep(3600)  

async def resolve_user_id(cfg: Settings, ident: str, console) -> Optional[int]:
    if ident.startswith("@"):
        if not cfg.accounts:
            console.print("[red]Нужен хотя бы один аккаунт для резолва username[/red]")
            return None
        client = TelegramClient(StringSession(cfg.accounts[0].session_str), cfg.api_id, cfg.api_hash)
        try:
            await client.connect()
            uid = await client.get_peer_id(ident)
            await client.disconnect()
            return uid
        except Exception as e:
            console.print(f"[red]Ошибка: {e}[/red]")
            return None
    try:
        return int(ident)
    except ValueError:
        console.print("[red]Некорректный id[/red]")
        return None

def notify(cfg: Settings, admin_msg: str, console: Console, parse_mode: str = "HTML"):
    for admin_id in cfg.admin_chat_id:
        url = f"https://api.telegram.org/bot{cfg.bot_token}/sendMessage"
        max_retries = 3
        retry_delay = 2  # секунды
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    url,
                    data={
                        "chat_id": admin_id,
                        "text": admin_msg,
                        "parse_mode": parse_mode,
                        "disable_web_page_preview": True
                    },
                    timeout=10
                )
                if response.status_code == 200:
                    return
                error_msg = response.json().get('description', 'Неизвестная ошибка')
                console.log(f"[red]Ошибка отправки админу {admin_id} (попытка {attempt+1}/{max_retries}): {error_msg}[/red]")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
            except Exception as e:
                console.log(f"[red]Не удалось отправить уведомление админу {admin_id} (попытка {attempt+1}/{max_retries}): {e}[/red]")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)

async def start_monitoring(cfg: Settings, console: Console, seen_file: str):
    if not cfg.bot_token or not cfg.admin_chat_id or not cfg.accounts or not cfg.api_id or not cfg.api_hash:
        console.print(Panel("[red]Сначала настройте аккаунты, бота, ID администраторов, API ID и API Hash.[/red]"))
        return

    valid_accounts = []
    for index, acc in enumerate(cfg.accounts, start=1):
        if await acc.connect(console, cfg.api_id, cfg.api_hash, index):
            valid_accounts.append(acc)
        else:
            console.print(f"[yellow]Пропущен аккаунт #{index} ({acc.name}): не авторизован или заблокирован[/yellow]")

    if not valid_accounts:
        console.print(Panel("[red]Нет доступных аккаунтов для мониторинга.[/red]"))
        return

    lowered_keywords = [k.lower() for k in cfg.keywords]
    lowered_stop_words = [s.lower() for s in cfg.stop_words]

    chat_count = 0
    chat_ids = set()
    for acc in valid_accounts:
        try:
            async for dialog in acc.client.iter_dialogs(archived=True):
                if dialog.is_group or dialog.is_channel:
                    chat_ids.add(dialog.entity.id)
        except Exception as e:
            console.print(f"[red]Ошибка при получении чатов для аккаунта {acc.name}: {e}[/red]")
    chat_count = len(chat_ids)

    def get_stats():
        return Text(f"Отслеживается чатов: {chat_count}", style="cyan")

    stats_text = get_stats()
    spinner = Spinner("dots", text="Слушаем…")
    live = Live(Panel(Group(stats_text, spinner), title="Статус"), refresh_per_second=4, console=console)
    live.start()

    
    asyncio.create_task(clear_seen_users_daily(console, seen_file))

    _processed_messages = set()
    _processed_lock = asyncio.Lock()

    async def handler(event, acc_name: str):
        if event.message.sender and getattr(event.message.sender, "bot", False):
            return
        try:
            if not event.is_group and not event.is_channel:
                return
            await event.mark_read()
            sender = await event.get_sender()
            sender_id = sender.id if sender else None
            if sender_id is None:
                return
            message_key = (event.chat_id, event.id)
            async with _processed_lock:
                if message_key in _processed_messages:
                    return
                _processed_messages.add(message_key)
            text = event.message.message or ""
            if not text:
                return
            
            if any(s in text.lower() for s in lowered_stop_words):
                return
            watch_hit = sender_id in cfg.watchlist
            keyword_hit = any(k in text.lower() for k in lowered_keywords)
            if not (watch_hit or keyword_hit) or (keyword_hit and already_seen(sender_id, seen_file)):
                return
            chat = await event.get_chat()
            chat_username = getattr(chat, "username", None)
            chat_id = event.chat_id
            if chat_username:
                message_link = f"https://t.me/{chat_username}/{event.id}"
            else:
                link_chat_id = str(chat_id).replace("-100", "-")
                message_link = f"https://t.me/c/{link_chat_id[1:]}/{event.id}"
            
            sender_username = getattr(sender, "username", None)
            if sender_username:
                contact = f"Контакт: @{sender_username}"
            else:
                sender_name = getattr(sender, "first_name", "Неизвестный")
                if isinstance(sender, User) and sender.last_name:
                    sender_name += f" {sender.last_name}"
                sender_name = html.escape(sender_name)
                contact = f"Контакт: <a href=\"tg://user?id={sender_id}\">{sender_name}</a>"
            
            admin_msg = f"Обнаружено аккаунтом: {html.escape(acc_name)}\n\n{html.escape(text)}\n\n{contact}\n\n<a href='{message_link}'>Ссылка на сообщение</a>"
            notify(cfg, admin_msg, console)
            if keyword_hit:
                mark_seen(sender_id, seen_file)
        except Exception as e:
            console.log(f"[red]Ошибка при обработке сообщения в чате {event.chat_id}: {e}[/red]")

    async def chat_action_handler(event, acc_name: str):
        nonlocal chat_count, chat_ids
        if event.created or event.user_joined or event.added_by:
            if event.is_group or event.is_channel:
                chat_id = event.chat_id
                if chat_id not in chat_ids:
                    chat_ids.add(chat_id)
                    chat_count = len(chat_ids)
                    live.update(Panel(Group(get_stats(), spinner), title="Статус"))

    for acc in valid_accounts:
        acc.client.add_event_handler(
            lambda e, n=acc.name: asyncio.create_task(handler(e, n)),
            events.NewMessage()
        )
        acc.client.add_event_handler(
            lambda e, n=acc.name: asyncio.create_task(chat_action_handler(e, n)),
            events.ChatAction()
        )

    console.print(Panel("[green]Мониторинг запущен![/green] Нажмите Ctrl+C для остановки.", title="Статус"))

    try:
        await asyncio.gather(*(acc.client.run_until_disconnected() for acc in valid_accounts))
    finally:
        live.stop()
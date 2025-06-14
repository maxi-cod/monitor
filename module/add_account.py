import asyncio
import json
import os
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError
from rich.console import Console
from rich.prompt import Prompt


console = Console(width=80)

async def add_account(api_id: int, api_hash: str, accounts_file: str):
    """Авторизует новый аккаунт и добавляет его в accounts.json."""
    phone = Prompt.ask("Введите номер телефона (в формате +1234567890)")
    client = TelegramClient(StringSession(), api_id, api_hash)
    
    try:
        await client.connect()
        await client.send_code_request(phone)
        code = Prompt.ask("Введите код авторизации, отправленный в Telegram")
        
        try:
            await client.sign_in(phone, code=code)
        except SessionPasswordNeededError:
            console.print("[yellow]Требуется пароль двухфакторной аутентификации[/yellow]")
            password = Prompt.ask("Введите пароль двухфакторной аутентификации", password=True)
            await client.sign_in(password=password)
        
        me = await client.get_me()
        session_str = client.session.save()
        account_name = me.username or me.first_name or phone
        account_data = {
            "name": account_name,
            "session_str": session_str
        }
        
        
        if os.path.exists(accounts_file):
            with open(accounts_file, "r", encoding="utf-8") as f:
                accounts = json.load(f)
        else:
            accounts = []
        
        
        if any(acc["session_str"] == session_str for acc in accounts):
            console.print(f"[yellow]Аккаунт {account_name} уже добавлен[/yellow]")
            return
        
        
        accounts.append(account_data)
        with open(accounts_file, "w", encoding="utf-8") as f:
            json.dump(accounts, f, ensure_ascii=False, indent=4)
        
        console.print(f"[green]Аккаунт {account_name} успешно добавлен[/green]")
    
    except Exception as e:
        console.print(f"[red]Ошибка авторизации: {e}[/red]")
    finally:
        await client.disconnect()

async def main(api_id: int, api_hash: str, accounts_file: str):
    """Основная функция для добавления аккаунтов."""
    while True:
        await add_account(api_id, api_hash, accounts_file)
        if not Prompt.ask("Добавить ещё один аккаунт? (y/n)", choices=["y", "n"], default="n") == "y":
            break
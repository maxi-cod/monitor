# Telegram Monitoring Script

Скрипт для мониторинга чатов Telegram, отслеживания ключевых слов и уведомления администраторов через Telegram API.

Репозиторий: [https://github.com/maxi-cod/monitor.git](https://github.com/maxi-cod/monitor.git)

## Требования

- Python 3.9
- Docker и Docker Compose (опционально)
- Telegram API ID и Hash
- Токен Telegram-бота

## Получение API ID и API Hash

1. Перейдите на [my.telegram.org](https://my.telegram.org).
2. Войдите с номером телефона Telegram-аккаунта.
3. Выберите **API development tools**.
4. Создайте приложение:
   - **App title**: любое название (например, "MonitorScript").
   - **Short name**: короткое имя (например, "Monitor").
   - **URL**: можно оставить пустым.
   - **Platform**: выберите "Desktop".
   - **Description**: необязательно.
5. Нажмите **Create application**.
6. Скопируйте **App api_id** и **App api_hash** в `config/config.json`.

**Важно**: Храните `api_hash` в тайне.

## Получение токена бота

1. Откройте Telegram и найдите [@BotFather](https://t.me/BotFather).
2. Напишите `/start` и `/newbot`.
3. Задайте имя и username бота.
4. Скопируйте токен в `config/config.json` (поле `bot_token`).

## Установка

1. **Клонируйте репозиторий**:
   ```bash
   git clone https://github.com/maxi-cod/monitor.git
   cd monitor
   ```

2. **Настройте конфигурацию**:
   - Отредактируйте файлы в папке `config/` (см. ниже).
   - Убедитесь, что файлы доступны для записи.

3. **Запуск**:
   - **С Docker (в фоне)**:
     ```bash
     docker-compose up -d --build
     ```
   - **Без Docker**:
     ```bash
     pip install -r requirements.txt
     python main.py
     ```
     Для запуска в фоне:
     ```bash
     nohup python main.py > monitor.log 2>&1 &
     ```

## Файлы конфигурации

Все файлы находятся в папке `config/`:

1. **`config.json`**:
   - Основные настройки скрипта.
   - Поля:
     - `bot_token`: Токен бота от @BotFather.
     - `admin_chat_id`: Список ID чатов администраторов (например, `[123456789]`). Получите ID через [@userinfobot](https://t.me/userinfobot).
     - `api_id`: Идентификатор приложения Telegram.
     - `api_hash`: Хэш приложения Telegram.
   - Пример:
     ```json
     {
         "bot_token": "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
         "admin_chat_id": [123456789],
         "api_id": 1234567,
         "api_hash": "abcdef1234567890abcdef1234567890"
     }
     ```

2. **`phrases.json`**:
   - Ключевые слова для мониторинга.
   - Поле `keywords`: Список фраз (например, `["ищу кодер", "нужен разраб"]`).
   - Пример:
     ```json
     {
         "keywords": ["ищу кодер", "нужен кодер", "нужен разраб"]
     }
     ```

3. **`accounts.json`**:
   - Список Telegram-аккаунтов.
   - Поля: `name` (имя аккаунта), `session_str` (строка сессии).
   - Заполняется при добавлении аккаунта.
   - Пример:
     ```json
     [
         {
             "name": "@username",
             "session_str": "1BQw..."
         }
     ]
     ```

4. **`seen_users.json`**:
   - Кэш ID просмотренных пользователей.
   - Создаётся/обновляется автоматически, очищается ежедневно.
   - Пример:
     ```json
     [123456789]
     ```

5. **`stop_words.json`**:
   - Стоп-слова для исключения сообщений.
   - Поле `stop_words`: Список слов/фраз (например, `["спам", "реклама"]`).
   - Пример:
     ```json
     {
         "stop_words": ["спам", "реклама"]
     }
     ```

6. **`watchlist.json`**:
   - Список ID пользователей для наблюдения.
   - Поле `watchlist`: Список ID (например, `[123456789]`).
   - Уведомления отправляются даже без ключевых слов.
   - Пример:
     ```json
     {
         "watchlist": [123456789]
     }
     ```

## Использование

### Добавление аккаунта

1. Запустите команду:
   ```bash
   docker-compose exec app python main.py add-account
   ```
   Или без Docker:
   ```bash
   python main.py add-account
   ```

2. Введите номер телефона, код авторизации (и пароль 2FA, если требуется).
3. Аккаунт сохраняется в `accounts.json`.

### Мониторинг

- Скрипт отслеживает чаты, в которых состоят аккаунты.
- Уведомляет администраторов при обнаружении ключевых слов или пользователей из `watchlist`.
- Стоп-слова фильтруют сообщения.
- Кэш `seen_users.json` сбрасывается ежедневно.

### Остановка

- С Docker:
  ```bash
  docker-compose down
  ```
- Без Docker: Найдите процесс (`ps aux | grep python`) и завершите (`kill <PID>`), или нажмите `Ctrl+C` в терминале.

## Структура проекта

```
├── config/
│   ├── config.json
│   ├── accounts.json
│   ├── phrases.json
│   ├── stop_words.json
│   ├── watchlist.json
│   ├── seen_users.json
├── module/
│   ├── add_account.py
│   ├── monitoring.py
├── Dockerfile
├── docker-compose.yml
├── main.py
├── requirements.txt
```

## Логирование

- Логи выводятся в консоль через `rich`.
- При запуске в фоне без Docker логи записываются в `monitor.log`.

## Примечания

- Проверяйте, что аккаунты не заблокированы.
- Храните конфиденциальные данные безопасно.
- Для большого числа чатов добавьте несколько аккаунтов.
- Если проблемы с my.telegram.org, отключите VPN или смените браузер.

## Лицензия

MIT License. См. файл `LICENSE`.

*Документация обновлена: 14 июня 2025, 20:55 (UTC+5).*

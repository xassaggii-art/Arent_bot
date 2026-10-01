# Arent Bot — уведомления о квартирах в Гюмри

Telegram-бот присылает **новые** объявления о продаже и аренде квартир в **Гюмри** с [List.am](https://www.list.am) (и опционально Facebook Marketplace). Логика похожа на [@BrokerBotAM_bot](https://t.me/BrokerBotAM_bot): выбираете категории — получаете алерты с ценой, локацией и ссылкой.

## Что уже сделано

- Подписки: долгая аренда, посуточная, продажа, вся недвижимость по Gyumri на List.am
- Дедупликация: при первом запуске «запоминает» текущие объявления, дальше шлёт только новые
- Обход Cloudflare List.am через [FlareSolverr](https://github.com/FlareSolverr/FlareSolverr) (как в [list_am_bot](https://github.com/zombiQWERTY/list_am_bot))
- Опциональный Facebook Marketplace (нужны cookies)

Parse.bot [List API](https://parse.bot/marketplace/71081b21-3c4d-459d-b602-358d7c6ef2e9/list-am-api) сейчас покрывает **авто**, не недвижимость — для квартир используем прямой парсинг HTML List.am.

## Быстрый старт

### 1. Telegram

1. Создайте бота через [@BotFather](https://t.me/BotFather), скопируйте `BOT_TOKEN`.
2. Узнайте свой `ADMIN_CHAT_ID` (например, [@userinfobot](https://t.me/userinfobot)).

### 2. Локально

```bash
cd "/Users/mimfm/Freelance projects/Arent_bot"
python3.11 -m venv .venv   # нужен Python 3.11+
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# отредактируйте .env

docker run -d --name flaresolverr -p 8191:8191 ghcr.io/flaresolverr/flaresolverr:latest

python -m app.main
```

### 3. Docker Compose (бот + FlareSolverr)

Сначала **запустите Docker Desktop** (иначе будет `Cannot connect to the Docker daemon`).

```bash
cp .env.example .env
# заполните BOT_TOKEN и ADMIN_CHAT_ID
docker compose up -d --build
```

### 4. Только List.am без Facebook (локально)

Facebook по умолчанию выключен (`FACEBOOK_ENABLED=false`).

```bash
# после запуска Docker Desktop — один раз FlareSolverr:
docker run -d --name arent_flaresolverr -p 8191:8191 --restart unless-stopped \
  ghcr.io/flaresolverr/flaresolverr:latest

chmod +x scripts/run-local.sh
./scripts/run-local.sh
```

## Настройка (.env)

| Переменная | Описание |
|------------|----------|
| `BOT_TOKEN` | Токен Telegram-бота |
| `ADMIN_CHAT_ID` | ID для служебных сообщений об ошибках |
| `FLARESOLVERR_URL` | URL FlareSolverr (по умолчанию `http://localhost:8191`) |
| `POLL_INTERVAL_SEC` | Интервал проверки, сек (по умолчанию 180) |
| `FACEBOOK_ENABLED` | `true` — включить Facebook |
| `FACEBOOK_COOKIE` | Cookie из браузера после входа в facebook.com |

## Facebook

Marketplace без авторизации часто отдаёт страницу входа. Скопируйте cookie из DevTools → Network → запрос к facebook.com → заголовок `Cookie` в `FACEBOOK_COOKIE`. Это хрупко: при истечении сессии обновите cookie.

## Категории List.am (Гюмри)

| Подписка | URL |
|----------|-----|
| Долгая аренда | `category/56?q=gyumri` |
| Посуточная | `category/166?q=gyumri` |
| Продажа квартир | `category/60?q=gyumri` |
| Вся недвижимость | `category/54?q=gyumri` |

Ссылки и сортировка «сначала новые» (`srt=3`) заданы в `app/models.py`.

## Структура

```
app/
  main.py           — запуск бота и мониторинга
  monitor.py        — периодический опрос источников
  scrapers/         — List.am и Facebook
  bot_handlers.py   — команды и кнопки Telegram
```

## Дальше (по желанию)

- Фильтры по цене и комнатам
- Несколько городов
- Webhook вместо polling для продакшена
- Parse.bot / свой scraper API, если появится недвижимость

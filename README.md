Trading Engine · Bybit Testnet

Легкий Python-двигун для демо-торгівлі деривативами на Bybit Testnet:

старт угоди з JSON-конфігом;

TP у % від середньої (автореплейс після усереднення);

«драбинка» лімітних ордерів для добору;

клієнтський SL / Trailing / Breakeven;

простий веб-UI та єдиний REST ендпоінт /.

Зміст

Вимоги

Швидкий старт (Docker)

Змінні оточення .env

Конфіг угоди (що заповнювати)

Користування UI та API

Як це працює

Траблшутінг

Налаштування ризику

Скріншоти

Безпека

Вимоги

Docker і Docker Compose

Обліковка Bybit Demo (Testnet) з USDT у Unified Trading

Швидкий старт (Docker)

Створи Testnet API-ключ у Bybit: Demo → Create New Key → API Transaction. Дай права Orders і Positions в Unified Trading / Contract.

Заповни .env у корені репозиторію. Є приклад у .env_sample.

Запусти контейнер: docker compose up --build -d.

Відкрий http://localhost:8000/. Якщо у статусі free_usdt: 0 — зроби Assets → Transfer з Funding у Unified Trading (USDT).

Натисни Start from file і підвантаж свій config.json.

Змінні оточення .env

BYBIT_API_KEY — твій testnet API key

BYBIT_SECRET — твій testnet API secret

MARKET_TYPE — тип ринку для ccxt, використовуй swap

POLL_INTERVAL — період моніторингу в секундах (наприклад 2.0)

Не коміть реальні ключі. Для продакшена — IP-обмеження, окремі креденшли, обережний мані-менеджмент.

Конфіг угоди (що заповнювати)

Використовуй деривативний символ (наприклад BTC/USDT:USDT).
Поля конфігу:

account — довільна назва (напр. Bybit/Testnet);

symbol — ринок (напр. BTC/USDT:USDT);

side — long або short;

market_order_amount — ноціонал входу в USDT;

limit_orders_amount — загальний бюджет на драбинку (USDT);

leverage — плече;

stop_loss_percent, trailing_sl_offset_percent, move_sl_to_breakeven — параметри захисту;

tp_orders — масив рівнів TP (кожен має price_percent і quantity_percent);

limit_orders.range_percent, limit_orders.orders_count, limit_orders.engine_deal_duration_minutes.

У репозиторії є файлик-приклад sample_config.json — просто скопіюй і відредагуй під себе.

Користування UI та API

UI: натисни Start from file, завантаж config.json. У таблицях побачиш TP, драбинку та логи.

Зупинка: натисни Stop (зупиняє моніторинг; ордери на біржі не чіпає).

REST (усі запити на /):

GET / — UI

GET /?json=1 — поточний стан у JSON (включно з free_usdt)

POST / — старт угоди (або multipart/form-data з полем file, або raw JSON у тілі)

DELETE / — зупинка моніторингу

Як це працює

Вхід ринком на суму market_order_amount (USDT). Кількість контрактів ≈ USDT / ціна, з округленням до мін-лота.

TP ставляться як reduceOnly від середньої ціни. Після доборів середня змінюється — TP перевиставляються.

Драбинка: orders_count ліміток проти поточної ціни в межах range_percent від середньої. Бюджет limit_orders_amount розподіляється порівну.

Захист: stop_loss_percent, trailing_sl_offset_percent, move_sl_to_breakeven. За тригером — ринкове reduceOnly закриття.

Моніторинг і робота двигуна тривають до engine_deal_duration_minutes, далі — автозупинка.

Траблшутінг

AuthenticationError 10003 (API key is invalid) — ключ не testnet або не зчитався. Пересоздай ключ у Demo, онови .env, перезапусти контейнер.

InsufficientFunds / 110007 (ab not enough) — у Unified Trading бракує USDT. Зроби Assets → Transfer.

setLeverage() requires linear/inverse market — вказано спот. Використай BTC/USDT:USDT.

InvalidOrder … amount must be >= min — надто мала кількість. Підійми market_order_amount/limit_orders_amount або зменш orders_count.

UI порожній / угода не стартує — подивись docker logs -f trade-engine, виправ причину з підказок вище.

Налаштування ризику

Ранні виходи по трейлінгу — підвищ trailing_sl_offset_percent (5–8) або вимкни move_sl_to_breakeven.

Пропускаються сходинки — зменш orders_count або збільш limit_orders_amount.

Замало часу — збільш engine_deal_duration_minutes (напр. 240–1440).

Скріншоти

Поклади картинки в docs/img/ і встав у README так:

![UI](docs/img/ui.png)

![Orders](docs/img/orders.png)

Безпека

Ніколи не коміть реальні ключі.

Для реальних грошей: IP-whitelist, окремі ролі, строгі ліміти, перевірка ордерів на стороні біржі.

Проєкт зроблено для тестів/навчання.

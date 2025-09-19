Trading Engine (Bybit Testnet)

Невеликий Python-двигун для демо-торгівлі деривативами на Bybit Testnet:

старт угоди з JSON-конфігом;

TP у % від середньої ціни (автоматичний replace після усереднення);

драбинка limit-ордерів для усереднення;

клієнтський SL / Trailing / BE;

простий веб-UI і єдиний REST ендпоінт /.

Зміст

Вимоги

Швидкий старт (Docker)

Змінні оточення (.env)

Приклад конфігу (config.json)

Користування UI та API

Як це працює

Траблшутінг

Налаштування ризику

Скріншоти

Безпека

Вимоги

Docker + Docker Compose

Обліковка Bybit Demo (Testnet) з балансом USDT в Unified Trading

Швидкий старт (Docker)
1) Створи Testnet API-ключ

Увімкни Demo Trading у шапці Bybit.

Create New Key → API Transaction.

Permissions (Read/Write):

Unified Trading → Contract → Orders

Unified Trading → Contract → Positions

IP restriction: No IP restriction (для тесту ок).

Збережи API Key та Secret (secret показують лише один раз).

2) Налаштуй .env (у корені репо)
BYBIT_API_KEY=your_testnet_key
BYBIT_SECRET=your_testnet_secret
MARKET_TYPE=swap
POLL_INTERVAL=2.0


За потреби скопіюй з .env_sample.

3) Запуск
docker compose up --build -d
# Логи:
docker logs -f trade-engine
# або
docker compose logs -f engine


Відкрий http://localhost:8000/
.
Якщо у статусі free_usdt: 0 — зроби Assets → Transfer до Unified Trading (USDT).

Змінні оточення (.env)
Змінна	Опис	Приклад
BYBIT_API_KEY	Testnet API key	abc...
BYBIT_SECRET	Testnet API secret	xyz...
MARKET_TYPE	Тип ринку для ccxt	swap
POLL_INTERVAL	Інтервал моніторингу (сек)	2.0
Приклад конфігу (config.json)

Використовуй деривативний символ BTC/USDT:USDT.
tp_orders — у % від середньої, з автоматичним перерахунком після доборів.

{
  "account": "Bybit/Testnet",
  "symbol": "BTC/USDT:USDT",
  "side": "short",
  "market_order_amount": 2000,
  "stop_loss_percent": 7,
  "trailing_sl_offset_percent": 3,
  "limit_orders_amount": 2000,
  "leverage": 10,
  "move_sl_to_breakeven": true,
  "tp_orders": [
    { "price_percent": 2.0, "quantity_percent": 25.0 },
    { "price_percent": 3.0, "quantity_percent": 25.0 },
    { "price_percent": 5.0, "quantity_percent": 25.0 },
    { "price_percent": 7.0, "quantity_percent": 25.0 }
  ],
  "limit_orders": {
    "range_percent": 5.0,
    "orders_count": 6,
    "engine_deal_duration_minutes": 110
  }
}


У репозиторії є файл-заготовка: sample_config.json.

Користування UI та API

UI: на сторінці натисни Start from file і підвантаж config.json.
Нижче побачиш TP ордери, драбинку, логи.

Зупинка: кнопка Stop (зупиняє моніторинг; ордери на біржі не чіпає).

REST (все на /)

GET / → UI (HTML)

GET /?json=1 → JSON-стан (разом із free_usdt)

POST / → старт угоди:

multipart/form-data з полем file (конфіг), або

raw JSON (той самий конфіг) у тілі.

DELETE / → стоп моніторингу

Як це працює

Market-вхід на market_order_amount (USDT)
→ кількість ≈ USDT / last_price, округлення до мін-лота.

TP — reduceOnly у % від середньої; після філа сходинки середня і TP перевиставляються.

Драбинка — N limit-ордерів проти ціни в діапазоні range_percent від середньої;
limit_orders_amount ділиться порівну між сходинками.

Захист (клієнтський): stop_loss_percent, trailing_sl_offset_percent, move_sl_to_breakeven.
За тригером — market reduceOnly.

Моніторинг раз на POLL_INTERVAL сек; по engine_deal_duration_minutes зупиняється.

Траблшутінг
Симптом / код	Причина	Що робити
AuthenticationError 10003: API key is invalid	ключ не Testnet / не підхопився	Створи ключ на Demo → API Transaction, дозволь Orders + Positions. Онови .env у корені, перезапусти: docker compose down && docker compose up --build -d
InsufficientFunds / 110007 ab not enough	немає USDT у Unified Trading	Assets → Transfer з Funding у Unified Trading (USDT)
setLeverage() requires linear/inverse market	спотовий символ	Вкажи symbol: "BTC/USDT:USDT"
InvalidOrder ... amount must be >= min	замало контрактів	Збільш market_order_amount / limit_orders_amount або зменш orders_count
UI порожній	угода не стартанула (була помилка)	Подивись docker logs -f trade-engine та виправ за таблицею вище
docker compose exec trade-engine ... не працює	ім’я сервісу != ім’я контейнера	У Compose сервіс — engine, контейнер — trade-engine. Використовуй docker compose exec engine ... або docker exec -it trade-engine sh
Налаштування ризику

Часті ранні виходи → збільш trailing_sl_offset_percent (5–8) або вимкни move_sl_to_breakeven.

Пропускаються дрібні сходинки → зменш orders_count або збільш limit_orders_amount.

Довший моніторинг → підвищ engine_deal_duration_minutes (наприклад, 240–1440).

Скріншоти
<img width="1280" height="550" alt="image" src="https://github.com/user-attachments/assets/086354d6-5cf6-4288-8994-4fc4b6b72428" />
<img width="1732" height="795" alt="image" src="https://github.com/user-attachments/assets/c795faa1-d8ec-4630-ab56-72f060d7fad1" />
<img width="841" height="802" alt="image" src="https://github.com/user-attachments/assets/4f7cd4a5-9e10-4abc-974e-0f2ebbc6740c" />



На GitHub ці шляхи відносні до кореня репозиторію.
Рекомендовані імена: ui.png, bybit-key.png, unified-transfer.png.

Безпека

Не коміть реальні ключі.

Якщо ключ “засвітили” — видаліть і перевипустіть.

Проєкт зроблено для тестнету / навчальних цілей.

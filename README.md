Trading Engine (Bybit Testnet)

Невеликий Python-двигун для демо-торгівлі деривативами на Bybit Testnet.

Що вміє:

запуск угоди з JSON-конфігом;

тейк-профіти у відсотках від середньої ціни входу (TP автоматично перевиставляються після усереднення);

«драбинка» лімітних ордерів для добору позиції;

клієнтський SL / Trailing / Breakeven;

простий веб-UI та один REST-ендпоінт /.

Зміст

Вимоги

Швидкий старт (Docker)

Змінні оточення (.env)

Конфіг угоди (поля)

Користування UI та API

Як це працює

Траблшутінг

Налаштування ризику

Скріншоти

Безпека

Вимоги

Встановлені Docker і Docker Compose

Обліковка Bybit Demo (Testnet) з USDT у Unified Trading

Швидкий старт (Docker)

Створи Testnet API-ключ
Увімкни Demo Trading → Create New Key → API Transaction. Дозволи Read/Write для Unified Trading → Contract → Orders і Positions. IP restriction можна залишити No IP restriction (для тестів ок). Збережи API Key і Secret (secret показують лише один раз).

Налаштуй .env у корені репозиторію
Потрібні змінні:
— BYBIT_API_KEY — твій testnet key
— BYBIT_SECRET — твій testnet secret
— MARKET_TYPE — swap
— POLL_INTERVAL — наприклад 2.0
Є шаблон .env_sample.

Запусти контейнер
docker compose up --build -d
Логи: docker logs -f trade-engine або docker compose logs -f engine.

Відкрий інтерфейс
http://localhost:8000/. Якщо у статусі free_usdt: 0 — зроби Assets → Transfer з Funding у Unified Trading (USDT).

Змінні оточення (.env)

BYBIT_API_KEY — Testnet API key

BYBIT_SECRET — Testnet API secret

MARKET_TYPE — тип ринку для ccxt, використовуй swap

POLL_INTERVAL — інтервал моніторингу в секундах

Конфіг угоди (поля)

Використовуй деривативний символ, наприклад BTC/USDT:USDT.

Головні поля:

account — довільний підпис, наприклад Bybit/Testnet

symbol — символ ринку, наприклад BTC/USDT:USDT

side — long або short

market_order_amount — ноціонал входу в USDT

stop_loss_percent — відсоток для клієнтського SL

trailing_sl_offset_percent — відступ трейлінгу у відсотках

limit_orders_amount — загальна сума для драбинки (USDT)

leverage — плече

move_sl_to_breakeven — якщо true, SL переноситься в беззбиток при русі ціни

Тейк-профіти:

tp_orders[].price_percent — рівень TP у відсотках від середньої ціни

tp_orders[].quantity_percent — частка позиції, яка закривається на цьому рівні

Драбинка:

limit_orders.range_percent — діапазон драбинки від середньої ціни у відсотках

limit_orders.orders_count — кількість сходинок

limit_orders.engine_deal_duration_minutes — час роботи моніторингу (хв)

У репозиторії є зразок файлу: sample_config.json.

Користування UI та API

На головній сторінці натисни Start from file і підвантаж config.json.

Кнопка Stop зупиняє лише моніторинг (існуючі ордери на біржі не змінюються).

Ендпоінти (усі на /):

GET / — UI (HTML)

GET /?json=1 — JSON-стан (включно з free_usdt)

POST / — старт угоди; можна передати multipart/form-data з полем file або raw JSON з конфігом у тілі

DELETE / — зупинка моніторингу

Як це працює

Вхід ринком на ноціонал market_order_amount (USDT). Кількість контрактів розраховується як USDT / остання ціна, далі — округлення до мін-лота.

TP ставляться як reduceOnly у відсотках від середньої ціни входу.

Драбинка лімітних ордерів розкладається проти поточного руху в межах range_percent; загальний limit_orders_amount ділиться порівну між сходинками.

Клієнтський захист: stop_loss_percent, trailing_sl_offset_percent, move_sl_to_breakeven. За тригером позиція закривається market reduceOnly.

Моніторинг із періодом POLL_INTERVAL. Після engine_deal_duration_minutes двигун зупиняється.

Траблшутінг

AuthenticationError 10003 (API key is invalid): ключ не testnet або не зчитався. Створи ключ у Demo → API Transaction з правами Orders і Positions, онови .env, перезапусти контейнер (docker compose down && up --build -d).

InsufficientFunds / 110007 (ab not enough): немає USDT у Unified Trading. Зроби Assets → Transfer з Funding у Unified Trading (USDT).

setLeverage() requires linear/inverse market: вказано спотовий символ. Використай BTC/USDT:USDT.

InvalidOrder … amount must be >= min: замало контрактів. Збільш market_order_amount або limit_orders_amount, або зменш orders_count.

Порожній UI/нічого не відбувається: угода не стартанула через помилку. Перевір логи контейнера та виправ за підказками вище.

Не працює docker compose exec trade-engine …: ім’я сервісу в Compose — engine, контейнера — trade-engine. Використовуй docker compose exec engine … або docker exec -it trade-engine sh.

Налаштування ризику

Ранні виходи за трейлінгом — підвищ trailing_sl_offset_percent (5–8) або вимкни move_sl_to_breakeven.

Пропускаються дрібні сходинки — зменш orders_count або збільш limit_orders_amount.

Замало часу на відпрацювання плану — підвищ engine_deal_duration_minutes (наприклад 240–1440).

Скріншоти

Збережи зображення у теку docs/img/ (наприклад docs/img/ui.png) і додай у README так:
![UI](docs/img/ui.png)
![Orders](docs/img/orders.png)

Безпека

Не коміть API-ключі у репозиторій.

Для продакшена додай IP-обмеження у ключ, окремі креденшли та перевірку ордерів на стороні біржі.

Цей проєкт призначений для тестів і навчання.

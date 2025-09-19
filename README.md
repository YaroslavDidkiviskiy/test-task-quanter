# Trading Engine · Bybit Testnet

Легкий Python-двигун для **демо-торгівлі деривативами** на Bybit Testnet:

- старт угоди з JSON-конфігом;
- TP у % від **середньої** (автореплейс після усереднення);
- «драбинка» лімітних ордерів для добору;
- клієнтський SL / Trailing / Breakeven;
- простий веб-UI та **єдиний REST ендпоінт** `/`.

---

## Зміст
- [Вимоги](#вимоги)
- [Швидкий старт (Docker)](#швидкий-старт-docker)
- [Змінні оточення `.env`](#змінні-оточення-env)
- [Конфіг угоди](#конфіг-угоди)
- [Користування UI та API](#користування-ui-та-api)
- [Як це працює](#як-це-працює)
- [Траблшутінг](#траблшутінг)
- [Налаштування ризику](#налаштування-ризику)
- [Скріншоти](#скріншоти)
- [Безпека](#безпека)

---

## Вимоги
- Docker і Docker Compose  
- Обліковка **Bybit Demo (Testnet)** з USDT у **Unified Trading**

---

## Швидкий старт (Docker)

1. **Створи Testnet API-ключ**: Demo → *Create New Key* → *API Transaction*. Дай права **Orders** і **Positions** у *Unified Trading / Contract*.
2. **Заповни `.env`** у корені (є приклад у `.env_sample`).
3. Запусти:  
   `docker compose up --build -d`
4. Відкрий **http://localhost:8000/**. Якщо `free_usdt: 0` — зроби *Assets → Transfer* з Funding у Unified Trading (USDT).
5. Натисни **Start from file** і вибери свій `config.json`.

---

## Змінні оточення `.env`

- `BYBIT_API_KEY` — testnet API key  
- `BYBIT_SECRET` — testnet API secret  
- `MARKET_TYPE` — тип ринку для ccxt (використовуй `swap`)  
- `POLL_INTERVAL` — період моніторингу (сек), напр. `2.0`

> Не коміть реальні ключі.

---

## Конфіг угоди

Використовуй **деривативний символ** (напр. `BTC/USDT:USDT`).

Головні поля:
- `side`: `long` або `short`
- `market_order_amount`: ноціонал входу в USDT
- `limit_orders_amount`: бюджет на драбинку (USDT)
- `leverage`: плече
- `tp_orders`: список рівнів (`price_percent`, `quantity_percent`)
- `limit_orders`: `range_percent`, `orders_count`, `engine_deal_duration_minutes`
- захист: `stop_loss_percent`, `trailing_sl_offset_percent`, `move_sl_to_breakeven`

Шаблон: див. **`sample_config.json`** у репо.

---

## Користування UI та API

- **UI**: кнопка **Start from file** → обери `config.json`. Нижче видно TP, драбинку, логи.  
- **Stop**: зупиняє моніторинг (ордери на біржі не чіпає).

**REST (усе на `/`):**
- `GET /` — UI  
- `GET /?json=1` — стан у JSON (включно з `free_usdt`)  
- `POST /` — старт угоди (multipart `file` **або** raw JSON у тілі)  
- `DELETE /` — стоп моніторингу

---

## Як це працює

1. Вхід **ринком** на `market_order_amount` (USDT) → кількість ≈ USDT/ціна (з округленням до мін-лота).
2. **TP** ставляться як *reduceOnly* від **середньої**; після добору середня змінюється — TP **перевиставляються**.
3. **Драбинка**: `orders_count` ліміток проти ціни в межах `range_percent` від середньої; бюджет `limit_orders_amount` ділиться порівну.
4. **Захист**: `stop_loss_percent`, `trailing_sl_offset_percent`, `move_sl_to_breakeven`. За тригером — ринкове `reduceOnly` закриття.
5. Моніторинг триває до `engine_deal_duration_minutes`, потім автозупинка.

---

## Траблшутінг

- **10003 API key is invalid** — ключ не testnet або не підхопився. Пересоздай у Demo, онови `.env`, перезапусти контейнер.  
- **110007 ab not enough / InsufficientFunds** — у Unified Trading немає USDT. *Assets → Transfer*.  
- **setLeverage… requires linear/inverse market** — вказано спот. Використай `BTC/USDT:USDT`.  
- **InvalidOrder … amount must be >= min** — надто мала кількість. Підвищ `market_order_amount`/`limit_orders_amount` або зменш `orders_count`.  
- **UI порожній** — подивись `docker logs -f trade-engine`, виправ причину.

---

## Налаштування ризику

- Ранні виходи по трейлінгу → збільш `trailing_sl_offset_percent` (5–8) або вимкни `move_sl_to_breakeven`.  
- Пропускаються сходинки → зменш `orders_count` або збільш `limit_orders_amount`.  
- Замало часу → збільш `engine_deal_duration_minutes` (наприклад 240–1440).

---

## Скріншоти

Поклади файли в `docs/img/` і встав посиланням:

<img width="1280" height="550" alt="image" src="https://github.com/user-attachments/assets/90bf7896-de05-4c84-b69c-504b4e9304c1" />
<img width="1280" height="575" alt="image" src="https://github.com/user-attachments/assets/9f5f876c-c7d7-4fdf-a7ec-848a268f7de5" />
<img width="841" height="802" alt="image" src="https://github.com/user-attachments/assets/4f7cd4a5-9e10-4abc-974e-0f2ebbc6740c" />

---

## Безпека

- Не коміть реальні ключі; для реальних грошей — IP-whitelist, окремі креденшли та суворі ліміти.  
- Проєкт для тестів/навчання.


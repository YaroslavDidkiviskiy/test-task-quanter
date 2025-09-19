# app/engine.py
import asyncio, time
from .models import DealConfig, EngineState, OrderRef, PositionState
from .exchange import ExchangeClient
from .tp_manager import compute_tp_prices, compute_tp_amounts, side_to_reduce, side_to_enter

def now_ms() -> int: return int(time.time() * 1000)

class DealEngine:
    def __init__(self, ex: ExchangeClient, state: EngineState, poll_interval: float = 2.0):
        self.ex = ex
        self.s = state
        self.poll = poll_interval
        self._task = None
        self._sym = None  # резольвлений символ

    async def start(self, cfg: DealConfig):
        self.s.running = True
        self.s.config = cfg

        # load + resolve + leverage
        await self.ex.load()
        self._sym = self.ex.resolve_symbol(cfg.symbol)
        await self.ex.set_leverage(self._sym, cfg.leverage)

        # баланс і автоскейл
        bal = await self.ex.fetch_balance()
        free_usdt = self.ex.get_free_usdt(bal)

        last = await self.ex.ticker_last(self._sym)
        min_amt = self.ex.min_amount(self._sym)
        min_notional = min_amt * last

        entry = max(cfg.market_order_amount, min_notional)
        ladder = max(0.0, cfg.limit_orders_amount)
        lev = max(1, cfg.leverage)
        need = (entry + ladder) / lev * 1.05

        if free_usdt < need:
            scale = max(0.0, (free_usdt / need) * 0.98)
            entry *= scale
            ladder *= scale
            self.s.log(f"[AUTO-SCALE] entry≈{entry:.2f}USDT ladder≈{ladder:.2f}USDT (free {free_usdt:.2f})")

            # мінімальний лот по входу
            if entry < min_notional:
                ladder = 0.0
                entry = min_notional
                need_min = entry / lev * 1.05
                if free_usdt < need_min:
                    self.s.running = False
                    raise ValueError(
                        f"Insufficient USDT even for min lot: need≈{need_min:.4f}, have {free_usdt:.4f}. "
                        f"Top up testnet USDT to Derivatives/Unified or reduce amounts."
                    )

        # MARKET ENTRY
        qty = self.ex.amount_to_precision(self._sym, max(min_amt, entry / last))
        side = side_to_enter(cfg.side)
        try:
            await self.ex.create_market(self._sym, side, qty, params={"reduceOnly": False})
        except Exception as e:
            self.s.running = False
            raise ValueError(
                f"Insufficient funds for market entry: qty≈{qty:.6f} ({entry:.2f} USDT @ {last:.2f}), "
                f"free≈{free_usdt:.2f}. Bybit: {e}"
            )
        self.s.log(f"[ENTRY] {cfg.side.upper()} ~{qty:.6f} {self._sym} @ ~{last:.2f}")

        await self.refresh_position()

        # SL/Trailing init
        if self.s.position and self.s.position.avg_entry_price > 0:
            if cfg.side == "long":
                self.s.sl_price_abs = self.s.position.avg_entry_price * (1 - cfg.stop_loss_percent/100.0)
            else:
                self.s.sl_price_abs = self.s.position.avg_entry_price * (1 + cfg.stop_loss_percent/100.0)
            self.s.trailing_best = self.s.position.avg_entry_price
            self.s.log(f"[SL] client SL: {self.s.sl_price_abs:.2f}")

        await self.replace_tp_orders()
        if ladder > 0:
            old = self.s.config.limit_orders_amount
            self.s.config.limit_orders_amount = float(ladder)
            await self.place_limit_ladder()
            self.s.config.limit_orders_amount = old

        self._task = asyncio.create_task(self._monitor())

    async def stop(self):
        self.s.running = False
        if self._task:
            self._task.cancel()
            try: await self._task
            except asyncio.CancelledError: pass

    async def refresh_position(self):
        cfg = self.s.config
        pos = PositionState(symbol=self._sym or cfg.symbol, side=cfg.side, size=0.0, avg_entry_price=0.0, leverage=cfg.leverage)
        positions = await self.ex.fetch_positions(self._sym or cfg.symbol)
        rs = self._sym or cfg.symbol
        for p in positions or []:
            if p.get("symbol") == rs and float(p.get("contracts", 0) or 0) > 0:
                pos.size = float(p.get("contracts", 0) or 0)
                pos.avg_entry_price = float(p.get("entryPrice") or p.get("entry_price") or 0.0)
                break
        self.s.position = pos

    async def replace_tp_orders(self):
        cfg = self.s.config
        await self.refresh_position()
        if not self.s.position or self.s.position.size <= 0 or self.s.position.avg_entry_price <= 0:
            self.s.log("[TP] no position -> skip")
            return

        # cancel старі reduceOnly
        opens = await self.ex.fetch_open_orders(self._sym or cfg.symbol)
        for o in opens:
            if o.get("type") == "limit" and o.get("reduceOnly"):
                await self.ex.cancel_order(self._sym or cfg.symbol, o["id"])

        avg = self.s.position.avg_entry_price
        total = self.s.position.size
        prices = compute_tp_prices(avg, cfg.side, cfg)
        amounts = compute_tp_amounts(total, cfg)
        rside = side_to_reduce(cfg.side)

        min_amt = self.ex.min_amount(self._sym or cfg.symbol)
        self.s.tp_orders.clear()

        carry = 0.0
        for i, (p, a) in enumerate(zip(prices, amounts)):
            a2 = a + carry
            if i < len(prices) - 1 and a2 < min_amt:
                carry = a2
                continue
            if i == len(prices) - 1:
                a2 = max(total - sum([x.amount for x in self.s.tp_orders]), min_amt if total >= min_amt else total)

            price = self.ex.price_to_precision(self._sym or cfg.symbol, p)
            amount = self.ex.amount_to_precision(self._sym or cfg.symbol, a2)
            if amount <= 0: continue
            if total < min_amt and amount > total:
                amount = self.ex.amount_to_precision(self._sym or cfg.symbol, total)
                if amount < min_amt:
                    self.s.log(f"[TP] position {total:.6f} < min {min_amt:.6f} → skip TPs")
                    break

            created = await self.ex.create_limit(self._sym or cfg.symbol, rside, amount, price,
                                                 params={"reduceOnly": True, "timeInForce": "GTC"})
            self.s.tp_orders.append(OrderRef(id=created["id"], price=price, amount=amount,
                                             type="limit", side=rside, status="open", reduce_only=True))
            self.s.log(f"[TP] {rside} {amount:.6f} @ {price:.2f} (id={created['id']})")
            carry = 0.0

    async def place_limit_ladder(self):
        cfg = self.s.config
        await self.refresh_position()
        if not self.s.position or self.s.position.size <= 0 or self.s.position.avg_entry_price <= 0:
            return
        avg = self.s.position.avg_entry_price
        n = cfg.limit_orders.orders_count
        rng = cfg.limit_orders.range_percent / 100.0
        per_usdt = cfg.limit_orders_amount / max(1, n)
        min_amt = self.ex.min_amount(self._sym or cfg.symbol)

        self.s.limit_ladder.clear()
        for i in range(1, n+1):
            frac = i / n
            side = "buy" if cfg.side == "long" else "sell"
            price_raw = avg * (1 - rng*frac) if cfg.side == "long" else avg * (1 + rng*frac)
            price = self.ex.price_to_precision(self._sym or cfg.symbol, price_raw)
            qty_raw = await self.ex.usdt_to_contracts(self._sym or cfg.symbol, per_usdt, price)
            if qty_raw < min_amt:
                self.s.log(f"[LADDER] skip {i}/{n}: too small ({qty_raw:.6f} < {min_amt:.6f})")
                continue
            qty = self.ex.amount_to_precision(self._sym or cfg.symbol, max(qty_raw, min_amt))
            created = await self.ex.create_limit(self._sym or cfg.symbol, side, qty, price,
                                                 params={"reduceOnly": False, "postOnly": True, "timeInForce": "GTC"})
            self.s.limit_ladder.append(OrderRef(id=created["id"], price=price, amount=qty,
                                                type="limit", side=side, status="open", reduce_only=False))
            self.s.log(f"[LADDER] {side} {qty:.6f} @ {price:.2f} (id={created['id']})")

    async def _client_side_stops(self) -> bool:
        cfg = self.s.config
        pos = self.s.position
        if not pos or pos.size <= 0 or pos.avg_entry_price <= 0:
            return False
        last = await self.ex.ticker_last(self._sym or cfg.symbol)
        off = cfg.trailing_sl_offset_percent/100.0

        if cfg.side == "long":
            self.s.trailing_best = max(self.s.trailing_best or last, last)
            trigger = self.s.trailing_best * (1 - off)
            if cfg.move_sl_to_breakeven and not self.s.be_moved and self.s.trailing_best > pos.avg_entry_price:
                self.s.sl_price_abs = pos.avg_entry_price; self.s.be_moved = True
                self.s.log(f"[BE] SL -> breakeven @ {self.s.sl_price_abs:.2f}")
            if (self.s.sl_price_abs and last <= self.s.sl_price_abs) or last <= trigger:
                await self._market_close_all(); return True
        else:
            self.s.trailing_best = min(self.s.trailing_best or last, last)
            trigger = self.s.trailing_best * (1 + off)
            if cfg.move_sl_to_breakeven and not self.s.be_moved and self.s.trailing_best < pos.avg_entry_price:
                self.s.sl_price_abs = pos.avg_entry_price; self.s.be_moved = True
                self.s.log(f"[BE] SL -> breakeven @ {self.s.sl_price_abs:.2f}")
            if (self.s.sl_price_abs and last >= self.s.sl_price_abs) or last >= trigger:
                await self._market_close_all(); return True
        return False

    async def _market_close_all(self):
        cfg = self.s.config; pos = self.s.position
        if not pos or pos.size <= 0: return
        rside = side_to_reduce(cfg.side)
        amt = self.ex.amount_to_precision(self._sym or cfg.symbol, pos.size)
        await self.ex.create_market(self._sym or cfg.symbol, rside, amt, params={"reduceOnly": True})
        self.s.log(f"[CLOSE] {rside} {amt:.6f} @ market (reduceOnly)")
        pos.size = 0.0

    async def _monitor(self):
        cfg = self.s.config
        deadline = now_ms() + cfg.limit_orders.engine_deal_duration_minutes * 60 * 1000
        while self.s.running:
            try:
                if await self._client_side_stops():
                    break
                opens = await self.ex.fetch_open_orders(self._sym or cfg.symbol)
                open_ids = {o["id"] for o in opens}
                before = {o.id for o in self.s.limit_ladder}
                filled = list(before - open_ids)
                if filled:
                    self.s.limit_ladder = [o for o in self.s.limit_ladder if o.id not in filled]
                    self.s.log(f"[FILL] ladder filled: {filled}")
                    await self.refresh_position()
                    await self.replace_tp_orders()
                if now_ms() > deadline:
                    self.s.log("[ENGINE] duration exceeded -> stop")
                    break
            except Exception as e:
                self.s.log(f"[MONITOR ERROR] {e}")
            await asyncio.sleep(self.poll)

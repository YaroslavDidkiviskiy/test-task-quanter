# app/exchange.py
import ccxt.async_support as ccxt
from typing import List, Dict, Any, Optional

class ExchangeClient:
    def __init__(self, api_key: str, secret: str, market_type: str = "swap", testnet: bool = True):
        self.exchange = ccxt.bybit({
            "apiKey": api_key,
            "secret": secret,
            "enableRateLimit": True,
            "options": {
                "defaultType": market_type,        # деривативи
                "createMarketBuyOrderRequiresPrice": False,
            },
        })
        self.exchange.set_sandbox_mode(testnet)
        self._markets_loaded = False

    # --- базове ---
    async def load(self) -> None:
        await self.exchange.load_markets()
        self._markets_loaded = True

    async def close(self) -> None:
        await self.exchange.close()

    async def fetch_balance(self) -> Dict[str, Any]:
        return await self.exchange.fetch_balance()

    def get_free_usdt(self, bal: Dict[str, Any]) -> float:
        if isinstance(bal.get("free"), dict):
            return float(bal["free"].get("USDT") or 0.0)
        if isinstance(bal.get("USDT"), dict):
            return float(bal["USDT"].get("free") or 0.0)
        return 0.0

    # --- символ/прецизійність/ліміти ---
    def resolve_symbol(self, symbol: str) -> str:
        return self._resolve_symbol(symbol)

    def _resolve_symbol(self, symbol: str) -> str:
        if not self._markets_loaded:
            return symbol
        markets = self.exchange.markets or {}
        if ":" in symbol:
            return symbol
        # Пріоритет: BASE/USDT:USDT
        if "/" in symbol:
            base, _ = symbol.split("/", 1)
            cand = f"{base}/USDT:USDT"
            if cand in markets:
                return cand
            # запасний: будь-який linear swap з тим же base
            for m in markets.values():
                if m.get("swap") and m.get("linear") and m.get("base") == base:
                    return m["symbol"]
        return symbol if symbol in markets else symbol

    def market_info(self, symbol: str) -> Dict[str, Any]:
        rs = self.resolve_symbol(symbol)
        return self.exchange.market(rs)

    def amount_to_precision(self, symbol: str, amount: float) -> float:
        rs = self.resolve_symbol(symbol)
        return float(self.exchange.amount_to_precision(rs, amount))

    def price_to_precision(self, symbol: str, price: float) -> float:
        rs = self.resolve_symbol(symbol)
        return float(self.exchange.price_to_precision(rs, price))

    def min_amount(self, symbol: str) -> float:
        m = self.market_info(symbol)
        lim = (m.get("limits") or {}).get("amount") or {}
        mn = lim.get("min")
        if mn is not None:
            return float(mn)
        prec = (m.get("precision") or {}).get("amount")
        return float(prec or 0.0)

    # --- торгівля ---
    async def set_leverage(self, symbol: str, leverage: int) -> None:
        if not self._markets_loaded:
            return
        rs = self.resolve_symbol(symbol)
        m = self.exchange.market(rs)
        if not (m.get("swap") and (m.get("linear") or m.get("inverse"))):
            return
        try:
            await self.exchange.set_leverage(leverage, rs, params={
                "category": "linear", "buyLeverage": leverage, "sellLeverage": leverage
            })
        except Exception:
            try:
                await self.exchange.set_margin_mode("cross", rs, params={"category": "linear"})
                await self.exchange.set_position_mode(hedged=False, symbol=rs, params={"category": "linear"})
                await self.exchange.set_leverage(leverage, rs, params={
                    "category": "linear", "buyLeverage": leverage, "sellLeverage": leverage
                })
            except Exception:
                pass

    async def ticker_last(self, symbol: str) -> float:
        rs = self.resolve_symbol(symbol)
        t = await self.exchange.fetch_ticker(rs)
        for k in ("last", "close", "ask", "bid"):
            v = t.get(k)
            if v is not None:
                return float(v)
        return float(t["last"])

    async def fetch_positions(self, symbol: str) -> List[Dict[str, Any]]:
        rs = self.resolve_symbol(symbol)
        try:
            return await self.exchange.fetch_positions([rs])
        except Exception:
            return []

    async def fetch_open_orders(self, symbol: str) -> List[Dict[str, Any]]:
        rs = self.resolve_symbol(symbol)
        try:
            return await self.exchange.fetch_open_orders(rs)
        except Exception:
            return []

    async def create_market(self, symbol: str, side: str, amount: float,
                            params: Optional[dict] = None) -> Dict[str, Any]:
        rs = self.resolve_symbol(symbol)
        p = {"timeInForce": "GTC", "category": "linear"}
        if params:
            p.update(params)
        return await self.exchange.create_order(rs, "market", side, amount, None, p)

    async def create_limit(self, symbol: str, side: str, amount: float, price: float,
                           params: Optional[dict] = None) -> Dict[str, Any]:
        rs = self.resolve_symbol(symbol)
        p = {"timeInForce": "GTC", "category": "linear"}
        if params:
            p.update(params)
        return await self.exchange.create_order(rs, "limit", side, amount, price, p)

    async def cancel_order(self, symbol: str, order_id: str) -> None:
        rs = self.resolve_symbol(symbol)
        try:
            await self.exchange.cancel_order(order_id, rs)
        except Exception:
            pass

    async def usdt_to_contracts(self, symbol: str, usdt: float, price: float) -> float:
        if price <= 0:
            return 0.0
        return usdt / price

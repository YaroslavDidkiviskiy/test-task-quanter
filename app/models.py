from typing import List, Literal, Optional
from pydantic import BaseModel, Field

Side = Literal["long", "short"]

class TPOrderCfg(BaseModel):
    price_percent: float
    quantity_percent: float

class LimitLadderCfg(BaseModel):
    range_percent: float
    orders_count: int
    engine_deal_duration_minutes: int

class DealConfig(BaseModel):
    account: str = "Bybit/Testnet"
    symbol: str
    side: Side
    market_order_amount: float
    stop_loss_percent: float
    trailing_sl_offset_percent: float
    limit_orders_amount: float
    leverage: int = 10
    move_sl_to_breakeven: bool = True
    tp_orders: List[TPOrderCfg]
    limit_orders: LimitLadderCfg

class OrderRef(BaseModel):
    id: str
    price: float
    amount: float
    type: str
    side: str
    status: Optional[str] = None
    reduce_only: bool = False

class PositionState(BaseModel):
    symbol: str
    side: Side
    size: float = 0.0
    avg_entry_price: float = 0.0
    leverage: Optional[int] = None

class EngineState(BaseModel):
    running: bool = False
    config: Optional[DealConfig] = None
    position: Optional[PositionState] = None
    tp_orders: List[OrderRef] = Field(default_factory=list)
    limit_ladder: List[OrderRef] = Field(default_factory=list)
    sl_price_abs: Optional[float] = None
    trailing_best: Optional[float] = None
    be_moved: bool = False
    logs: List[str] = Field(default_factory=list)

    def log(self, msg: str):
        self.logs.append(msg)
        print(msg, flush=True)

from typing import List
from .models import DealConfig

def compute_tp_prices(avg_entry: float, side: str, cfg: DealConfig) -> List[float]:
    prices = []
    for tp in cfg.tp_orders:
        if side == "long":
            prices.append(avg_entry * (1 + tp.price_percent/100.0))
        else:
            prices.append(avg_entry * (1 - tp.price_percent/100.0))
    return prices

def compute_tp_amounts(total_contracts: float, cfg: DealConfig) -> List[float]:
    return [total_contracts * (tp.quantity_percent/100.0) for tp in cfg.tp_orders]

def side_to_reduce(side: str) -> str:
    return "sell" if side == "long" else "buy"

def side_to_enter(side: str) -> str:
    return "buy" if side == "long" else "sell"

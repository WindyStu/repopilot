from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class PriceChanged:
    sku: str
    old_price: Decimal
    new_price: Decimal

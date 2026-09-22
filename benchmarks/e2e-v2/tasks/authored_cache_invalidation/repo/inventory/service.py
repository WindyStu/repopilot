from decimal import Decimal

from inventory.models import Product
from inventory.repository import InventoryRepository


class InventoryService:
    def __init__(self, repository: InventoryRepository) -> None:
        self._repository = repository
        self._cache: dict[str, Product] = {}

    def get_product(self, sku: str) -> Product:
        if sku not in self._cache:
            self._cache[sku] = self._repository.get(sku)
        return self._cache[sku]

    def update_price(self, sku: str, price: Decimal) -> Product:
        return self._repository.update_price(sku, price)

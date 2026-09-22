from decimal import Decimal

from inventory.models import Product


class InventoryRepository:
    def __init__(self, products: list[Product]) -> None:
        self._products = {product.sku: product for product in products}
        self.fail_updates: set[str] = set()
        self.read_count: dict[str, int] = {}

    def get(self, sku: str) -> Product:
        self.read_count[sku] = self.read_count.get(sku, 0) + 1
        return self._products[sku]

    def update_price(self, sku: str, price: Decimal) -> Product:
        if sku in self.fail_updates:
            raise RuntimeError("persistence failed")
        product = Product(sku=sku, price=price)
        self._products[sku] = product
        return product

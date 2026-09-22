from decimal import Decimal

from inventory import InventoryRepository, InventoryService, Product


def test_get_product_is_cached():
    repository = InventoryRepository([Product("A", Decimal("10.00"))])
    service = InventoryService(repository)

    assert service.get_product("A") == service.get_product("A")
    assert repository.read_count["A"] == 1

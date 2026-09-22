from decimal import Decimal

import pytest

from inventory import InventoryRepository, InventoryService, Product


def build_service():
    repository = InventoryRepository(
        [Product("A", Decimal("10.00")), Product("B", Decimal("20.00"))]
    )
    return repository, InventoryService(repository)


def test_successful_update_invalidates_updated_product():
    repository, service = build_service()
    service.get_product("A")

    service.update_price("A", Decimal("12.50"))

    assert service.get_product("A").price == Decimal("12.50")
    assert repository.read_count["A"] == 2


def test_successful_update_does_not_evict_other_products():
    repository, service = build_service()
    original_b = service.get_product("B")
    service.get_product("A")

    service.update_price("A", Decimal("11.00"))

    assert service.get_product("B") is original_b
    assert repository.read_count["B"] == 1


def test_failed_update_preserves_cached_value():
    repository, service = build_service()
    cached = service.get_product("A")
    repository.fail_updates.add("A")

    with pytest.raises(RuntimeError, match="persistence failed"):
        service.update_price("A", Decimal("99.00"))

    assert service.get_product("A") is cached
    assert repository.read_count["A"] == 1

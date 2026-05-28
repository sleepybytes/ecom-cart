"""
Tests for InventoryService — hard validation on add/update.
"""
import pytest

from app.repositories.product_repo import ProductRepository
from app.services.inventory_service import InventoryService


class TestInventoryService:
    @pytest.fixture
    def service(self, db):
        return InventoryService(ProductRepository(db))

    def test_sufficient_inventory_passes(self, service, products):
        # p2 has inventory=50, requesting 10 → should not raise
        service.validate("p2", 10)

    def test_exact_inventory_passes(self, service, products):
        # p2 has inventory=50, requesting exactly 50
        service.validate("p2", 50)

    def test_exceeds_inventory_raises(self, service, products):
        with pytest.raises(ValueError, match="Insufficient inventory"):
            service.validate("p2", 51)

    def test_error_message_contains_product_name(self, service, products):
        with pytest.raises(ValueError, match="Whole Milk"):
            service.validate("p2", 999)

    def test_error_message_shows_requested_and_available(self, service, products):
        with pytest.raises(ValueError, match="Requested: 99, Available: 50"):
            service.validate("p2", 99)

    def test_product_not_found_raises(self, service, products):
        with pytest.raises(ValueError, match="not found"):
            service.validate("p999", 1)

    def test_low_inventory_product(self, service, products):
        # p7 has inventory=5
        service.validate("p7", 5)
        with pytest.raises(ValueError):
            service.validate("p7", 6)

    def test_quantity_one_always_valid_when_in_stock(self, service, products):
        for pid in ["p1", "p2", "p3", "p5"]:
            service.validate(pid, 1)  # should not raise

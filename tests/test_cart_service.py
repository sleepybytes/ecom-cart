"""
Tests for CartService — business logic layer.
"""
import pytest
from fastapi import HTTPException

from app.repositories.cart_repo import CartRepository
from app.repositories.product_repo import ProductRepository
from app.repositories.promotion_repo import PromotionRepository
from app.schemas.cart import CartItemIn, CartItemUpdate
from app.services.cart_service import CartService
from app.services.inventory_service import InventoryService
from app.services.promotion_service import PromotionService


@pytest.fixture
def service(db):
    product_repo = ProductRepository(db)
    cart_repo = CartRepository(db)
    promo_repo = PromotionRepository(db)
    promotion_service = PromotionService(promo_repo)
    inventory_service = InventoryService(product_repo)
    return CartService(cart_repo, product_repo, promotion_service, inventory_service)


# ── get_cart ──────────────────────────────────────────────────────────────────

class TestGetCart:
    def test_empty_cart_returns_zero_totals(self, service):
        cart = service.get_cart(None)
        assert cart.items == []
        assert cart.subtotal == 0.0
        assert cart.total == 0.0
        assert cart.total_discount == 0.0

    def test_cart_with_item_returns_correct_subtotal(self, service, products):
        service.add_item(CartItemIn(product_id="p2", quantity=2))
        cart = service.get_cart(None)
        assert len(cart.items) == 1
        assert cart.subtotal == pytest.approx(9.98, abs=0.01)

    def test_promo_applied_and_discount_calculated(self, service, products, promotions):
        service.add_item(CartItemIn(product_id="p2", quantity=2))
        cart = service.get_cart(None)
        item = cart.items[0]
        # 20% off Whole Milk × 2 = 2.00 discount
        assert item.total_item_discount == pytest.approx(2.00, abs=0.01)
        assert item.line_total == pytest.approx(7.98, abs=0.01)
        assert cart.total_discount == pytest.approx(2.00, abs=0.01)

    def test_no_promo_for_unrelated_product(self, service, products, promotions):
        service.add_item(CartItemIn(product_id="p5", quantity=1))
        cart = service.get_cart(None)
        item = cart.items[0]
        assert item.applied_promotions == []
        assert item.total_item_discount == 0.0

    def test_inventory_warning_when_stock_drops(self, service, products, db):
        service.add_item(CartItemIn(product_id="p2", quantity=3))
        # Simulate stock dropping externally
        from app.models.product import Product
        p = db.get(Product, "p2")
        p.inventory = 1
        db.commit()

        cart = service.get_cart(None)
        assert len(cart.inventory_warnings) == 1
        assert "Whole Milk" in cart.inventory_warnings[0]

    def test_delivery_warning_when_promo_expires_before_delivery(self, service, products, db):
        from app.models.promotion import Promotion
        from tests.conftest import utc_dt
        promo = Promotion(
            id="expiring",
            description="Expiring Soon",
            type="PERCENTAGE",
            value=10,
            start_date=utc_dt(days=-1),
            end_date=utc_dt(days=2),
            applicable_product_ids=["p2"],
        )
        db.add(promo)
        db.commit()

        service.add_item(CartItemIn(product_id="p2", quantity=1))
        from datetime import timezone
        delivery = utc_dt(days=10).replace(tzinfo=timezone.utc)
        cart = service.get_cart(delivery)
        assert any("expiring" in w for w in cart.warnings)

    def test_eligible_promotions_shown_in_manual_mode(self, service, products, promotions, db):
        service.add_item(CartItemIn(product_id="p2", quantity=1))
        cart = service.get_cart(None)
        item_id = cart.items[0].id
        # Remove one promo to switch to manual mode with an eligible promo remaining
        service.remove_promotion(item_id, "promo_pct")
        cart = service.get_cart(None)
        item = cart.items[0]
        eligible_ids = {e.id for e in item.eligible_promotions}
        assert "promo_pct" in eligible_ids


# ── add_item ──────────────────────────────────────────────────────────────────

class TestAddItem:
    def test_adds_new_item(self, service, products):
        cart = service.add_item(CartItemIn(product_id="p2", quantity=2))
        assert len(cart.items) == 1
        assert cart.items[0].product_id == "p2"
        assert cart.items[0].quantity == 2

    def test_same_product_increments_quantity(self, service, products):
        service.add_item(CartItemIn(product_id="p2", quantity=2))
        cart = service.add_item(CartItemIn(product_id="p2", quantity=3))
        assert len(cart.items) == 1
        assert cart.items[0].quantity == 5

    def test_different_products_create_separate_items(self, service, products):
        service.add_item(CartItemIn(product_id="p2", quantity=1))
        cart = service.add_item(CartItemIn(product_id="p3", quantity=1))
        assert len(cart.items) == 2

    def test_invalid_product_raises_404(self, service, products):
        with pytest.raises(HTTPException) as exc:
            service.add_item(CartItemIn(product_id="p999", quantity=1))
        assert exc.value.status_code == 404

    def test_exceeds_inventory_raises_400(self, service, products):
        with pytest.raises(HTTPException) as exc:
            service.add_item(CartItemIn(product_id="p7", quantity=999))
        assert exc.value.status_code == 400
        assert "Insufficient inventory" in exc.value.detail

    def test_combined_quantity_exceeds_inventory_raises(self, service, products):
        # p7 has inventory=5; add 4, then try to add 3 more (total 7 > 5)
        service.add_item(CartItemIn(product_id="p7", quantity=4))
        with pytest.raises(HTTPException) as exc:
            service.add_item(CartItemIn(product_id="p7", quantity=3))
        assert exc.value.status_code == 400

    def test_price_locked_at_add_time(self, service, products, db):
        service.add_item(CartItemIn(product_id="p2", quantity=1))
        # Change product price externally
        from app.models.product import Product
        p = db.get(Product, "p2")
        original_price = p.price
        p.price = 99.99
        db.commit()

        cart = service.get_cart(None)
        assert cart.items[0].unit_price_at_add == pytest.approx(original_price)


# ── update_item ───────────────────────────────────────────────────────────────

class TestUpdateItem:
    def test_updates_quantity(self, service, products):
        cart = service.add_item(CartItemIn(product_id="p2", quantity=2))
        item_id = cart.items[0].id
        cart = service.update_item(item_id, CartItemUpdate(quantity=5))
        assert cart.items[0].quantity == 5

    def test_item_not_found_raises_404(self, service, products):
        with pytest.raises(HTTPException) as exc:
            service.update_item(9999, CartItemUpdate(quantity=1))
        assert exc.value.status_code == 404

    def test_exceeds_inventory_raises_400(self, service, products):
        cart = service.add_item(CartItemIn(product_id="p7", quantity=1))
        item_id = cart.items[0].id
        with pytest.raises(HTTPException) as exc:
            service.update_item(item_id, CartItemUpdate(quantity=999))
        assert exc.value.status_code == 400

    def test_total_recalculates_after_update(self, service, products, promotions):
        cart = service.add_item(CartItemIn(product_id="p2", quantity=1))
        item_id = cart.items[0].id
        cart = service.update_item(item_id, CartItemUpdate(quantity=3))
        # 20% of 4.99 × 3 = 2.994 → ~3.00
        assert cart.total_discount == pytest.approx(3.00, abs=0.01)


# ── delete_item ───────────────────────────────────────────────────────────────

class TestDeleteItem:
    def test_removes_item(self, service, products):
        cart = service.add_item(CartItemIn(product_id="p2", quantity=1))
        item_id = cart.items[0].id
        cart = service.delete_item(item_id)
        assert cart.items == []

    def test_item_not_found_raises_404(self, service, products):
        with pytest.raises(HTTPException) as exc:
            service.delete_item(9999)
        assert exc.value.status_code == 404

    def test_other_items_remain_after_delete(self, service, products):
        service.add_item(CartItemIn(product_id="p2", quantity=1))
        cart = service.add_item(CartItemIn(product_id="p3", quantity=2))
        item_id = cart.items[0].id
        cart = service.delete_item(item_id)
        assert len(cart.items) == 1


# ── clear_cart ────────────────────────────────────────────────────────────────

class TestClearCart:
    def test_empties_all_items(self, service, products):
        service.add_item(CartItemIn(product_id="p2", quantity=1))
        service.add_item(CartItemIn(product_id="p3", quantity=2))
        cart = service.clear_cart()
        assert cart.items == []
        assert cart.total == 0.0

    def test_clear_empty_cart_is_safe(self, service):
        cart = service.clear_cart()
        assert cart.items == []


# ── apply / remove promotion ──────────────────────────────────────────────────

class TestPromotionApplication:
    def test_apply_promotion_moves_to_applied(self, service, products, promotions, db):
        from app.models.promotion import Promotion
        from tests.conftest import utc_dt
        # Add a second active promo for p2 so one is eligible after removing promo_pct
        second = Promotion(
            id="promo_pct2",
            description="5% Extra Off",
            type="PERCENTAGE",
            value=5,
            start_date=utc_dt(days=-1),
            end_date=utc_dt(days=10),
            applicable_product_ids=["p2"],
        )
        db.add(second)
        db.commit()

        cart = service.add_item(CartItemIn(product_id="p2", quantity=1))
        item_id = cart.items[0].id
        # Switch to manual mode: remove promo_pct → it goes to eligible
        service.remove_promotion(item_id, "promo_pct")
        # Now apply it back
        cart = service.apply_promotion(item_id, "promo_pct")
        applied_ids = {p.id for p in cart.items[0].applied_promotions}
        assert "promo_pct" in applied_ids

    def test_apply_already_applied_raises_400(self, service, products, promotions):
        cart = service.add_item(CartItemIn(product_id="p2", quantity=1))
        item_id = cart.items[0].id
        with pytest.raises(HTTPException) as exc:
            service.apply_promotion(item_id, "promo_pct")
        assert exc.value.status_code == 400

    def test_apply_non_applicable_promo_raises_400(self, service, products, promotions):
        # p5 (Chicken Breast) — promo_pct applies to dairy only
        cart = service.add_item(CartItemIn(product_id="p5", quantity=1))
        item_id = cart.items[0].id
        with pytest.raises(HTTPException) as exc:
            service.apply_promotion(item_id, "promo_pct")
        assert exc.value.status_code == 400

    def test_apply_nonexistent_promo_raises_404(self, service, products):
        cart = service.add_item(CartItemIn(product_id="p2", quantity=1))
        item_id = cart.items[0].id
        with pytest.raises(HTTPException) as exc:
            service.apply_promotion(item_id, "promo_does_not_exist")
        assert exc.value.status_code == 404

    def test_remove_promotion_moves_to_eligible(self, service, products, promotions):
        cart = service.add_item(CartItemIn(product_id="p2", quantity=1))
        item_id = cart.items[0].id
        cart = service.remove_promotion(item_id, "promo_pct")
        item = cart.items[0]
        applied_ids = {p.id for p in item.applied_promotions}
        eligible_ids = {p.id for p in item.eligible_promotions}
        assert "promo_pct" not in applied_ids
        assert "promo_pct" in eligible_ids

    def test_remove_unapplied_promo_raises_400(self, service, products, promotions):
        cart = service.add_item(CartItemIn(product_id="p2", quantity=1))
        item_id = cart.items[0].id
        # promo_expired is not active — cannot be in the applied list
        with pytest.raises(HTTPException) as exc:
            service.remove_promotion(item_id, "promo_expired")
        assert exc.value.status_code == 400

    def test_remove_item_not_found_raises_404(self, service, products):
        with pytest.raises(HTTPException) as exc:
            service.remove_promotion(9999, "promo_pct")
        assert exc.value.status_code == 404

"""
API integration tests via FastAPI TestClient.
Covers all routes end-to-end against an in-memory SQLite database.
"""
import pytest
from tests.conftest import utc_dt


# ── /products ─────────────────────────────────────────────────────────────────

class TestProductsAPI:
    def test_list_all_products(self, client, products):
        res = client.get("/products")
        assert res.status_code == 200
        assert len(res.json()) == len(products)

    def test_filter_by_category(self, client, products):
        res = client.get("/products?category=dairy")
        assert res.status_code == 200
        data = res.json()
        assert all(p["category"] == "dairy" for p in data)
        assert len(data) == 2  # p2, p3

    def test_filter_unknown_category_returns_empty(self, client, products):
        res = client.get("/products?category=nonexistent")
        assert res.status_code == 200
        assert res.json() == []

    def test_get_single_product(self, client, products):
        res = client.get("/products/p2")
        assert res.status_code == 200
        data = res.json()
        assert data["id"] == "p2"
        assert data["name"] == "Whole Milk"
        assert data["price"] == 4.99

    def test_get_nonexistent_product_returns_404(self, client, products):
        res = client.get("/products/p999")
        assert res.status_code == 404

    def test_product_schema_fields(self, client, products):
        res = client.get("/products/p2")
        data = res.json()
        assert set(data.keys()) >= {"id", "name", "price", "inventory", "category"}


# ── /promotions ───────────────────────────────────────────────────────────────

class TestPromotionsAPI:
    def test_list_promotions(self, client, promotions):
        res = client.get("/promotions")
        assert res.status_code == 200
        assert len(res.json()) == len(promotions)

    def test_active_promotion_status(self, client, promotions):
        res = client.get("/promotions")
        statuses = {p["id"]: p["status"] for p in res.json()}
        assert statuses["promo_pct"] == "active"

    def test_expired_promotion_status(self, client, promotions):
        res = client.get("/promotions")
        statuses = {p["id"]: p["status"] for p in res.json()}
        assert statuses["promo_expired"] == "expired"

    def test_upcoming_promotion_status(self, client, promotions):
        res = client.get("/promotions")
        statuses = {p["id"]: p["status"] for p in res.json()}
        assert statuses["promo_future"] == "upcoming"

    def test_promotion_schema_fields(self, client, promotions):
        res = client.get("/promotions")
        promo = res.json()[0]
        assert set(promo.keys()) >= {
            "id", "description", "type", "value",
            "start_date", "end_date", "applicable_product_ids", "status"
        }


# ── GET /cart ─────────────────────────────────────────────────────────────────

class TestGetCartAPI:
    def test_empty_cart(self, client, products):
        res = client.get("/cart")
        assert res.status_code == 200
        data = res.json()
        assert data["items"] == []
        assert data["total"] == 0.0
        assert data["subtotal"] == 0.0

    def test_cart_schema_fields(self, client, products):
        res = client.get("/cart")
        data = res.json()
        assert set(data.keys()) >= {
            "id", "items", "subtotal", "total_discount",
            "total", "delivery_time", "warnings", "inventory_warnings"
        }

    def test_delivery_time_returned_in_response(self, client, products):
        delivery = utc_dt(days=5).strftime("%Y-%m-%dT%H:%M:%SZ")
        res = client.get(f"/cart?delivery_time={delivery}")
        assert res.status_code == 200
        assert res.json()["delivery_time"] is not None


# ── POST /cart/items ──────────────────────────────────────────────────────────

class TestAddItemAPI:
    def test_add_item_returns_201(self, client, products):
        res = client.post("/cart/items", json={"product_id": "p2", "quantity": 2})
        assert res.status_code == 201

    def test_added_item_appears_in_cart(self, client, products):
        res = client.post("/cart/items", json={"product_id": "p2", "quantity": 2})
        data = res.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["product_id"] == "p2"
        assert data["items"][0]["quantity"] == 2

    def test_adding_same_product_increments_quantity(self, client, products):
        client.post("/cart/items", json={"product_id": "p2", "quantity": 2})
        res = client.post("/cart/items", json={"product_id": "p2", "quantity": 3})
        assert res.json()["items"][0]["quantity"] == 5

    def test_invalid_product_returns_404(self, client, products):
        res = client.post("/cart/items", json={"product_id": "p999", "quantity": 1})
        assert res.status_code == 404

    def test_zero_quantity_returns_422(self, client, products):
        res = client.post("/cart/items", json={"product_id": "p2", "quantity": 0})
        assert res.status_code == 422

    def test_negative_quantity_returns_422(self, client, products):
        res = client.post("/cart/items", json={"product_id": "p2", "quantity": -1})
        assert res.status_code == 422

    def test_exceeds_inventory_returns_400(self, client, products):
        res = client.post("/cart/items", json={"product_id": "p7", "quantity": 999})
        assert res.status_code == 400
        assert "Insufficient inventory" in res.json()["detail"]

    def test_promo_applied_in_response(self, client, products, promotions):
        res = client.post("/cart/items", json={"product_id": "p2", "quantity": 2})
        item = res.json()["items"][0]
        assert len(item["applied_promotions"]) > 0
        assert item["total_item_discount"] > 0

    def test_cart_item_schema(self, client, products):
        res = client.post("/cart/items", json={"product_id": "p2", "quantity": 1})
        item = res.json()["items"][0]
        assert set(item.keys()) >= {
            "id", "product_id", "product_name", "quantity",
            "unit_price", "unit_price_at_add", "applied_promotions",
            "eligible_promotions", "total_item_discount", "line_total"
        }


# ── PATCH /cart/items/:id ─────────────────────────────────────────────────────

class TestUpdateItemAPI:
    def test_update_quantity(self, client, products):
        add_res = client.post("/cart/items", json={"product_id": "p2", "quantity": 1})
        item_id = add_res.json()["items"][0]["id"]
        res = client.patch(f"/cart/items/{item_id}", json={"quantity": 4})
        assert res.status_code == 200
        assert res.json()["items"][0]["quantity"] == 4

    def test_zero_quantity_returns_422(self, client, products):
        add_res = client.post("/cart/items", json={"product_id": "p2", "quantity": 1})
        item_id = add_res.json()["items"][0]["id"]
        res = client.patch(f"/cart/items/{item_id}", json={"quantity": 0})
        assert res.status_code == 422

    def test_exceeds_inventory_returns_400(self, client, products):
        add_res = client.post("/cart/items", json={"product_id": "p7", "quantity": 1})
        item_id = add_res.json()["items"][0]["id"]
        res = client.patch(f"/cart/items/{item_id}", json={"quantity": 999})
        assert res.status_code == 400

    def test_nonexistent_item_returns_404(self, client, products):
        res = client.patch("/cart/items/9999", json={"quantity": 1})
        assert res.status_code == 404

    def test_totals_recalculate_after_update(self, client, products, promotions):
        add_res = client.post("/cart/items", json={"product_id": "p2", "quantity": 1})
        item_id = add_res.json()["items"][0]["id"]
        res = client.patch(f"/cart/items/{item_id}", json={"quantity": 3})
        # 20% of 4.99 × 3 = 2.994 → ~3.00
        assert res.json()["total_discount"] == pytest.approx(3.00, abs=0.01)


# ── DELETE /cart/items/:id ────────────────────────────────────────────────────

class TestDeleteItemAPI:
    def test_delete_removes_item(self, client, products):
        add_res = client.post("/cart/items", json={"product_id": "p2", "quantity": 1})
        item_id = add_res.json()["items"][0]["id"]
        res = client.delete(f"/cart/items/{item_id}")
        assert res.status_code == 200
        assert res.json()["items"] == []

    def test_nonexistent_item_returns_404(self, client, products):
        res = client.delete("/cart/items/9999")
        assert res.status_code == 404

    def test_other_items_unaffected(self, client, products):
        client.post("/cart/items", json={"product_id": "p2", "quantity": 1})
        add_res = client.post("/cart/items", json={"product_id": "p3", "quantity": 2})
        item_id = add_res.json()["items"][0]["id"]
        res = client.delete(f"/cart/items/{item_id}")
        assert len(res.json()["items"]) == 1


# ── DELETE /cart ──────────────────────────────────────────────────────────────

class TestClearCartAPI:
    def test_clears_all_items(self, client, products):
        client.post("/cart/items", json={"product_id": "p2", "quantity": 1})
        client.post("/cart/items", json={"product_id": "p3", "quantity": 2})
        res = client.delete("/cart")
        assert res.status_code == 200
        assert res.json()["items"] == []
        assert res.json()["total"] == 0.0

    def test_clear_empty_cart_is_safe(self, client, products):
        res = client.delete("/cart")
        assert res.status_code == 200


# ── POST /cart/items/:id/promotions ──────────────────────────────────────────

class TestApplyPromoAPI:
    def test_apply_promotion(self, client, products, promotions, db):
        from app.models.promotion import Promotion
        second = Promotion(
            id="promo_pct2",
            description="5% Extra",
            type="PERCENTAGE",
            value=5,
            start_date=utc_dt(days=-1),
            end_date=utc_dt(days=10),
            applicable_product_ids=["p2"],
        )
        db.add(second)
        db.commit()

        add_res = client.post("/cart/items", json={"product_id": "p2", "quantity": 1})
        item_id = add_res.json()["items"][0]["id"]
        # Remove one to enter manual mode with eligible promos
        client.delete(f"/cart/items/{item_id}/promotions/promo_pct")
        res = client.post(
            f"/cart/items/{item_id}/promotions",
            json={"promotion_id": "promo_pct"}
        )
        assert res.status_code == 200
        applied_ids = {p["id"] for p in res.json()["items"][0]["applied_promotions"]}
        assert "promo_pct" in applied_ids

    def test_apply_nonexistent_promo_returns_404(self, client, products):
        add_res = client.post("/cart/items", json={"product_id": "p2", "quantity": 1})
        item_id = add_res.json()["items"][0]["id"]
        res = client.post(
            f"/cart/items/{item_id}/promotions",
            json={"promotion_id": "nonexistent"}
        )
        assert res.status_code == 404

    def test_apply_non_applicable_promo_returns_400(self, client, products, promotions):
        # p5 not in promo_pct's applicable_product_ids
        add_res = client.post("/cart/items", json={"product_id": "p5", "quantity": 1})
        item_id = add_res.json()["items"][0]["id"]
        res = client.post(
            f"/cart/items/{item_id}/promotions",
            json={"promotion_id": "promo_pct"}
        )
        assert res.status_code == 400


# ── DELETE /cart/items/:id/promotions/:promo_id ───────────────────────────────

class TestRemovePromoAPI:
    def test_remove_promotion(self, client, products, promotions):
        add_res = client.post("/cart/items", json={"product_id": "p2", "quantity": 1})
        item_id = add_res.json()["items"][0]["id"]
        res = client.delete(f"/cart/items/{item_id}/promotions/promo_pct")
        assert res.status_code == 200
        applied_ids = {p["id"] for p in res.json()["items"][0]["applied_promotions"]}
        assert "promo_pct" not in applied_ids

    def test_remove_unapplied_promo_returns_400(self, client, products, promotions):
        add_res = client.post("/cart/items", json={"product_id": "p2", "quantity": 1})
        item_id = add_res.json()["items"][0]["id"]
        res = client.delete(f"/cart/items/{item_id}/promotions/promo_expired")
        assert res.status_code == 400

    def test_remove_promo_nonexistent_item_returns_404(self, client, products):
        res = client.delete("/cart/items/9999/promotions/promo_pct")
        assert res.status_code == 404


# ── Delivery-aware pricing ────────────────────────────────────────────────────

class TestDeliveryAwarePricing:
    def test_warning_when_promo_expires_before_delivery(self, client, products, db):
        from app.models.promotion import Promotion
        promo = Promotion(
            id="short_promo",
            description="Short Live Sale",
            type="PERCENTAGE",
            value=15,
            start_date=utc_dt(days=-1),
            end_date=utc_dt(days=2),
            applicable_product_ids=["p2"],
        )
        db.add(promo)
        db.commit()

        client.post("/cart/items", json={"product_id": "p2", "quantity": 1})
        delivery = utc_dt(days=10).strftime("%Y-%m-%dT%H:%M:%SZ")
        res = client.get(f"/cart?delivery_time={delivery}")
        assert res.status_code == 200
        assert any("short_promo" in w for w in res.json()["warnings"])

    def test_no_warning_when_promo_covers_delivery(self, client, products, promotions):
        client.post("/cart/items", json={"product_id": "p2", "quantity": 1})
        delivery = utc_dt(days=5).strftime("%Y-%m-%dT%H:%M:%SZ")  # promo_pct ends in 30 days
        res = client.get(f"/cart?delivery_time={delivery}")
        assert res.status_code == 200
        assert res.json()["warnings"] == []

    def test_inventory_warning_included_with_delivery_time(self, client, products, db):
        from app.models.product import Product
        client.post("/cart/items", json={"product_id": "p2", "quantity": 5})
        p = db.get(Product, "p2")
        p.inventory = 1
        db.commit()
        delivery = utc_dt(days=5).strftime("%Y-%m-%dT%H:%M:%SZ")
        res = client.get(f"/cart?delivery_time={delivery}")
        assert res.status_code == 200
        assert len(res.json()["inventory_warnings"]) == 1

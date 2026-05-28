"""
Tests for promotion strategy pattern and PromotionService logic.
"""
import pytest
from datetime import timezone

from app.promotions.percentage import PercentagePromotion
from app.promotions.fixed import FixedPromotion
from app.promotions.registry import get_strategy, PROMOTION_REGISTRY
from app.repositories.promotion_repo import PromotionRepository
from app.services.promotion_service import PromotionService
from tests.conftest import utc_dt


# ── Strategy: PercentagePromotion ─────────────────────────────────────────────

class TestPercentagePromotion:
    def test_basic_discount(self):
        promo = PercentagePromotion(20)
        assert promo.apply(10.00, 1) == 2.00

    def test_multiple_quantity(self):
        promo = PercentagePromotion(10)
        assert promo.apply(5.00, 3) == 1.50

    def test_rounding(self):
        promo = PercentagePromotion(20)
        # 20% of 4.99 * 2 = 1.996 → rounds to 2.00
        assert promo.apply(4.99, 2) == 2.00

    def test_zero_percent(self):
        promo = PercentagePromotion(0)
        assert promo.apply(100.00, 5) == 0.00

    def test_hundred_percent(self):
        promo = PercentagePromotion(100)
        assert promo.apply(9.99, 1) == 9.99


# ── Strategy: FixedPromotion ──────────────────────────────────────────────────

class TestFixedPromotion:
    def test_basic_discount(self):
        promo = FixedPromotion(2)
        assert promo.apply(8.99, 1) == 2.00

    def test_multiple_quantity(self):
        promo = FixedPromotion(2)
        assert promo.apply(8.99, 3) == 6.00

    def test_floor_at_item_total(self):
        # Discount ($10) exceeds item total ($1.99 * 1 = $1.99) → capped at $1.99
        promo = FixedPromotion(10)
        assert promo.apply(1.99, 1) == 1.99

    def test_floor_multi_quantity(self):
        # $5 off × 2 = $10, item total = 2 × $3 = $6 → capped at $6
        promo = FixedPromotion(5)
        assert promo.apply(3.00, 2) == 6.00

    def test_exact_match(self):
        promo = FixedPromotion(5)
        assert promo.apply(5.00, 1) == 5.00


# ── Registry ──────────────────────────────────────────────────────────────────

class TestRegistry:
    def test_percentage_key(self):
        strategy = get_strategy("PERCENTAGE", 20)
        assert isinstance(strategy, PercentagePromotion)

    def test_fixed_key(self):
        strategy = get_strategy("FIXED", 2)
        assert isinstance(strategy, FixedPromotion)

    def test_unknown_type_raises(self):
        with pytest.raises(ValueError, match="Unknown promotion type"):
            get_strategy("BOGO", 1)

    def test_registry_contains_expected_types(self):
        assert "PERCENTAGE" in PROMOTION_REGISTRY
        assert "FIXED" in PROMOTION_REGISTRY


# ── PromotionService ──────────────────────────────────────────────────────────

class TestPromotionService:
    @pytest.fixture
    def service(self, db):
        return PromotionService(PromotionRepository(db))

    def test_active_promo_applied_auto_mode(self, service, products, promotions):
        product = products["p2"]
        result = service.resolve_promotions(product, 2, None, None)
        applied_ids = {r.promotion.id for r in result.applied}
        assert "promo_pct" in applied_ids

    def test_expired_promo_not_applied(self, service, products, promotions):
        product = products["p2"]
        result = service.resolve_promotions(product, 1, None, None)
        applied_ids = {r.promotion.id for r in result.applied}
        assert "promo_expired" not in applied_ids

    def test_future_promo_not_applied(self, service, products, promotions):
        product = products["p2"]
        result = service.resolve_promotions(product, 1, None, None)
        applied_ids = {r.promotion.id for r in result.applied}
        assert "promo_future" not in applied_ids

    def test_multiple_active_promos_all_applied_auto(self, service, products, promotions, db):
        from app.models.promotion import Promotion
        # Add a second active promo for p2
        second = Promotion(
            id="promo_pct2",
            description="5% Extra Off Dairy",
            type="PERCENTAGE",
            value=5,
            start_date=utc_dt(days=-1),
            end_date=utc_dt(days=10),
            applicable_product_ids=["p2"],
        )
        db.add(second)
        db.commit()

        product = products["p2"]
        result = service.resolve_promotions(product, 1, None, None)
        applied_ids = {r.promotion.id for r in result.applied}
        # Both active promos should stack
        assert "promo_pct" in applied_ids
        assert "promo_pct2" in applied_ids

    def test_no_promos_for_unrelated_product(self, service, products, promotions):
        product = products["p5"]  # Chicken Breast — no promo targets it
        result = service.resolve_promotions(product, 1, None, None)
        assert result.applied == []
        assert result.eligible == []

    def test_manual_mode_applies_only_selected(self, service, products, promotions, db):
        from app.models.promotion import Promotion
        second = Promotion(
            id="promo_pct2",
            description="5% Extra Off Dairy",
            type="PERCENTAGE",
            value=5,
            start_date=utc_dt(days=-1),
            end_date=utc_dt(days=10),
            applicable_product_ids=["p2"],
        )
        db.add(second)
        db.commit()

        product = products["p2"]
        result = service.resolve_promotions(product, 1, None, ["promo_pct"])
        applied_ids = {r.promotion.id for r in result.applied}
        eligible_ids = {r.promotion.id for r in result.eligible}
        assert "promo_pct" in applied_ids
        assert "promo_pct2" in eligible_ids

    def test_manual_mode_empty_list_applies_nothing(self, service, products, promotions):
        product = products["p2"]
        result = service.resolve_promotions(product, 1, None, [])
        assert result.applied == []
        assert len(result.eligible) > 0

    def test_delivery_warning_when_promo_expires_before_delivery(self, service, products, db):
        from app.models.promotion import Promotion
        # Promo ends in 3 days, delivery is in 10 days
        promo = Promotion(
            id="promo_expiring_soon",
            description="Expiring Soon",
            type="PERCENTAGE",
            value=10,
            start_date=utc_dt(days=-1),
            end_date=utc_dt(days=3),
            applicable_product_ids=["p2"],
        )
        db.add(promo)
        db.commit()

        product = products["p2"]
        delivery = utc_dt(days=10)
        result = service.resolve_promotions(product, 1, delivery, None)

        assert len(result.warnings) > 0
        assert "promo_expiring_soon" in result.warnings[0]

    def test_no_warning_when_promo_covers_delivery(self, service, products, promotions):
        product = products["p2"]
        delivery = utc_dt(days=5)  # promo_pct ends in 30 days — covers it
        result = service.resolve_promotions(product, 1, delivery, None)
        assert result.warnings == []

    def test_discount_amount_correct(self, service, products, promotions):
        product = products["p2"]  # price = 4.99
        result = service.resolve_promotions(product, 2, None, None)
        applied = {r.promotion.id: r for r in result.applied}
        # 20% of 4.99 * 2 = 2.00 (rounded)
        assert applied["promo_pct"].discount == pytest.approx(2.00, abs=0.01)

    def test_get_all_with_status(self, service, promotions):
        statuses = {p.id: s for p, s in service.get_all_with_status()}
        assert statuses["promo_pct"] == "active"
        assert statuses["promo_expired"] == "expired"
        assert statuses["promo_future"] == "upcoming"

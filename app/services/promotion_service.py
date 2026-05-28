from dataclasses import dataclass, field
from datetime import datetime, timezone
from app.models.product import Product
from app.models.promotion import Promotion
from app.repositories.promotion_repo import PromotionRepository
from app.promotions.registry import get_strategy


@dataclass
class PromoResult:
    promotion: Promotion
    discount: float
    warning: str | None = None


@dataclass
class PromotionSummaryResult:
    applied: list[PromoResult] = field(default_factory=list)
    eligible: list[PromoResult] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def total_discount(self) -> float:
        return round(sum(r.discount for r in self.applied), 2)


class PromotionService:
    def __init__(self, promotion_repo: PromotionRepository):
        self.promotion_repo = promotion_repo

    def _is_active(self, promo: Promotion, reference_time: datetime) -> bool:
        start = promo.start_date
        end = promo.end_date
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)
        if reference_time.tzinfo is None:
            reference_time = reference_time.replace(tzinfo=timezone.utc)
        return start <= reference_time <= end

    def _calculate_discount(self, promo: Promotion, unit_price: float, quantity: int) -> float:
        strategy = get_strategy(promo.type, promo.value)
        return strategy.apply(unit_price, quantity)

    def resolve_promotions(
        self,
        product: Product,
        quantity: int,
        delivery_time: datetime | None,
        applied_promotion_ids: list[str] | None,
    ) -> PromotionSummaryResult:
        """
        Resolve which promotions are applied vs eligible for a cart item.

        applied_promotion_ids=None  → auto mode: apply all active eligible promos
        applied_promotion_ids=[]    → user opted out of all promos
        applied_promotion_ids=[ids] → apply only the listed promo IDs
        """
        now = datetime.now(timezone.utc)
        reference_time = delivery_time if delivery_time else now

        all_promos = self.promotion_repo.get_all()
        applicable = [p for p in all_promos if product.id in p.applicable_product_ids]

        warnings: list[str] = []

        # Promotions active right now but expiring before delivery
        if delivery_time:
            for promo in applicable:
                if self._is_active(promo, now) and not self._is_active(promo, delivery_time):
                    end_str = promo.end_date.strftime("%Y-%m-%d")
                    del_str = delivery_time.strftime("%Y-%m-%d")
                    warnings.append(
                        f"{promo.id} '{promo.description}' expires {end_str}, "
                        f"before delivery on {del_str} — discount not applied"
                    )

        # Active at the reference time (today or delivery date)
        active = [p for p in applicable if self._is_active(p, reference_time)]

        result = PromotionSummaryResult(warnings=warnings)

        if applied_promotion_ids is None:
            # Auto mode — apply all active promos
            for promo in active:
                discount = self._calculate_discount(promo, product.price, quantity)
                result.applied.append(PromoResult(promotion=promo, discount=discount))
        else:
            # Manual mode — split into applied vs eligible
            applied_ids_set = set(applied_promotion_ids)
            for promo in active:
                discount = self._calculate_discount(promo, product.price, quantity)
                if promo.id in applied_ids_set:
                    result.applied.append(PromoResult(promotion=promo, discount=discount))
                else:
                    result.eligible.append(PromoResult(promotion=promo, discount=discount))

        return result

    def get_all_with_status(self) -> list[tuple[Promotion, str]]:
        now = datetime.now(timezone.utc)
        result = []
        for promo in self.promotion_repo.get_all():
            if self._is_active(promo, now):
                status = "active"
            else:
                end = promo.end_date
                if end.tzinfo is None:
                    end = end.replace(tzinfo=timezone.utc)
                status = "expired" if end < now else "upcoming"
            result.append((promo, status))
        return result

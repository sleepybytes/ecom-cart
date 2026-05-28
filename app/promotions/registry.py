from app.promotions.base import PromotionStrategy
from app.promotions.percentage import PercentagePromotion
from app.promotions.fixed import FixedPromotion

PROMOTION_REGISTRY: dict[str, type[PromotionStrategy]] = {
    "PERCENTAGE": PercentagePromotion,
    "FIXED": FixedPromotion,
}


def get_strategy(promo_type: str, value: float) -> PromotionStrategy:
    cls = PROMOTION_REGISTRY.get(promo_type)
    if not cls:
        raise ValueError(f"Unknown promotion type: {promo_type}")
    return cls(value)

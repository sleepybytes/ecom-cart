from app.promotions.base import PromotionStrategy


class FixedPromotion(PromotionStrategy):
    def __init__(self, value: float):
        self.discount = value

    def apply(self, unit_price: float, quantity: int) -> float:
        return round(min(self.discount * quantity, unit_price * quantity), 2)

from app.promotions.base import PromotionStrategy


class PercentagePromotion(PromotionStrategy):
    def __init__(self, value: float):
        self.rate = value / 100

    def apply(self, unit_price: float, quantity: int) -> float:
        return round(unit_price * self.rate * quantity, 2)

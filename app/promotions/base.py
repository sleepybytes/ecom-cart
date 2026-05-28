from abc import ABC, abstractmethod


class PromotionStrategy(ABC):
    @abstractmethod
    def apply(self, unit_price: float, quantity: int) -> float:
        """Returns total discount amount for this line item."""

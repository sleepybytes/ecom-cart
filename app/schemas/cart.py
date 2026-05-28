from datetime import datetime
from pydantic import BaseModel, field_validator


class CartItemIn(BaseModel):
    product_id: str
    quantity: int

    @field_validator("quantity")
    @classmethod
    def quantity_must_be_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError("Quantity must be at least 1")
        return v


class CartItemUpdate(BaseModel):
    quantity: int

    @field_validator("quantity")
    @classmethod
    def quantity_must_be_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError("Quantity must be at least 1. Use DELETE to remove item.")
        return v


class PromoApplyIn(BaseModel):
    promotion_id: str


class AppliedPromotion(BaseModel):
    id: str
    description: str
    type: str
    discount_per_unit: float
    total_discount: float


class EligiblePromotion(BaseModel):
    """A promotion that is active and applicable to this product but not currently applied."""
    id: str
    description: str
    type: str
    value: float
    discount_amount: float  # calculated discount for current quantity


class CartItemOut(BaseModel):
    id: int
    product_id: str
    product_name: str
    quantity: int
    unit_price: float
    unit_price_at_add: float
    applied_promotions: list[AppliedPromotion]
    eligible_promotions: list[EligiblePromotion]
    total_item_discount: float
    line_total: float


class CartOut(BaseModel):
    id: int
    items: list[CartItemOut]
    subtotal: float
    total_discount: float
    total: float
    delivery_time: datetime | None
    warnings: list[str]
    inventory_warnings: list[str]

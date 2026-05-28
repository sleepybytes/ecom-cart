from datetime import datetime
from fastapi import HTTPException
from app.models.cart import CartItem
from app.repositories.cart_repo import CartRepository
from app.repositories.product_repo import ProductRepository
from app.repositories.promotion_repo import PromotionRepository
from app.schemas.cart import (
    CartOut, CartItemOut, CartItemIn, CartItemUpdate,
    AppliedPromotion, EligiblePromotion,
)
from app.services.promotion_service import PromotionService
from app.services.inventory_service import InventoryService


class CartService:
    def __init__(
        self,
        cart_repo: CartRepository,
        product_repo: ProductRepository,
        promotion_service: PromotionService,
        inventory_service: InventoryService,
    ):
        self.cart_repo = cart_repo
        self.product_repo = product_repo
        self.promotion_service = promotion_service
        self.inventory_service = inventory_service

    def get_cart(self, delivery_time: datetime | None) -> CartOut:
        cart = self.cart_repo.get_or_create()
        items_out: list[CartItemOut] = []
        warnings: list[str] = []
        inventory_warnings: list[str] = []

        for item in cart.items:
            product = self.product_repo.get(item.product_id)
            if not product:
                continue

            if product.inventory < item.quantity:
                inventory_warnings.append(
                    f"'{product.name}': requested {item.quantity}, only {product.inventory} in stock"
                )

            summary = self.promotion_service.resolve_promotions(
                product,
                item.quantity,
                delivery_time,
                item.applied_promotion_ids,
            )
            warnings.extend(summary.warnings)

            applied_out = [
                AppliedPromotion(
                    id=r.promotion.id,
                    description=r.promotion.description,
                    type=r.promotion.type,
                    discount_per_unit=round(r.discount / item.quantity, 2),
                    total_discount=r.discount,
                )
                for r in summary.applied
            ]

            eligible_out = [
                EligiblePromotion(
                    id=r.promotion.id,
                    description=r.promotion.description,
                    type=r.promotion.type,
                    value=r.promotion.value,
                    discount_amount=r.discount,
                )
                for r in summary.eligible
            ]

            total_item_discount = summary.total_discount
            line_total = round(item.unit_price_at_add * item.quantity - total_item_discount, 2)

            items_out.append(CartItemOut(
                id=item.id,
                product_id=item.product_id,
                product_name=product.name,
                quantity=item.quantity,
                unit_price=product.price,
                unit_price_at_add=item.unit_price_at_add,
                applied_promotions=applied_out,
                eligible_promotions=eligible_out,
                total_item_discount=total_item_discount,
                line_total=line_total,
            ))

        subtotal = round(sum(i.unit_price_at_add * i.quantity for i in cart.items), 2)
        total_discount = round(sum(i.total_item_discount for i in items_out), 2)
        total = round(subtotal - total_discount, 2)

        return CartOut(
            id=cart.id,
            items=items_out,
            subtotal=subtotal,
            total_discount=total_discount,
            total=total,
            delivery_time=delivery_time,
            warnings=warnings,
            inventory_warnings=inventory_warnings,
        )

    def add_item(self, payload: CartItemIn) -> CartOut:
        product = self.product_repo.get(payload.product_id)
        if not product:
            raise HTTPException(status_code=404, detail=f"Product '{payload.product_id}' not found")

        cart = self.cart_repo.get_or_create()
        existing = self.cart_repo.get_item_by_product(cart.id, payload.product_id)
        new_quantity = (existing.quantity if existing else 0) + payload.quantity

        try:
            self.inventory_service.validate(payload.product_id, new_quantity)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        if existing:
            self.cart_repo.update_item_quantity(existing, new_quantity)
        else:
            item = CartItem(
                cart_id=cart.id,
                product_id=payload.product_id,
                quantity=payload.quantity,
                unit_price_at_add=product.price,
                applied_promotion_ids=None,  # auto mode by default
            )
            self.cart_repo.add_item(item)

        return self.get_cart(None)

    def update_item(self, item_id: int, payload: CartItemUpdate) -> CartOut:
        item = self.cart_repo.get_item(item_id)
        if not item:
            raise HTTPException(status_code=404, detail=f"Cart item {item_id} not found")

        try:
            self.inventory_service.validate(item.product_id, payload.quantity)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        self.cart_repo.update_item_quantity(item, payload.quantity)
        return self.get_cart(None)

    def delete_item(self, item_id: int) -> CartOut:
        item = self.cart_repo.get_item(item_id)
        if not item:
            raise HTTPException(status_code=404, detail=f"Cart item {item_id} not found")
        self.cart_repo.delete_item(item)
        return self.get_cart(None)

    def clear_cart(self) -> CartOut:
        cart = self.cart_repo.get_or_create()
        self.cart_repo.clear_cart(cart)
        return self.get_cart(None)

    def apply_promotion(self, item_id: int, promotion_id: str) -> CartOut:
        item = self.cart_repo.get_item(item_id)
        if not item:
            raise HTTPException(status_code=404, detail=f"Cart item {item_id} not found")

        product = self.product_repo.get(item.product_id)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        # Verify the promotion is valid and applicable to this product
        promo = self.promotion_service.promotion_repo.get(promotion_id)
        if not promo:
            raise HTTPException(status_code=404, detail=f"Promotion '{promotion_id}' not found")
        if product.id not in promo.applicable_product_ids:
            raise HTTPException(
                status_code=400,
                detail=f"Promotion '{promotion_id}' is not applicable to '{product.name}'",
            )

        # Compute effective applied list first (auto mode → seed from active promos)
        from datetime import timezone
        from datetime import datetime as dt
        if item.applied_promotion_ids is None:
            now = dt.now(timezone.utc)
            all_promos = self.promotion_service.promotion_repo.get_all()
            current_ids: list[str] = [
                p.id for p in all_promos
                if product.id in p.applicable_product_ids
                and self.promotion_service._is_active(p, now)
            ]
        else:
            current_ids = list(item.applied_promotion_ids)

        if promotion_id in current_ids:
            raise HTTPException(status_code=400, detail=f"Promotion '{promotion_id}' is already applied")

        current_ids.append(promotion_id)

        self.cart_repo.update_item_promotions(item, current_ids)
        return self.get_cart(None)

    def remove_promotion(self, item_id: int, promotion_id: str) -> CartOut:
        item = self.cart_repo.get_item(item_id)
        if not item:
            raise HTTPException(status_code=404, detail=f"Cart item {item_id} not found")

        product = self.product_repo.get(item.product_id)

        # If auto mode, seed the list from all currently active promos then remove the target
        if item.applied_promotion_ids is None:
            from datetime import timezone
            from datetime import datetime as dt
            now = dt.now(timezone.utc)
            all_promos = self.promotion_service.promotion_repo.get_all()
            current_ids = [
                p.id for p in all_promos
                if product and product.id in p.applicable_product_ids
                and self.promotion_service._is_active(p, now)
            ]
        else:
            current_ids = list(item.applied_promotion_ids)

        if promotion_id not in current_ids:
            raise HTTPException(
                status_code=400,
                detail=f"Promotion '{promotion_id}' is not currently applied to this item",
            )

        current_ids.remove(promotion_id)
        self.cart_repo.update_item_promotions(item, current_ids)
        return self.get_cart(None)

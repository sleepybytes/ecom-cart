from sqlalchemy import select
from app.models.cart import Cart, CartItem
from app.repositories.base_repo import BaseRepository


class CartRepository(BaseRepository[Cart]):
    def __init__(self, db):
        super().__init__(Cart, db)

    def get_or_create(self) -> Cart:
        cart = self.db.get(Cart, 1)
        if not cart:
            cart = Cart(id=1)
            self.db.add(cart)
            self.db.commit()
            self.db.refresh(cart)
        return cart

    def get_item(self, item_id: int) -> CartItem | None:
        return self.db.get(CartItem, item_id)

    def get_item_by_product(self, cart_id: int, product_id: str) -> CartItem | None:
        return self.db.execute(
            select(CartItem).where(
                CartItem.cart_id == cart_id,
                CartItem.product_id == product_id,
            )
        ).scalar_one_or_none()

    def add_item(self, item: CartItem) -> CartItem:
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def update_item_quantity(self, item: CartItem, quantity: int) -> CartItem:
        item.quantity = quantity
        self.db.commit()
        self.db.refresh(item)
        return item

    def delete_item(self, item: CartItem) -> None:
        self.db.delete(item)
        self.db.commit()

    def update_item_promotions(self, item: CartItem, promotion_ids: list[str]) -> CartItem:
        item.applied_promotion_ids = promotion_ids
        self.db.commit()
        self.db.refresh(item)
        return item

    def clear_cart(self, cart: Cart) -> None:
        for item in list(cart.items):
            self.db.delete(item)
        self.db.commit()
        self.db.refresh(cart)

from app.repositories.product_repo import ProductRepository


class InventoryService:
    def __init__(self, product_repo: ProductRepository):
        self.product_repo = product_repo

    def validate(self, product_id: str, quantity: int) -> None:
        """Raises ValueError if inventory is insufficient."""
        product = self.product_repo.get(product_id)
        if not product:
            raise ValueError(f"Product '{product_id}' not found")
        if product.inventory < quantity:
            raise ValueError(
                f"Insufficient inventory for '{product.name}'. "
                f"Requested: {quantity}, Available: {product.inventory}"
            )

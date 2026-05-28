from sqlalchemy import select
from app.models.product import Product
from app.repositories.base_repo import BaseRepository


class ProductRepository(BaseRepository[Product]):
    def __init__(self, db):
        super().__init__(Product, db)

    def get_by_category(self, category: str) -> list[Product]:
        return list(
            self.db.execute(
                select(Product).where(Product.category == category)
            ).scalars().all()
        )

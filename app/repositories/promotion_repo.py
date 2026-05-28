from app.models.promotion import Promotion
from app.repositories.base_repo import BaseRepository


class PromotionRepository(BaseRepository[Promotion]):
    def __init__(self, db):
        super().__init__(Promotion, db)

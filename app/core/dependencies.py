from typing import Generator
from sqlalchemy.orm import Session
from fastapi import Depends
from app.core.database import SessionLocal
from app.repositories.product_repo import ProductRepository
from app.repositories.cart_repo import CartRepository
from app.repositories.promotion_repo import PromotionRepository
from app.services.promotion_service import PromotionService
from app.services.inventory_service import InventoryService
from app.services.cart_service import CartService


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_product_repo(db: Session = Depends(get_db)) -> ProductRepository:
    return ProductRepository(db)


def get_cart_repo(db: Session = Depends(get_db)) -> CartRepository:
    return CartRepository(db)


def get_promotion_repo(db: Session = Depends(get_db)) -> PromotionRepository:
    return PromotionRepository(db)


def get_cart_service(db: Session = Depends(get_db)) -> CartService:
    product_repo = ProductRepository(db)
    cart_repo = CartRepository(db)
    promotion_repo = PromotionRepository(db)
    promotion_service = PromotionService(promotion_repo)
    inventory_service = InventoryService(product_repo)
    return CartService(cart_repo, product_repo, promotion_service, inventory_service)

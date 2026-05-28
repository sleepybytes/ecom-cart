from fastapi import APIRouter, Depends, HTTPException
from app.repositories.product_repo import ProductRepository
from app.schemas.product import ProductOut
from app.core.dependencies import get_product_repo

router = APIRouter(prefix="/products", tags=["products"])


@router.get("", response_model=list[ProductOut])
def list_products(
    category: str | None = None,
    repo: ProductRepository = Depends(get_product_repo),
):
    if category:
        return repo.get_by_category(category)
    return repo.get_all()


@router.get("/{product_id}", response_model=ProductOut)
def get_product(product_id: str, repo: ProductRepository = Depends(get_product_repo)):
    product = repo.get(product_id)
    if not product:
        raise HTTPException(status_code=404, detail=f"Product '{product_id}' not found")
    return product

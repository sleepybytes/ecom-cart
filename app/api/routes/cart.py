from datetime import datetime
from fastapi import APIRouter, Depends, Query
from app.schemas.cart import CartOut, CartItemIn, CartItemUpdate, PromoApplyIn
from app.services.cart_service import CartService
from app.core.dependencies import get_cart_service

router = APIRouter(tags=["cart"])


@router.get("/cart", response_model=CartOut)
def get_cart(
    delivery_time: datetime | None = Query(None),
    service: CartService = Depends(get_cart_service),
):
    return service.get_cart(delivery_time)


@router.post("/cart/items", response_model=CartOut, status_code=201)
def add_item(payload: CartItemIn, service: CartService = Depends(get_cart_service)):
    return service.add_item(payload)


@router.patch("/cart/items/{item_id}", response_model=CartOut)
def update_item(
    item_id: int,
    payload: CartItemUpdate,
    service: CartService = Depends(get_cart_service),
):
    return service.update_item(item_id, payload)


@router.delete("/cart/items/{item_id}", response_model=CartOut)
def delete_item(item_id: int, service: CartService = Depends(get_cart_service)):
    return service.delete_item(item_id)


@router.delete("/cart", response_model=CartOut)
def clear_cart(service: CartService = Depends(get_cart_service)):
    return service.clear_cart()


@router.post("/cart/items/{item_id}/promotions", response_model=CartOut)
def apply_promotion(
    item_id: int,
    payload: PromoApplyIn,
    service: CartService = Depends(get_cart_service),
):
    return service.apply_promotion(item_id, payload.promotion_id)


@router.delete("/cart/items/{item_id}/promotions/{promo_id}", response_model=CartOut)
def remove_promotion(
    item_id: int,
    promo_id: str,
    service: CartService = Depends(get_cart_service),
):
    return service.remove_promotion(item_id, promo_id)

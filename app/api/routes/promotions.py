from fastapi import APIRouter, Depends
from app.schemas.promotion import PromotionOut
from app.services.promotion_service import PromotionService
from app.repositories.promotion_repo import PromotionRepository
from app.core.dependencies import get_promotion_repo

router = APIRouter(prefix="/promotions", tags=["promotions"])


def get_promotion_service(repo: PromotionRepository = Depends(get_promotion_repo)) -> PromotionService:
    return PromotionService(repo)


@router.get("", response_model=list[PromotionOut])
def list_promotions(service: PromotionService = Depends(get_promotion_service)):
    result = []
    for promo, status in service.get_all_with_status():
        result.append(PromotionOut(
            id=promo.id,
            description=promo.description,
            type=promo.type,
            value=promo.value,
            start_date=promo.start_date,
            end_date=promo.end_date,
            applicable_product_ids=promo.applicable_product_ids,
            status=status,
        ))
    return result

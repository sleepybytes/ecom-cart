from datetime import datetime
from pydantic import BaseModel


class PromotionOut(BaseModel):
    id: str
    description: str
    type: str
    value: float
    start_date: datetime
    end_date: datetime
    applicable_product_ids: list[str]
    status: str

    model_config = {"from_attributes": True}

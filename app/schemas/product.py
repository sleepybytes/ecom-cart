from pydantic import BaseModel


class ProductOut(BaseModel):
    id: str
    name: str
    price: float
    inventory: int
    category: str

    model_config = {"from_attributes": True}

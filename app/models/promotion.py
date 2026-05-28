from sqlalchemy import String, Float, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.sqlite import JSON
from app.core.database import Base


class Promotion(Base):
    __tablename__ = "promotions"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    description: Mapped[str] = mapped_column(String, nullable=False)
    type: Mapped[str] = mapped_column(String, nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    start_date: Mapped[object] = mapped_column(DateTime, nullable=False)
    end_date: Mapped[object] = mapped_column(DateTime, nullable=False)
    applicable_product_ids: Mapped[object] = mapped_column(JSON, nullable=False, default=list)

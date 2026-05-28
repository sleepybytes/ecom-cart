from typing import Any, Generic, TypeVar
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.core.database import Base

T = TypeVar("T", bound=Base)


class BaseRepository(Generic[T]):
    def __init__(self, model: type[T], db: Session):
        self.model = model
        self.db = db

    def get(self, id: Any) -> T | None:
        return self.db.get(self.model, id)

    def get_all(self) -> list[T]:
        return list(self.db.execute(select(self.model)).scalars().all())

    def create(self, obj: T) -> T:
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def delete(self, obj: T) -> None:
        self.db.delete(obj)
        self.db.commit()

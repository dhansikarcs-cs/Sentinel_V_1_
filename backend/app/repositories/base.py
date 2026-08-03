from typing import Generic, TypeVar, Type, Optional, Any
from sqlalchemy.orm import Session
from app.core.database import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    def __init__(self, model: Type[ModelType], db: Session):
        self.model = model
        self.db = db

    def get(self, id: Any) -> Optional[ModelType]:
        return self.db.query(self.model).filter(self.model.id == id).first()

    def get_all(self) -> list[ModelType]:
        return self.db.query(self.model).all()

    def add(self, instance: ModelType) -> ModelType:
        self.db.add(instance)
        self.db.commit()
        self.db.refresh(instance)
        return instance

    def update(self, instance: ModelType, **kwargs) -> ModelType:
        for key, value in kwargs.items():
            if hasattr(instance, key):
                setattr(instance, key, value)
        self.db.commit()
        self.db.refresh(instance)
        return instance

    def delete(self, instance: ModelType) -> None:
        self.db.delete(instance)
        self.db.commit()

    def filter_by(self, **kwargs) -> list[ModelType]:
        return self.db.query(self.model).filter_by(**kwargs).all()

    def count(self, **kwargs) -> int:
        q = self.db.query(self.model)
        if kwargs:
            q = q.filter_by(**kwargs)
        return q.count()

from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.schemas.product import ProductCategory
from app.models.mixins import TimeStampMixin


class Product(Base, TimeStampMixin):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str]
    description: Mapped[str]
    category: Mapped[ProductCategory] = mapped_column(default=ProductCategory.BOOKS)
    price: Mapped[float]

    def __repr__(self) -> str:
        return f"Product(id={self.id}, name='{self.name}', category='{self.category}', price={self.price})"

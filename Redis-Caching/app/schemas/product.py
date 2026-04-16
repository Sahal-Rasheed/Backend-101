from enum import StrEnum

from pydantic import BaseModel, Field, StrictStr


class ProductCategory(StrEnum):
    ELECTRONICS = "electronics"
    BOOKS = "books"
    CLOTHING = "clothing"
    HOME = "home"
    TOYS = "toys"


class ProductBase(BaseModel):
    name: StrictStr = Field(..., min_length=1, max_length=100)
    description: StrictStr = Field(..., min_length=1, max_length=200)
    price: float = Field(..., gt=0, description="Price must be greater than zero")
    category: ProductCategory


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: StrictStr | None = Field(None, min_length=1, max_length=100)
    description: StrictStr | None = Field(None, min_length=1, max_length=200)
    price: float | None = Field(
        None, gt=0, description="Price must be greater than zero"
    )
    category: ProductCategory | None = None


class ProductResponse(ProductBase):
    id: int

    class Config:
        from_attributes = True

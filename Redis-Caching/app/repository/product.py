from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func

from app.models.product import Product
from app.schemas.product import ProductCreate, ProductUpdate


class ProductRepository:
    def __init__(self):
        self.model = Product

    async def create_product(
        self, db: AsyncSession, product_create: ProductCreate
    ) -> Product:
        product = self.model(**product_create.model_dump())
        db.add(product)
        await db.commit()
        await db.refresh(product)
        return product

    async def get_product(self, db: AsyncSession, product_id: int) -> Product | None:
        result = await db.execute(select(self.model).where(self.model.id == product_id))
        return result.scalar_one_or_none()

    async def get_all_products(
        self, db: AsyncSession, limit: int = 100, offset: int = 0
    ) -> list[Product]:

        query = select(self.model).offset(offset).limit(limit).order_by(self.model.id)
        result = await db.execute(query)
        return list(result.scalars().all())

    async def update_product(
        self, db: AsyncSession, product_id: int, product_update: ProductUpdate
    ) -> Product | None:

        update_data = (
            product_update.model_dump(exclude_unset=True)
            if isinstance(product_update, ProductUpdate)
            else product_update
        )

        result = await db.execute(
            update(self.model)
            .where(self.model.id == product_id)
            .values(**update_data)
            .returning(self.model)
        )

        await db.commit()
        return result.scalar_one_or_none()

    async def delete_product(self, db: AsyncSession, product_id: int) -> bool:
        result = await db.execute(delete(self.model).where(self.model.id == product_id))
        await db.commit()
        return result.rowcount > 0

    async def product_count(self, db: AsyncSession) -> int:
        query = select(func.count()).select_from(self.model)
        result = await db.execute(query)
        return result.scalar_one()

    async def exists(self, db: AsyncSession, id: int) -> bool:
        query = select(select(self.model.id).where(self.model.id == id).exists())
        result = await db.execute(query)
        return result.scalar()


product_repository = ProductRepository()

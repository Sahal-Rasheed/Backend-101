import asyncio

from fastapi import APIRouter, Query, status
from fastapi.exceptions import HTTPException

from app.utils.redis import cache
from app.db.session import AsyncSessionDep
from app.repository.product import product_repository
from app.schemas.product import ProductCreate, ProductUpdate, ProductResponse

router = APIRouter(prefix="/products", tags=["products"])


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=ProductResponse)
async def create_product(
    db: AsyncSessionDep, product_create: ProductCreate
) -> ProductResponse:
    product = await product_repository.create_product(db, product_create)
    await cache.set(
        f"product:{product.id}", ProductResponse.model_validate(product).model_dump()
    )
    await cache.delete_pattern("products:limit=*")
    return product


@router.get("/", status_code=status.HTTP_200_OK, response_model=list[ProductResponse])
async def list_products(
    db: AsyncSessionDep,
    limit: int = Query(5, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> list[ProductResponse]:
    # hit
    cached_products = await cache.get(f"products:limit={limit}:offset={offset}")
    if cached_products:
        print(f"Cache hit for products: limit={limit}, offset={offset}")
        return cached_products

    # miss
    print(f"Cache miss for products: limit={limit}, offset={offset}")
    products = await product_repository.get_all_products(db, limit, offset)
    products_payload = [
        ProductResponse.model_validate(product).model_dump() for product in products
    ]
    await cache.set(
        f"products:limit={limit}:offset={offset}",
        products_payload,
    )
    return products


@router.get(
    "/{product_id}", status_code=status.HTTP_200_OK, response_model=ProductResponse
)
async def get_product(db: AsyncSessionDep, product_id: int) -> ProductResponse:
    # hit
    cached_product = await cache.get(f"product:{product_id}")
    if cached_product:
        print(f"Cache hit for product_id={product_id}")
        return cached_product

    # miss
    print(f"Cache miss for product_id={product_id}")

    # acquire lock to prevent cache stampede
    # on a cache miss, multiple requests for the same product_id can hit the database simultaneously, causing high load.
    # by acquiring a lock, we ensure that only one request fetches the data from the database and populates the cache, while others wait and retry after a short delay.
    lock_key = f"lock:product:{product_id}"
    lock_acquired = await cache.acquire_lock(lock_key, timeout=10)
    if lock_acquired:
        product = await product_repository.get_product(db, product_id)
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
            )
        await cache.set(
            f"product:{product.id}",
            ProductResponse.model_validate(product).model_dump(),
        )
        return product
    else:
        # wait before retrying,
        # giving the lock holder time to fetch data and populate cache
        await asyncio.sleep(0.5)
        cached_product = await cache.get(f"product:{product_id}")
        if cached_product:
            print(f"Cache hit after waiting for product_id={product_id}")
            return cached_product
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Please retry after a moment",
            )


@router.put(
    "/{product_id}", status_code=status.HTTP_200_OK, response_model=ProductResponse
)
async def update_product(
    db: AsyncSessionDep, product_id: int, product_update: ProductUpdate
) -> ProductResponse:
    product = await product_repository.update_product(db, product_id, product_update)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
        )

    await cache.set(
        f"product:{product.id}",
        ProductResponse.model_validate(product).model_dump(),
    )
    await cache.delete_pattern("products:limit=*")
    return product


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(db: AsyncSessionDep, product_id: int) -> None:
    success = await product_repository.delete_product(db, product_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
        )
    await cache.delete(f"product:{product_id}")
    await cache.delete_pattern("products:limit=*")

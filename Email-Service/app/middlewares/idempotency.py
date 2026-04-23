from typing import Annotated

from fastapi.exceptions import HTTPException
from fastapi import Depends, Request, status

from app.utils.redis import redis_service


def idempotency_dependency_middleware(request: Request):
    """
    Middleware dependency to enforce idempotency based on request-id header, on Email-Service endpoint.
    Idempotency key is valid for 24 hours and ensures that multiple requests with the same key will only be processed once.
    """
    idempotency_key = request.headers.get("x-request-id", None)
    if not idempotency_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing idempotency key header",
        )

    key = f"idempotency:{idempotency_key}"
    existing_response = redis_service.get(key)
    print(
        f"Existing idempotency response for key {idempotency_key}: {existing_response}, type: {type(existing_response)}"
    )
    if existing_response and existing_response["status"] == "processing":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Duplicate request, this request is already being processed",
        )

    if existing_response and existing_response["status"] == "completed":
        del existing_response["status"]
        raise HTTPException(
            status_code=status.HTTP_200_OK,
            detail="Duplicate request, returning previous response",
        )

    locked = redis_service.acquire_lock(key, {"status": "processing"})
    if not locked:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Duplicate request, this request is already being processed",
        )


IdempotencyDep = Annotated[None, Depends(idempotency_dependency_middleware)]

# Redis Caching API

A FastAPI project demonstrating practical Redis caching patterns for CRUD APIs. This project focuses on a simple product catalog with cache-aside pattern, for both detail and list endpoints, along with cache invalidation strategies and basic anti-stampede locking.

## Tech Stack

- Python 3.12+
- FastAPI
- SQLAlchemy 2.0 (async)
- SQLite (`aiosqlite`)
- Redis (`redis-py` async client + `hiredis`)
- ORJSON for fast serialization

## Features

- Async REST API for products
- Read-through caching for detail and list endpoints
- Cache invalidation after create/update/delete
- Pattern-based invalidation for paginated list cache keys
- Basic distributed lock with Redis `SET NX EX` to mitigate cache stampede

## Quick Setup

Create a `.env` file in this folder:

```env
REDIS_URL=redis://localhost:6379/0
SQLITE_DATABASE_URL=sqlite+aiosqlite:///./database.db
```

Start Redis and Redis Commander:

```bash
docker compose up -d
```

Services:

- Redis: `localhost:6379`
- Redis Commander UI: `http://localhost:8081`

Run the Backend:

```bash
# From this directory, run:
uv venv
source venv/bin/activate
uv sync
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- Swagger UI: `http://127.0.0.1:8000/api/v1/docs`
- OpenAPI JSON: `http://127.0.0.1:8000/api/v1/openapi.json`

## API Endpoints

Base prefix: `/api/v1/products`

- `POST /` create product
- `GET /` list products (supports `limit`, `offset`)
- `GET /{product_id}` get single product
- `PUT /{product_id}` update product
- `DELETE /{product_id}` delete product

## Caching Behavior

### Product Detail (`GET /{product_id}`)

1. Try Redis key: `product:{id}`.
2. On hit, return cached JSON.
3. On miss, try acquiring lock: `lock:product:{id}`.
4. Lock holder reads DB and stores cache.
5. Non-lock holders wait briefly and retry cache.

### Product List (`GET /`)

1. Try Redis key: `products:limit={limit}:offset={offset}`.
2. On miss, query DB and cache serialized list.

### Invalidation

- On create/update/delete:
  - Update product detail key with new data if applicable.
  - Delete matching list keys with pattern: `products:limit=*`

This keeps list caches fresh after writes.

## Quick Test with cURL

Create:

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/products/" \
	-H "Content-Type: application/json" \
	-d '{
		"name": "Notebook",
		"description": "A5 ruled notebook",
		"price": 4.5,
		"category": "books"
	}'
```

List:

```bash
curl "http://127.0.0.1:8000/api/v1/products/?limit=5&offset=0"
```

Detail:

```bash
curl "http://127.0.0.1:8000/api/v1/products/1"
```

Update:

```bash
curl -X PUT "http://127.0.0.1:8000/api/v1/products/1" \
	-H "Content-Type: application/json" \
	-d '{"price": 5.25}'
```

Delete:

```bash
curl -X DELETE "http://127.0.0.1:8000/api/v1/products/1"
```

## Learning Goals

This project is useful for learning:

- how to integrate Redis caching in a FastAPI application
- cache key design for list/detail endpoints
- invalidation strategy trade-offs
- basic anti-stampede locking in Redis

---

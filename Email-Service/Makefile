.PHONY: help build run stop restart logs app-logs celery-logs shell status

service ?= app # Default service

help:
	@echo "Usage: make <target>"
	@echo "Targets:"
	@echo "  build     - Build the Docker images"
	@echo "  run       - Start the Docker containers"
	@echo "  stop      - Stop the Docker containers"
	@echo "  restart   - Restart the Docker containers"
	@echo "  logs      - View the logs of the specified service"
	@echo "  app-logs  - View the logs of the app service"
	@echo "  celery-logs - View the logs of the Celery services"
	@echo "  shell     - Open a shell in the specified service"
	@echo "  status    - Show the status of the Docker containers"

build:
	docker compose build --no-cache

run:
	docker compose up -d

stop:
	docker compose down

restart:
	docker compose restart

logs:
	docker compose logs -f $(service)

app-logs:
	docker compose logs -f app

celery-logs:
	docker compose logs -f celery-worker-default celery-worker-high celery-worker-low

shell:
	docker compose exec $(service) bash

status:
	docker compose ps

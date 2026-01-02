.PHONY: help install dev-install migrate create-migration test lint format run docker-up docker-down clean

help:
	@echo "Available commands:"
	@echo "  install          Install production dependencies"
	@echo "  dev-install      Install all dependencies including dev"
	@echo "  migrate          Run database migrations"
	@echo "  create-migration Create a new migration"
	@echo "  test             Run tests"
	@echo "  lint             Run linters"
	@echo "  format           Format code"
	@echo "  run              Run the application locally"
	@echo "  docker-up        Start Docker Compose services"
	@echo "  docker-down      Stop Docker Compose services"
	@echo "  clean            Clean up generated files"

install:
	poetry install --no-dev

dev-install:
	poetry install

migrate:
	poetry run alembic upgrade head

create-migration:
	@read -p "Enter migration message: " msg; \
	poetry run alembic revision --autogenerate -m "$$msg"

test:
	poetry run pytest

lint:
	poetry run ruff check .
	poetry run mypy app

format:
	poetry run black app tests
	poetry run ruff check --fix .

run:
	poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	find . -type f -name ".coverage" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name "*.egg" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type d -name "htmlcov" -exec rm -rf {} +

# Terraform commands
tf-init:
	cd infrastructure/terraform && terraform init

tf-plan:
	cd infrastructure/terraform && terraform plan

tf-apply:
	cd infrastructure/terraform && terraform apply

tf-destroy:
	cd infrastructure/terraform && terraform destroy

# K8s commands
k8s-apply:
	kubectl apply -f infrastructure/k8s/

k8s-delete:
	kubectl delete -f infrastructure/k8s/
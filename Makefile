.PHONY: help db setup migrate seed run-sync run-async bench bench-sync bench-mock health clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

db: ## Start PostgreSQL
	docker compose up -d db
	@echo "Waiting for PostgreSQL..."
	@sleep 3

setup: db ## Full setup: DB + migrate + seed
	uv sync
	uv run python manage.py migrate
	uv run python manage.py seed_data --products 10000
	@echo "✅ Ready! Run 'make run-async' to start."

migrate: ## Run migrations
	uv run python manage.py migrate

seed: ## Seed 10K products
	uv run python manage.py seed_data --products 10000

run-async: ## Run with uvicorn (ASGI — async support) on :8000
	BENCHMARK_IO_MODE=mock uv run uvicorn DjangoAsyncProject.asgi:application --reload --host 0.0.0.0 --port 8000

run-sync: ## Run with gunicorn (WSGI — sync only) on :8001
	BENCHMARK_IO_MODE=mock uv run gunicorn DjangoAsyncProject.wsgi:application --bind 0.0.0.0:8001 --workers 4

bench: ## Run k6 benchmark against ASGI server (:8000)
	k6 run --out json=k6/results.json k6/benchmark.js

bench-sync: ## Run k6 benchmark against WSGI server (:8001)
	k6 run --out json=k6/results-sync.json -e BASE_URL=http://localhost:8001 k6/benchmark.js

bench-mock: ## Run k6 with mock mode (offline, deterministic)
	BENCHMARK_IO_MODE=mock k6 run --out json=k6/results-mock.json k6/benchmark.js

health: ## Check health endpoint
	@curl -s http://localhost:8000/api/v1/health/ | python3 -m json.tool

clean: ## Reset DB and benchmark results
	docker compose down -v
	rm -f k6/results*.json
	@echo "🗑️ Database and results removed."

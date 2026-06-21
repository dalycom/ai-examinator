.PHONY: up down logs migrate seed test lint typecheck backend-test frontend-test ci

up:
	docker compose up --build

down:
	docker compose down

logs:
	docker compose logs -f

migrate:
	docker compose exec backend alembic upgrade head

seed:
	docker compose exec backend python -m app.scripts.seed_synthetic

backend-test:
	cd backend && pytest -q

backend-lint:
	cd backend && ruff check . && ruff format --check .

backend-typecheck:
	cd backend && mypy app

frontend-test:
	cd frontend && npm run test --if-present

frontend-lint:
	cd frontend && npm run lint

frontend-typecheck:
	cd frontend && npm run typecheck

ci: backend-lint backend-typecheck backend-test frontend-lint frontend-typecheck

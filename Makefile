.PHONY: install-api install-web install test run-api run-web docker-up eval

install-api:
	cd apps/api && pip install -e ".[dev]"

install-web:
	cd apps/web && npm install

install: install-api install-web

test:
	cd apps/api && pytest tests/ -v

run-api:
	cd apps/api && uvicorn accountflow.main:app --reload --port 8000

run-web:
	cd apps/web && npm run dev

docker-up:
	docker compose up --build

eval:
	python eval/run_eval.py

.PHONY: serve test test-unit test-integration install

serve:
	.venv/bin/uvicorn concierge.server:app --reload --port 8000

test:
	.venv/bin/pytest tests/

test-unit:
	.venv/bin/pytest tests/unit/ --no-cov -q

test-integration:
	.venv/bin/pytest tests/integration/ --no-cov -q

install:
	python3 -m venv .venv
	.venv/bin/pip install -e ".[dev]"
	cp -n .env.example .env || true

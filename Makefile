.PHONY: docs test dev
package_name = pricepoint

docs:
	( \
		source .venv/bin/activate && \
		cd docs && \
		$(MAKE) html && \
		open _build/html/index.html \
	)

clean:
	( \
		source .venv/bin/activate && \
		cd docs && \
		$(MAKE) clean \
	)

format:
	uv run ruff format
	uv run ruff check --fix

lint:
	uv run ruff format --check
	uv run ruff check
	uv run mypy $(package_name)

test:
	uv run pytest

coverage:
	uv run coverage run -m pytest
	uv run coverage html --omit="tests/*"
	open htmlcov/index.html

dev:
	$(MAKE) format
	$(MAKE) lint
	$(MAKE) test
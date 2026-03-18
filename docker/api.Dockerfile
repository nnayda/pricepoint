FROM python:3.12-slim

WORKDIR /app

# Install uv
RUN pip install --no-cache-dir uv

# Install dependencies first (cached unless pyproject.toml/uv.lock change)
COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen --no-dev

# Copy source code and config (changes here won't invalidate dependency cache)
COPY src/ src/
COPY alembic.ini ./
COPY docs/FEATURE_CATALOG.md docs/FEATURE_CATALOG.md

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "pricepoint.api.main:app", "--host", "0.0.0.0", "--port", "8000"]

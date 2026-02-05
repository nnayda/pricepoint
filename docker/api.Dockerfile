FROM python:3.12-slim

WORKDIR /app

# Install uv
RUN pip install --no-cache-dir uv

# Copy project files
COPY pyproject.toml uv.lock* ./
COPY src/ src/
COPY alembic.ini ./

# Install dependencies
RUN uv sync --frozen --no-dev

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "pricepoint.api.main:app", "--host", "0.0.0.0", "--port", "8000"]

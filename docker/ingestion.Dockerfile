# --- STAGE 1: The Builder (Install heavy dependencies) ---
FROM python:3.11-slim as builder

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc libgdal-dev g++ && \
    rm -rf /var/lib/apt/lists/*

# Install heavy GIS and DB libraries (This layer is cached!)
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# --- STAGE 2: The Final Image (Lean and Fast) ---
FROM python:3.11-slim

WORKDIR /app

# Copy the pre-installed libraries from the builder stage
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Copy your source code (This is the only part that changes frequently)
COPY src/ /app/src/

# Ensure Python doesn't buffer logs so they show up instantly in Airflow
ENV PYTHONUNBUFFERED=1

# The image is now ready to run any script in your /src folder
# Default command is just a placeholder
CMD ["python", "--version"]
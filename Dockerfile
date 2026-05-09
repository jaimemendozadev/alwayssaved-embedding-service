# Use a lightweight official Python image
FROM python:3.11-slim

# Environment settings
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

# Copy dependency files first (layer caching)
COPY pyproject.toml uv.lock ./

# Install dependencies (no project, just deps)
RUN uv sync --frozen --no-install-project --no-dev

# Copy the rest of your application code
COPY . .

# Install the project itself
RUN uv sync --frozen --no-dev

# Set default command
CMD ["uv", "run", "service.py"]

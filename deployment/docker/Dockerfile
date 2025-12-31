# Multi-stage Dockerfile for Smart Logistics Supply Chain ML
# Stage 1: Base image with Poetry and system dependencies
# Stage 2: Development image with all dependencies

# ============================================
# Stage 1: Base Image
# ============================================
FROM python:3.12-slim AS base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    POETRY_VERSION=1.7.1 \
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Set shell with pipefail for proper error handling in pipes
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 - \
    && ln -s /opt/poetry/bin/poetry /usr/local/bin/poetry

# Copy only dependency files first (for better cache utilization)
COPY pyproject.toml poetry.lock* ./

# ============================================
# Stage 2: Development Image
# ============================================
FROM base AS dev

# Install all dependencies (including dev dependencies)
RUN poetry install --no-root --with dev

# Copy the entire project
COPY . .

# Install the project itself
RUN poetry install --only-root

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash appuser \
    && chown -R appuser:appuser /app
USER appuser

# Expose ports for MLflow UI and potential API
EXPOSE 5000 8080

# Default command for development
CMD ["python", "-c", "print('Smart Logistics ML - Development Container Ready')"]

# ============================================
# Stage 3: Production Image (slim)
# ============================================
FROM base AS production

# Install only production dependencies
RUN poetry install --no-root --without dev

# Copy the entire project
COPY . .

# Install the project itself
RUN poetry install --only-root

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash appuser \
    && chown -R appuser:appuser /app
USER appuser

# Expose ports
EXPOSE 8080

# Default command for production
CMD ["python", "-m", "src"]

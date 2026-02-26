FROM python:3.13-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /app

# Install Python dependencies — cached independently of application code
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Copy application source
COPY src/ ./src/
COPY chat_app.py main.py chainlit.toml ./
COPY public/ ./public/

# Make the venv's binaries (chainlit, python, etc.) available directly
ENV PATH="/app/.venv/bin:$PATH"

# data/ and openspec/ are expected to be mounted at runtime

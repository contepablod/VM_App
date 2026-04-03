FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1

# Copy dependency metadata first for better caching.
COPY pyproject.toml uv.lock ./

# Install dependencies into the project virtual environment.
RUN uv sync --frozen --no-dev --no-install-project

# Copy the rest of the app.
COPY . .

EXPOSE 5000

# Run through uv-managed environment.
CMD ["uv", "run", "app.py"]

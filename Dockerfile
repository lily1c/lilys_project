FROM python:3.11-slim

WORKDIR /app

# Install uv for fast dependency management
RUN pip install uv

# Copy dependencies first for caching
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen

# Copy the rest of the application
COPY . .

# Expose the port Flask usually runs on
EXPOSE 8000

# Use gunicorn for production-grade serving
CMD ["/app/.venv/bin/gunicorn", "--bind", "0.0.0.0:8000", "run:app", "--workers", "4", "--threads", "2"]

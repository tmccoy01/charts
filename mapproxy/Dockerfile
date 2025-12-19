FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libproj-dev \
    libgeos-dev \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Set up working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies using uv
RUN uv sync --frozen --no-install-project

# Copy mapproxy config
COPY mapproxy/ /app/mapproxy/

# Create cache directory
RUN mkdir -p /cache && chmod 777 /cache
VOLUME /cache

# Set environment variables
ENV PYTHONPATH=/app
ENV PATH="/app/.venv/bin:$PATH"

# Expose port
EXPOSE 8080

# Command to run MapProxy
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8080", "--chdir", "/app/mapproxy/chart", "wsgi:application"]

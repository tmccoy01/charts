FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libproj-dev \
    libgeos-dev \
    gdal-bin \
    libgdal-dev \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Set up build directory
WORKDIR /app
COPY pyproject.toml uv.lock ./

# Install Perl dependencies (fix MapProxy issues)
COPY cpanfile /home/mapserv/
RUN cpanm --installdeps /home/mapserv/ || true

# Install dependencies using uv
ENV GDAL_CONFIG=/usr/bin/gdal-config
RUN uv sync --frozen --no-install-project

# Copy mapproxy config
COPY mapproxy/ /app/config/

# Copy downloader into image (for updater job)
COPY download_charts.py /app/download_charts.py

# Create cache directory
RUN mkdir -p /cache && chmod 777 /cache
VOLUME /cache

# Set environment variables
ENV PYTHONPATH=/app
ENV PATH="/app/.venv/bin:$PATH"

# Expose port
EXPOSE 8080

# Command to run MapProxy
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8080", "--chdir", "/app/config/chart", "wsgi:application"]

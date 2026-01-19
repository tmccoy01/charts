# Summary of Work: Charts Server Modernization

This document outlines the changes made to modernize the `charts` project, transitioning it to a containerized architecture managed by `uv` and Docker.

## Core Changes

### 1. Dependency Management (`uv`)
-   **File**: `pyproject.toml`
-   **Description**: Initialized a standard Python project configuration.
-   **Action**: Replaced manual environment setup with `uv` for reproducible dependency installation. Dependencies like `mapproxy`, `gunicorn`, and `pyproj` are now explicitly defined.

### 2. Containerization (Docker)
-   **File**: `docker-compose.yml`
    -   Orchestrates two services: `mapproxy` (frontend) and `mapserver` (backend).
    -   Handles networking between containers and volume mapping for data persistence.
-   **File**: `mapproxy/Dockerfile`
    -   Builds a lightweight Python 3.12 image.
    -   Installs `uv` and synchronizes dependencies.
    -   Runs MapProxy via `gunicorn`.
-   **File**: `mapserv/Dockerfile`
    -   Builds a Debian-based image with MapServer, Apache/CGI, and necessary Perl/GDAL libraries.
    -   Replicates the legacy environment structure (`/root/bin`, `/root/perl`) to maintain compatibility with existing scripts.

### 3. Configuration Updates
-   **File**: `mapproxy/chart/mapproxy.yaml`
    -   **Networking**: Updated upstream source URLs from `http://mapserv.example.com` to `http://mapserver` (the Docker Compose service name).
    -   **Caching**: changed cache directory to `/cache/chart` to map to a Docker volume, ensuring performance and persistence.

### 4. Documentation
-   **File**: `README_DOCKER.md`
    -   New comprehensive guide for building, running, and populating the Dockerized server.
-   **File**: `PROXMOX_EXPOSURE.md`
    -   Strategy guide for exposing the internal server to outside networks using Proxmox (Reverse Proxy vs. VPN).

## Architecture Overview

**Before**:
-   Manual install of Apache, MapServer, and Python envs.
-   Hardcoded system paths.
-   Complex host dependency management.

**Now**:
-   **MapProxy Container** (Port 8080): Serves the frontend, caches tiles, and handles KML generation.
-   **MapServer Container** (Port 80, internal): Generates raw map images from source data.
-   **Docker Compose**: Bridges the two containers on a private network.
-   **Data Volumes**: Charts and cache are stored on the host and mounted into containers, preserving data across restarts.

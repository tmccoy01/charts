#!/bin/bash
set -e

# ==============================================================================
# Charts Server Setup Script
# ==============================================================================
# 1. uv installation and setup
# 2. Docker container creation
# 3. Directory structure initialization (respecting existing data)
# 4. Mapfile generation
# ==============================================================================

echo ">>> Starting Charts Server Setup..."

# ------------------------------------------------------------------------------
# 1. uv Setup
# ------------------------------------------------------------------------------
echo ">>> Checking for uv..."
if ! command -v uv &> /dev/null; then
    echo "    uv not found. Installing..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    source $HOME/.cargo/env 2>/dev/null || export PATH="$HOME/.cargo/bin:$PATH"
else
    echo "    uv is already installed."
fi

echo ">>> Syncing Python dependencies..."
uv sync --no-install-project

# ------------------------------------------------------------------------------
# 2. Directory Structure Check
# ------------------------------------------------------------------------------
echo ">>> Checking directory structure..."
# Ensure transient directories exist (work/index might not be in git)
mkdir -p mapserv/charts/{work,index}

# Verify critical directories exist
if [ ! -d "mapserv/charts/bref" ]; then
    echo "WARNING: mapserv/charts/bref not found. Please ensure data is present."
fi

# ------------------------------------------------------------------------------
# 3. Docker Setup
# ------------------------------------------------------------------------------
echo ">>> Building Docker containers..."
docker-compose build

echo ">>> Starting Services..."
docker-compose up -d

echo ">>> Docker containers are running!"

# ------------------------------------------------------------------------------
# 4. Mapfile Generation
# ------------------------------------------------------------------------------
echo ">>> Checking for charts to index..."

# Run makemap3.pl inside the container
# This script automatically finds chart directories like 'sec/20231005/',
# selects the newest date for each chart, and generates the mapfiles.
echo ">>> Running map generation script (makemap3.pl)..."
docker-compose exec mapserver /home/mapserv/bin/makemap3.pl

echo ""
echo "=============================================================================="
echo "Setup Complete!"
echo ""
echo "- If you have existing charts in 'mapserv/charts/<type>/<date>/', they should now be indexed."
echo "- MapProxy is available at: http://localhost:8080/demo/"
echo "- Google Earth KML: http://localhost:8080/kml/sec/0/0/0.kml"
echo ""
echo "To add new charts:"
echo "1. Download the FAA zip files."
echo "2. Create a folder: mapserv/charts/<type>/YYYYMMDD/"
echo "3. Extract TIF files into that folder."
echo "4. Run: docker-compose exec mapserver /home/mapserv/bin/makemap3.pl"
echo "=============================================================================="

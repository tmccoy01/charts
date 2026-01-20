#!/usr/bin/env python3
"""
Main orchestrator for FAA chart processing pipeline.
Coordinates downloading, processing, and service updates.
"""

import os
import sys
import subprocess
import time
import logging
from pathlib import Path
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_command(cmd, description="", check=True):
    """Run command with error handling."""
    logger.info(f"Running: {description}")
    logger.debug(f"Command: {cmd}")

    try:
        result = subprocess.run(
            cmd, shell=True, check=check,
            capture_output=True, text=True
        )
        if result.stdout:
            logger.debug(f"Output: {result.stdout}")
        # Return success based on return code when check=False
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed: {e}")
        if e.stderr:
            logger.error(f"Error output: {e.stderr}")
        return False


def download_charts():
    """Download latest charts."""
    logger.info("Starting chart download...")
    return run_command(
        "uv run python3 /home/mapserv/download_charts.py",
        "Download FAA charts"
    )


def process_charts():
    """Process downloaded charts."""
    logger.info("Starting chart processing...")
    return run_command(
        "cd /home/mapserv && perl bin/makemap3.pl",
        "Process charts with makemap3.pl"
    )


def update_tile_indexes():
    """Update tile indexes for performance."""
    logger.info("Updating tile indexes...")
    base_dir = Path("/home/mapserv/charts")
    index_dir = base_dir / "index"
    index_dir.mkdir(exist_ok=True)

    # Generate indexes for each chart type
    for chart_type in ['sec', 'tac', 'hel', 'enrl', 'enrh', 'enra']:
        chart_dir = base_dir / chart_type
        if chart_dir.exists():
            latest_date = max(
                [d.name for d in chart_dir.iterdir() if d.is_dir()], default=None)
            if latest_date:
                index_file = index_dir / f"{chart_type}_4326_index.shp"
                cmd = f"gdaltindex {index_file} {chart_dir}/{latest_date}/*_4326.tif"
                run_command(
                    cmd, f"Update {chart_type} tile index", check=False)


def reload_services():
    """Reload Apache to pick up new configurations."""
    logger.info("Reloading Apache...")
    return run_command("apachectl graceful", "Reload Apache")


def health_check():
    """Check if services are healthy."""
    logger.info("Performing health check...")

    # Check if MapServer is responding
    response = run_command(
        "curl -f http://localhost:80/mapserv?SERVICE=WMS&VERSION=1.1.1&REQUEST=GetCapabilities",
        "MapServer health check",
        check=False
    )

    if response:
        logger.info("✅ MapServer is healthy")
    else:
        logger.error("❌ MapServer is not responding")

    return response


def main():
    """Main orchestration workflow."""
    logger.info("Starting FAA chart orchestration...")

    start_time = time.time()

    # Step 1: Download charts
    if not download_charts():
        logger.error("Chart download failed, aborting")
        return 1

    # Step 2: Process charts
    if not process_charts():
        logger.error("Chart processing failed")
        return 1

    # Step 3: Update tile indexes
    update_tile_indexes()

    # Step 4: Reload services
    reload_services()

    # Step 5: Health check
    health_check()

    elapsed = time.time() - start_time
    logger.info(f"Orchestration completed in {elapsed:.2f} seconds")

    return 0


if __name__ == "__main__":
    sys.exit(main())

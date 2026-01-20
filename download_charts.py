#!/usr/bin/env python3
"""
FAA Chart Downloader

This script scrapes the FAA Digital Products pages for VFR and IFR charts,
identifies GeoTIFF zip files, and downloads them into a structured directory
layout suitable for the MapServer setup.

It uses only the Python standard library to ensure portability and ease of use.
"""

import os
import re
from typing import List, Optional, Tuple, Any
import zipfile
import urllib.request
import urllib.error
from html.parser import HTMLParser
from pathlib import Path
from datetime import datetime
import sys
import time
import subprocess

# Configuration
from dotenv import load_dotenv

# Load .env but do not override real environment by default.
# Docker/Compose sets container paths explicitly and we want those to win.
# On macOS it’s common to accidentally have a stale CHARTS_BASE_DIR in the shell;
# if it looks "unexpanded" (e.g. contains $(...)) or points at /home/mapserv,
# then override it from .env.
load_dotenv(interpolate=True)

existing_charts_dir = os.getenv("CHARTS_BASE_DIR")
if existing_charts_dir and (
    "$(" in existing_charts_dir
    or "${" in existing_charts_dir
    or (sys.platform == "darwin" and existing_charts_dir.startswith("/home/mapserv"))
):
    load_dotenv(override=True, interpolate=True)

BASE_DIR = Path(os.getenv("CHARTS_BASE_DIR", "mapserv/charts"))

# Limit chart types (default: sectional only)
# Examples:
# - CHART_TYPES=sec
# - CHART_TYPES=sec,tac
CHART_TYPES = [
    t.strip().lower() for t in os.getenv("CHART_TYPES", "sec").split(",") if t.strip()
]

# Cycle filtering:
# - Default is "latest" to avoid downloading multiple cycles.
# - Set CHART_CYCLE_POLICY=all to keep every cycle linked on FAA pages.
# - Set CHART_CYCLE=YYYYMMDD to force a specific cycle.
CHART_CYCLE_POLICY = os.getenv("CHART_CYCLE_POLICY", "latest").strip().lower()
CHART_CYCLE = os.getenv("CHART_CYCLE", "").strip()

# Disk savings: delete ZIPs after successful extraction.
DELETE_ZIPS = os.getenv("DELETE_ZIPS", "1") == "1"

VFR_URL = "https://www.faa.gov/air_traffic/flight_info/aeronav/digital_products/vfr/"
IFR_URL = "https://www.faa.gov/air_traffic/flight_info/aeronav/digital_products/ifr/"

# Subdirectories expected by makemap3.pl
# Mapping: FAA Category Name -> Local Directory
# Although not strictly used for logic below, this explains the directory codes.
CATEGORY_MAP = {
    "Sectional": "sec",
    "Terminal Area": "tac",
    "Helicopter": "hel",
    "Enroute Low": "enrl",
    "Enroute High": "enrh",
    "Enroute Area": "enra",
}

# Regex to identify chart types from URLs
# Updated to match typical filenames in links
# Tuple format: (Regex Pattern, Destination Directory Code)
TYPE_PATTERNS: List[Tuple[str, str]] = [
    (r"/sectional-files/", "sec"),
    (r"/terminal-files/", "tac"),
    (r"/helicopter-files/", "hel"),
    (r"/enr_l", "enrl"),
    (r"/enr_h", "enrh"),
    (r"/enr_a", "enra"),
    (r"/enr_akl", "enrl"),  # Alaska Low treated as Low
    (r"/enr_akh", "enrh"),  # Alaska High treated as High
]


def chart_type_from_url(url: str) -> str:
    """Return chart type code (sec/tac/hel/enrl/enrh/enra/misc) for a given URL."""
    for pattern, code in TYPE_PATTERNS:
        if re.search(pattern, url, re.IGNORECASE):
            return code
    return "misc"


def cycle_from_url(url: str) -> Optional[str]:
    """Extract YYYYMMDD cycle from URL path segment /MM-DD-YYYY/."""
    date_match = re.search(r"/(\d{2}-\d{2}-\d{4})/", url)
    if not date_match:
        return None
    try:
        dt = datetime.strptime(date_match.group(1), "%m-%d-%Y")
        return dt.strftime("%Y%m%d")
    except ValueError:
        return None


def filter_links(links: List[str]) -> Tuple[List[str], Optional[str]]:
    """Filter links by chart type and chart cycle policy.

    Returns (filtered_links, selected_cycle).
    """
    # First filter by chart types
    type_filtered = [u for u in links if chart_type_from_url(u) in CHART_TYPES]

    if not type_filtered:
        return ([], None)

    # Explicit cycle overrides everything
    if CHART_CYCLE:
        return (
            [u for u in type_filtered if cycle_from_url(u) == CHART_CYCLE],
            CHART_CYCLE,
        )

    if CHART_CYCLE_POLICY == "all":
        return (type_filtered, None)

    # Default: latest
    cycles = [c for c in (cycle_from_url(u) for u in type_filtered) if c]
    if not cycles:
        # If we can't detect cycles, fall back to no cycle filtering
        return (type_filtered, None)

    latest = max(cycles)
    return ([u for u in type_filtered if cycle_from_url(u) == latest], latest)


def get_url_content(url: str) -> Optional[str]:
    """
    Fetches the content of a URL using the standard urllib library.

    Args:
        url: The URL to fetch.

    Returns:
        The decoded string content of the page, or None if the request failed.
    """
    print(f"Reading {url}...")
    try:
        with urllib.request.urlopen(url) as response:
            return response.read().decode("utf-8")
    except urllib.error.URLError as e:
        print(f"Error fetching {url}: {e}")
        return None


class ZipLinkParser(HTMLParser):
    """
    Simple HTML Parser to extract .zip file links from <a> tags.
    Targeting links typically hosted on 'aeronav.faa.gov'.
    """

    def __init__(self) -> None:
        super().__init__()
        self.links: List[str] = []

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        """
        Overrides the standard handle_starttag to find 'a' tags with specific hrefs.
        """
        if tag == "a":
            href_val = dict(attrs).get("href")
            if href_val and href_val.endswith(".zip") and "aeronav.faa.gov" in href_val:
                self.links.append(href_val)


def print_progress(
    iteration: int,
    total: int,
    prefix: str = "",
    suffix: str = "",
    decimals: int = 1,
    length: int = 50,
    fill: str = "█",
    printEnd: str = "\r",
) -> None:
    """
    Call in a loop to create terminal progress bar.
    @params:
        iteration   - Required  : current iteration (Int)
        total       - Required  : total iterations (Int)
        prefix      - Optional  : prefix string (Str)
        suffix      - Optional  : suffix string (Str)
        decimals    - Optional  : positive number of decimals in percent complete (Int)
        length      - Optional  : character length of bar (Int)
        fill        - Optional  : bar fill character (Str)
        printEnd    - Optional  : end character (e.g. "\r", "\r\n") (Str)
    """
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filledLength = int(length * iteration // total)
    bar = fill * filledLength + "-" * (length - filledLength)
    sys.stdout.write(f"\r{prefix} |{bar}| {percent}% {suffix}")
    sys.stdout.flush()
    # Print New Line on Complete
    if iteration == total:
        print()


def ensure_aref_for_dir(target_dir: Path) -> None:
    """Create `.aref` files from FAA .htm metadata (bbox) if missing.

    The cropper scripts expect `<Chart Name>.aref` alongside each `.tif`.
    FAA does not ship `.aref`, but it does ship an `.htm` containing
    `dc.coverage.{x,y}.{min,max}` which we can use to build a rectangular ref.

    This yields a conservative crop polygon (bbox) that is good enough to
    enable cropping and bref generation.
    """

    def meta(name: str, text: str) -> Optional[str]:
        m = re.search(rf'name="{re.escape(name)}"[^>]*content="([^"]+)"', text)
        return m.group(1) if m else None

    for tif_path in target_dir.glob("*.tif"):
        aref_path = tif_path.with_suffix(".aref")
        if aref_path.exists():
            continue

        htm_path = tif_path.with_suffix(".htm")
        if not htm_path.exists():
            continue

        try:
            text = htm_path.read_text(encoding="utf-8", errors="ignore")
            x_min = meta("dc.coverage.x.min", text)
            x_max = meta("dc.coverage.x.max", text)
            y_min = meta("dc.coverage.y.min", text)
            y_max = meta("dc.coverage.y.max", text)
            if not (x_min and x_max and y_min and y_max):
                continue

            # Use geographic coords with linetype "g" (lon/lat).
            # Order points around rectangle.
            lines = [
                f"g {x_min} {y_min} g",
                f"g {x_min} {y_max} g",
                f"g {x_max} {y_max} g",
                f"g {x_max} {y_min} g",
            ]
            aref_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        except (IOError, OSError, ValueError) as e:
            # Best-effort; skip if file read/write fails or metadata is malformed.
            print(f"  Warning: Could not generate .aref for {tif_path.name}: {e}")
            continue


def download_file(url: str, quiet: bool = False) -> str:
    """
    Downloads a zip file from the given URL, determines its chart type and date,
    and extracts it into the appropriate directory.

    Args:
        url: The URL of the zip file to download.
        quiet: If True, suppress normal output (useful for progress bars).

    Returns:
        A status string indicating the result (e.g., "Downloaded", "Skipped", "Failed").
    """
    status = "Unknown"
    filename = url.split("/")[-1]

    chart_type = chart_type_from_url(url)

    # Optional filtering by chart type
    if CHART_TYPES and chart_type not in CHART_TYPES:
        return "Skipped (Filtered)"

    # Extract date from URL (typical format: .../11-27-2025/...)
    # This ensures we organize charts by their effective date cycle.
    date_match = re.search(r"/(\d{2}-\d{2}-\d{4})/", url)
    if not date_match:
        # Fallback: if date not found in URL, use current date.
        date_str = get_current_chart_cycle()
    else:
        d_str = date_match.group(1)
        # Convert MM-DD-YYYY to YYYYMMDD
        try:
            dt = datetime.strptime(d_str, "%m-%d-%Y")
            date_str = dt.strftime("%Y%m%d")
        except ValueError:
            date_str = get_current_chart_cycle()

    # Define target directory: mapserv/charts/<type>/<date>
    target_dir = BASE_DIR / chart_type / date_str
    target_dir.mkdir(parents=True, exist_ok=True)

    local_path = target_dir / filename

    # Check if file already exists to avoid re-downloading
    if local_path.exists():
        if not quiet:
            print(f"Skipping {filename} (already exists)")
        return "Skipped"

    if not quiet:
        print(f"Downloading {filename} to {chart_type}/{date_str}...")
    try:
        urllib.request.urlretrieve(url, local_path)
        if not quiet:
            print(f"  Unzipping...")
        try:
            with zipfile.ZipFile(local_path, "r") as zip_ref:
                zip_ref.extractall(target_dir)
            status = "Downloaded"
            ensure_aref_for_dir(target_dir)
            if DELETE_ZIPS and local_path.exists():
                local_path.unlink(missing_ok=True)
        except (zipfile.BadZipFile, NotImplementedError) as e:
            if not quiet:
                print(
                    f"\n  Warning: Python zipfile failed ({e}), trying system unzip..."
                )
            # Fallback to system unzip command
            try:
                subprocess.run(
                    ["unzip", "-o", "-q", str(local_path), "-d", str(target_dir)],
                    check=True,
                    capture_output=True,
                )
                status = "Downloaded (Fallback)"
                ensure_aref_for_dir(target_dir)
                if DELETE_ZIPS and local_path.exists():
                    local_path.unlink(missing_ok=True)
            except subprocess.CalledProcessError as se:
                print(f"\n  ERROR: System unzip also failed for {filename}")
                status = "Failed"
                # Cleanup bad zip
                if local_path.exists():
                    local_path.unlink()
    except Exception as e:
        print(f"\n  Failed: {filename} - {e}")
        status = "Failed"

    return status


def get_current_chart_cycle() -> str:
    """Get the current chart cycle date from FAA or use latest directory."""
    charts_base = Path(BASE_DIR)
    if not charts_base.exists():
        return datetime.now().strftime("%Y%m%d")

    # Find the latest date directory
    date_dirs = []
    for chart_type in ["sec", "tac", "hel", "enrl", "enrh", "enra"]:
        type_dir = charts_base / chart_type
        if type_dir.exists():
            date_dirs.extend([d.name for d in type_dir.iterdir() if d.is_dir()])
    if date_dirs:
        return max(date_dirs)
    return datetime.now().strftime("%Y%m%d")


def main() -> None:
    """
    Main execution function.
    Scrapes VFR and IFR pages and initiates downloads for all found charts.
    """
    print(">>> FAA Chart Downloader (Standard Lib)")

    # Get current chart cycle and display it
    current_cycle = get_current_chart_cycle()
    print(f">>> Current chart cycle: {current_cycle}")

    # Ensure base directory exists
    BASE_DIR.mkdir(parents=True, exist_ok=True)

    vfr_types = {"sec", "tac", "hel"}
    ifr_types = {"enrl", "enrh", "enra"}

    # 1. Scrape VFR Charts (only if any requested types are VFR)
    if any(t in vfr_types for t in CHART_TYPES):
        html_vfr = get_url_content(VFR_URL)
        if html_vfr:
            parser = ZipLinkParser()
            parser.feed(html_vfr)
            vfr_links = list(set(parser.links))
            filtered, selected_cycle = filter_links(vfr_links)
            print(
                f"Found {len(vfr_links)} VFR chart links ({len(filtered)} after filtering)."
            )
            if selected_cycle:
                print(f">>> Selected chart cycle (VFR): {selected_cycle}")

            print("Downloading VFR charts...")
            print_progress(
                0,
                len(filtered) or 1,
                prefix="VFR Progress:",
                suffix="Complete",
                length=40,
            )

            for i, link in enumerate(filtered):
                download_file(link, quiet=True)
                print_progress(
                    i + 1,
                    len(filtered) or 1,
                    prefix="VFR Progress:",
                    suffix="Complete",
                    length=40,
                )
    else:
        print(">>> Skipping VFR page scrape (no VFR chart types requested)")

    # 2. Scrape IFR Charts (only if any requested types are IFR)
    if any(t in ifr_types for t in CHART_TYPES):
        html_ifr = get_url_content(IFR_URL)
        if html_ifr:
            parser = ZipLinkParser()
            parser.feed(html_ifr)
            ifr_links = list(set(parser.links))
            filtered, selected_cycle = filter_links(ifr_links)
            print(
                f"Found {len(ifr_links)} IFR chart links ({len(filtered)} after filtering)."
            )
            if selected_cycle:
                print(f">>> Selected chart cycle (IFR): {selected_cycle}")

            print("Downloading IFR charts...")
            print_progress(
                0,
                len(filtered) or 1,
                prefix="IFR Progress:",
                suffix="Complete",
                length=40,
            )

            for i, link in enumerate(filtered):
                download_file(link, quiet=True)
                print_progress(
                    i + 1,
                    len(filtered) or 1,
                    prefix="IFR Progress:",
                    suffix="Complete",
                    length=40,
                )
    else:
        print(">>> Skipping IFR page scrape (no IFR chart types requested)")

    print("\n>>> Download complete.")


if __name__ == "__main__":
    main()

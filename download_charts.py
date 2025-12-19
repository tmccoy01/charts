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
BASE_DIR = Path("mapserv/charts")
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
    "Enroute Area": "enra"
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
    (r"/enr_akl", "enrl"), # Alaska Low treated as Low
    (r"/enr_akh", "enrh"), # Alaska High treated as High
]

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
            return response.read().decode('utf-8')
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
        if tag == 'a':
            href_val = dict(attrs).get('href')
            if href_val and href_val.endswith('.zip') and "aeronav.faa.gov" in href_val:
                self.links.append(href_val)

def print_progress(iteration: int, total: int, prefix: str = '', suffix: str = '', decimals: int = 1, length: int = 50, fill: str = '█', printEnd: str = "\r") -> None:
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
    bar = fill * filledLength + '-' * (length - filledLength)
    sys.stdout.write(f'\r{prefix} |{bar}| {percent}% {suffix}')
    sys.stdout.flush()
    # Print New Line on Complete
    if iteration == total:
        print()

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
    filename = url.split('/')[-1]
    
    # Identify type based on URL pattern
    chart_type = "misc"
    for pattern, code in TYPE_PATTERNS:
        if re.search(pattern, url, re.IGNORECASE):
            chart_type = code
            break
            
    # Extract date from URL (typical format: .../11-27-2025/...)
    # This ensures we organize charts by their effective date cycle.
    date_match = re.search(r'/(\d{2}-\d{2}-\d{4})/', url)
    if not date_match:
        # Fallback: if date not found in URL, use current date.
        date_str = datetime.now().strftime("%Y%m%d")
    else:
        d_str = date_match.group(1)
        # Convert MM-DD-YYYY to YYYYMMDD
        try:
            dt = datetime.strptime(d_str, "%m-%d-%Y")
            date_str = dt.strftime("%Y%m%d")
        except ValueError:
            date_str = datetime.now().strftime("%Y%m%d")

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
            with zipfile.ZipFile(local_path, 'r') as zip_ref:
                zip_ref.extractall(target_dir)
            status = "Downloaded"
        except (zipfile.BadZipFile, NotImplementedError) as e:
            if not quiet:
                print(f"\n  Warning: Python zipfile failed ({e}), trying system unzip...")
            # Fallback to system unzip command
            try:
                subprocess.run(
                    ["unzip", "-o", "-q", str(local_path), "-d", str(target_dir)], 
                    check=True, 
                    capture_output=True
                )
                status = "Downloaded (Fallback)"
            except subprocess.CalledProcessError as se:
                print(f"\n  ERROR: System unzip also failed for {filename}")
                status = "Failed"
                # Cleanup bad zip
                if local_path.exists():
                    os.remove(local_path)
    except Exception as e:
        print(f"\n  Failed: {filename} - {e}")
        status = "Failed"
    
    return status

def main() -> None:
    """
    Main execution function.
    Scrapes VFR and IFR pages and initiates downloads for all found charts.
    """
    print(">>> FAA Chart Downloader (Standard Lib)")
    
    # 1. Scrape VFR Charts
    html_vfr = get_url_content(VFR_URL)
    if html_vfr:
        parser = ZipLinkParser()
        parser.feed(html_vfr)
        vfr_links = list(set(parser.links))
        print(f"Found {len(vfr_links)} VFR chart links.")
        
        print("Downloading VFR charts...")
        # Initial call to print 0% progress
        print_progress(0, len(vfr_links), prefix='VFR Progress:', suffix='Complete', length=40)
        
        for i, link in enumerate(vfr_links): 
            download_file(link, quiet=True)
            print_progress(i + 1, len(vfr_links), prefix='VFR Progress:', suffix='Complete', length=40)

    # 2. Scrape IFR Charts
    html_ifr = get_url_content(IFR_URL)
    if html_ifr:
        parser = ZipLinkParser()
        parser.feed(html_ifr)
        ifr_links = list(set(parser.links))
        print(f"Found {len(ifr_links)} IFR chart links.")
        
        print("Downloading IFR charts...")
        # Initial call to print 0% progress
        print_progress(0, len(ifr_links), prefix='IFR Progress:', suffix='Complete', length=40)
        
        for i, link in enumerate(ifr_links):
            download_file(link, quiet=True)
            print_progress(i + 1, len(ifr_links), prefix='IFR Progress:', suffix='Complete', length=40)

    print("\n>>> Download complete.")

if __name__ == "__main__":
    main()

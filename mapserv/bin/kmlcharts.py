import simplekml
import re
import math
import os
from pathlib import Path


# Use environment variable or default to container path
BREF_DIR = Path(os.getenv("BREF_DIR", "/home/mapserv/charts/bref"))
BASE_PATH = BREF_DIR.glob("*SEC.bref")


def angle_to(point: int) -> float:
    return math.atan2(point[1], point[0])


def get_ref(chart_name: Path) -> list:
    """Get the boundary points of each chart sorted counterclockwise"""
    with chart_name.open() as ref:
        coords = ref.readlines()
    match = [re.findall(r'-?\d+\.\d*', line) for line in coords]
    match = [(float(point[0]), float(point[1])) for point in match]
    # return sorted(match, key=angle_to, reverse=True)
    return match


def plot_chart_boundary(chart_name: Path, kml: simplekml.Kml) -> None:
    """Plot the given charts points as a kml"""
    boundary_points = get_ref(chart_name)
    fol = kml.newfolder(name=chart_name)
    poly = fol.newpolygon(name=f"{chart_name.name.strip(".bref")}")
    poly.outerboundaryis = boundary_points
    poly.description = f"{chart_name}"
    return kml


def plot_all_charts():
    """Loop through each chart and plot the boundary"""
    kml = simplekml.Kml()
    for chart in BASE_PATH:
        kml = plot_chart_boundary(chart, kml)
    kml.save("Sectional Boundaries.kmz")


if __name__ == "__main__":
    plot_all_charts()

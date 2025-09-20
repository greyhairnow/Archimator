from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Tuple


def shoelace_area(points: List[Tuple[float, float]]) -> float:
    """Return the absolute area of a polygon using the shoelace formula."""
    if len(points) < 3:
        return 0.0
    area = 0.0
    n = len(points)
    for i in range(n):
        x1, y1 = points[i]
        x2, y2 = points[(i + 1) % n]
        area += x1 * y2 - x2 * y1
    return abs(area) / 2.0


def polygon_perimeter(points: List[Tuple[float, float]]) -> float:
    """Return the perimeter length of a polygon."""
    if len(points) < 2:
        return 0.0
    perim = 0.0
    n = len(points)
    for i in range(n):
        x1, y1 = points[i]
        x2, y2 = points[(i + 1) % n]
        perim += math.hypot(x2 - x1, y2 - y1)
    return perim


def point_in_polygon(pt: Tuple[float, float], polygon: List[Tuple[float, float]]) -> bool:
    """Ray casting algorithm to determine if a point lies within a polygon."""
    x, y = pt
    inside = False
    n = len(polygon)
    if n < 3:
        return False
    p1x, p1y = polygon[0]
    for i in range(n + 1):
        p2x, p2y = polygon[i % n]
        if min(p1y, p2y) < y <= max(p1y, p2y) and x <= max(p1x, p2x):
            if p1y != p2y:
                xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
            if p1x == p2x or x <= xinters:
                inside = not inside
        p1x, p1y = p2x, p2y
    return inside


@dataclass
class PolygonData:
    points: List[Tuple[float, float]] = field(default_factory=list)
    area_px: float = 0.0
    perimeter_px: float = 0.0
    metadata: dict = field(default_factory=dict)

    def compute_metrics(self) -> None:
        """Recompute area and perimeter in pixel units."""
        self.area_px = shoelace_area(self.points)
        self.perimeter_px = polygon_perimeter(self.points)



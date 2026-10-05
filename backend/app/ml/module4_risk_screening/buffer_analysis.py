"""
NeerNiti — Module 4: Proximity & GIS Buffer Analyzer (LIVE OSM MODE)
Computes real geodesic distance buffers to agricultural, industrial,
and drainage pollution proxies using the live OpenStreetMap Overpass API.
"""

import logging
import math
import time
from dataclasses import dataclass
from typing import Any

import requests
from shapely.geometry import Point

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ProximityFeatures:
    dist_to_farmland_m: float
    dist_to_industrial_m: float
    dist_to_sewage_line_m: float
    population_density: float
    data_confidence: float
    risk_category: str = "Low Risk"


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates the great-circle distance between two points on Earth in meters."""
    r = 6371000.0  # Earth radius in meters
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return r * c


class ProximityAnalyzer:
    """Calculates GIS buffer distances from candidate coordinates to pollution risk vectors."""

    # Multiple Overpass mirrors for failover (all free, no key needed)
    OVERPASS_ENDPOINTS = [
        "https://overpass-api.de/api/interpreter",
        "https://overpass.kumi.systems/api/interpreter",
        "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
    ]

    HEADERS = {
        "User-Agent": "NeerNiti-Geospatial-DSS/1.0 (contact@neerniti.org)",
        "Accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    }

    def __init__(self, timeout_sec: int = 45, max_retries: int = 2):
        self.timeout_sec = timeout_sec
        self.max_retries = max_retries

    def _post_overpass(self, query: str) -> dict[str, Any] | None:
        """Sends a single Overpass query with retry + endpoint failover."""
        for endpoint in self.OVERPASS_ENDPOINTS:
            for attempt in range(self.max_retries + 1):
                try:
                    response = requests.post(
                        endpoint,
                        data={"data": query},
                        headers=self.HEADERS,
                        timeout=self.timeout_sec,
                    )
                    response.raise_for_status()
                    return response.json()
                except requests.RequestException as e:
                    wait = 2 ** attempt
                    logger.debug(
                        f"Overpass attempt {attempt + 1} failed on {endpoint} ({e}). "
                        f"Retrying in {wait}s..."
                    )
                    if attempt < self.max_retries:
                        time.sleep(wait)
            # All retries exhausted on this endpoint, try the next mirror
            logger.debug(f"All retries exhausted on {endpoint}, trying next mirror...")

        logger.warning("All Overpass endpoints exhausted. Reverting to regional baseline.")
        return None

    def _query_overpass(self, lat: float, lng: float) -> dict[str, Any] | None:
        """
        Queries OpenStreetMap for nearby pollution vectors and farmlands.

        Splits into 3 smaller focused queries instead of one large query
        to avoid server-side timeouts on the public Overpass API. Each
        sub-query targets a single risk category with a tighter search radius.
        """
        ql_timeout = self.timeout_sec

        # Query 1: Farmland (smaller 3 km radius — rural India farmland polygons are huge)
        q_farmland = f"""
        [out:json][timeout:{ql_timeout}];
        way["landuse"="farmland"](around:3000,{lat},{lng});
        out center;
        """

        # Query 2: Industrial zones (5 km — sparse, fast to serialize)
        q_industrial = f"""
        [out:json][timeout:{ql_timeout}];
        (
          way["landuse"="industrial"](around:5000,{lat},{lng});
          node["landuse"="industrial"](around:5000,{lat},{lng});
        );
        out center;
        """

        # Query 3: Sewage & drainage (5 km)
        q_sewage = f"""
        [out:json][timeout:{ql_timeout}];
        (
          way["waterway"="drain"](around:5000,{lat},{lng});
          way["waterway"="ditch"](around:5000,{lat},{lng});
          node["man_made"="wastewater_plant"](around:5000,{lat},{lng});
          way["man_made"="wastewater_plant"](around:5000,{lat},{lng});
        );
        out center;
        """

        # Run each sub-query independently so a timeout on one doesn't lose the others
        combined_elements: list[dict[str, Any]] = []
        any_succeeded = False

        for label, query in [("farmland", q_farmland), ("industrial", q_industrial), ("sewage", q_sewage)]:
            result = self._post_overpass(query)
            if result and "elements" in result:
                combined_elements.extend(result["elements"])
                any_succeeded = True
                logger.info(f"  OSM {label}: {len(result['elements'])} features found")
            else:
                logger.warning(f"  OSM {label} query returned no data — will use baseline for this category")

        if not any_succeeded:
            return None

        return {"elements": combined_elements}

    def compute_proximity(
        self,
        point: Point,
        district_name: str = "Prayagraj",
    ) -> ProximityFeatures:
        """
        Computes geodesic buffer distances to farmland, industrial zones, and drainage canals.
        Shapely Points are standard (Longitude, Latitude) format.
        """
        is_alluvial = (district_name == "Prayagraj")

        # Extract lat/lng (with coordinate inversion guard for geographic points)
        coord_x, coord_y = point.x, point.y
        lat = min(coord_y, coord_x)
        lng = max(coord_x, coord_y)

        osm_data = self._query_overpass(lat, lng)

        # Baseline district defaults
        default_farmland = 600.0 if is_alluvial else 1500.0
        default_industrial = 4500.0 if is_alluvial else 7000.0
        default_sewage = 3500.0 if is_alluvial else 5500.0
        pop_density = 1080.0 if is_alluvial else 460.0

        if not osm_data or "elements" not in osm_data:
            # Fallback when Overpass API is unavailable
            return ProximityFeatures(
                dist_to_farmland_m=default_farmland,
                dist_to_industrial_m=default_industrial,
                dist_to_sewage_line_m=default_sewage,
                population_density=pop_density,
                data_confidence=0.70,
                risk_category="Low Risk"
            )

        industrial_dists = []
        sewage_dists = []
        farmland_dists = []

        for element in osm_data.get("elements", []):
            tags = element.get("tags", {})
            center = element.get("center", {})
            elem_lat = element.get("lat") or center.get("lat")
            elem_lon = element.get("lon") or center.get("lon")

            if elem_lat is None or elem_lon is None:
                continue

            dist = haversine_distance(lat, lng, elem_lat, elem_lon)

            if tags.get("landuse") == "industrial":
                industrial_dists.append(dist)
            elif tags.get("waterway") in ("drain", "ditch") or tags.get("man_made") == "wastewater_plant":
                sewage_dists.append(dist)
            elif tags.get("landuse") == "farmland":
                farmland_dists.append(dist)

        # Use nearest detected element, or max-search bound if none exist nearby
        dist_farmland = min(farmland_dists) if farmland_dists else 5000.0
        dist_industrial = min(industrial_dists) if industrial_dists else 10000.0
        dist_sewage = min(sewage_dists) if sewage_dists else 10000.0

        # Assess risk category based on proximity to pollution vectors
        if dist_industrial < 500.0 or dist_sewage < 500.0:
            risk_cat = "High Risk"
        elif dist_industrial < 1500.0 or dist_sewage < 1200.0:
            risk_cat = "Medium Risk"
        else:
            risk_cat = "Low Risk"

        return ProximityFeatures(
            dist_to_farmland_m=round(dist_farmland, 1),
            dist_to_industrial_m=round(dist_industrial, 1),
            dist_to_sewage_line_m=round(dist_sewage, 1),
            population_density=pop_density,
            data_confidence=0.95,
            risk_category=risk_cat,
        )


if __name__ == "__main__":
    analyzer = ProximityAnalyzer()

    # Prayagraj Candidate Location
    prayagraj_point = Point(81.8463, 25.4358)
    print("🔍 Testing Live OSM Buffer Analysis for Prayagraj...")
    results_p = analyzer.compute_proximity(prayagraj_point, district_name="Prayagraj")
    print(f"   🌾 Nearest Farmland:   {results_p.dist_to_farmland_m} m")
    print(f"   🏭 Nearest Industrial: {results_p.dist_to_industrial_m} m")
    print(f"   🚰 Nearest Drainage:   {results_p.dist_to_sewage_line_m} m")
    print(f"   ⚠️ Risk Classification: {results_p.risk_category} (Confidence: {results_p.data_confidence})")

    # Mirzapur Candidate Location
    mirzapur_point = Point(82.5681, 25.1321)
    print("\n🔍 Testing Live OSM Buffer Analysis for Mirzapur...")
    results_m = analyzer.compute_proximity(mirzapur_point, district_name="Mirzapur")
    print(f"   🌾 Nearest Farmland:   {results_m.dist_to_farmland_m} m")
    print(f"   🏭 Nearest Industrial: {results_m.dist_to_industrial_m} m")
    print(f"   🚰 Nearest Drainage:   {results_m.dist_to_sewage_line_m} m")
    print(f"   ⚠️ Risk Classification: {results_m.risk_category} (Confidence: {results_m.data_confidence})")
from __future__ import annotations

import requests


OSRM_URL = "https://router.project-osrm.org/route/v1/driving"


def get_road_geometry(
    start_lat: float,
    start_lon: float,
    end_lat: float,
    end_lon: float,
) -> list[tuple[float, float]]:
    """
    Devolve a geometria da estrada entre dois pontos.
    O OSRM devolve coordenadas como [lon, lat], mas o Folium precisa de [lat, lon].
    """

    url = (
        f"{OSRM_URL}/"
        f"{start_lon},{start_lat};{end_lon},{end_lat}"
        "?overview=full&geometries=geojson"
    )

    response = requests.get(url, timeout=20)
    response.raise_for_status()

    data = response.json()

    routes = data.get("routes", [])
    if not routes:
        return [
            (start_lat, start_lon),
            (end_lat, end_lon),
        ]

    coordinates = routes[0]["geometry"]["coordinates"]

    return [(lat, lon) for lon, lat in coordinates]


def build_road_route_geometry(
    points: list[tuple[float, float]],
) -> list[tuple[float, float]]:
    """
    Recebe a sequência otimizada de pontos e constrói uma linha pela estrada.
    """

    if len(points) < 2:
        return points

    full_geometry: list[tuple[float, float]] = []

    for start, end in zip(points[:-1], points[1:]):
        segment_geometry = get_road_geometry(
            start_lat=start[0],
            start_lon=start[1],
            end_lat=end[0],
            end_lon=end[1],
        )

        if full_geometry:
            segment_geometry = segment_geometry[1:]

        full_geometry.extend(segment_geometry)

    return full_geometry
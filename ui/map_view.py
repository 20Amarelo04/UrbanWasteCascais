from __future__ import annotations

import folium
import requests
import streamlit as st
from streamlit_folium import st_folium

from core.models import OptimizationResult


OSRM_URL = "https://router.project-osrm.org/route/v1/driving"

ROUTE_COLORS = [
    "blue",
    "green",
    "red",
    "purple",
    "orange",
    "darkred",
    "cadetblue",
    "darkgreen",
]


@st.cache_data(show_spinner=False)
def get_road_segment(
    start_lat: float,
    start_lon: float,
    end_lat: float,
    end_lon: float,
) -> list[list[float]]:
    """
    Gets the road geometry between two points.

    OSRM returns coordinates as [longitude, latitude].
    Folium expects [latitude, longitude].
    """

    fallback = [
        [start_lat, start_lon],
        [end_lat, end_lon],
    ]

    url = (
        f"{OSRM_URL}/"
        f"{start_lon},{start_lat};{end_lon},{end_lat}"
        "?overview=full&geometries=geojson"
    )

    try:
        response = requests.get(url, timeout=20)
        response.raise_for_status()
        data = response.json()

    except requests.RequestException:
        return fallback

    routes = data.get("routes", [])
    if not routes:
        return fallback

    coordinates = routes[0].get("geometry", {}).get("coordinates", [])
    if not coordinates:
        return fallback

    return [
        [latitude, longitude]
        for longitude, latitude in coordinates
    ]


def build_road_geometry(
    coordinates: list[list[float]],
) -> list[list[float]]:
    if len(coordinates) < 2:
        return coordinates

    road_geometry: list[list[float]] = []

    for start, end in zip(coordinates[:-1], coordinates[1:]):
        segment = get_road_segment(
            start_lat=float(start[0]),
            start_lon=float(start[1]),
            end_lat=float(end[0]),
            end_lon=float(end[1]),
        )

        if road_geometry:
            segment = segment[1:]

        road_geometry.extend(segment)

    return road_geometry


def get_uncollected_dataframe(
    result: OptimizationResult,
):
    possible_names = [
        "uncollected_df",
        "uncollected_containers_df",
        "not_collected_df",
        "non_collected_df",
        "nao_recolhidos_df",
    ]

    for name in possible_names:
        dataframe = getattr(result, name, None)

        if dataframe is not None:
            return dataframe.copy()

    return None


def has_coordinates(dataframe) -> bool:
    return (
        dataframe is not None
        and not dataframe.empty
        and "latitude" in dataframe.columns
        and "longitude" in dataframe.columns
    )


def format_popup_value(value) -> str:
    if value is None or value != value:
        return ""

    return str(value)


def build_uncollected_popup(row) -> str:
    popup_lines = [
        "<b>Contentor não recolhido</b>",
    ]

    popup_fields = [
        ("ID", "container_id"),
        ("Nome", "container_name"),
        ("matrix_id", "matrix_id"),
        ("Resíduos", "waste_kg"),
        ("Motivo", "reason"),
    ]

    for label, column in popup_fields:
        if column not in row:
            continue

        value = format_popup_value(row[column])
        if not value:
            continue

        popup_lines.append(f"{label}: {value}")

    return "<br>".join(popup_lines)


def add_uncollected_markers(
    solution_map: folium.Map,
    result: OptimizationResult,
    show_uncollected: bool,
) -> None:
    if not show_uncollected:
        return

    uncollected_df = get_uncollected_dataframe(result)

    if not has_coordinates(uncollected_df):
        return

    layer = folium.FeatureGroup(
        name="Contentores não recolhidos",
        show=True,
    )

    for _, row in uncollected_df.iterrows():
        folium.CircleMarker(
            location=[
                row["latitude"],
                row["longitude"],
            ],
            radius=6,
            color="gray",
            fill=True,
            fill_color="lightgray",
            fill_opacity=0.85,
            weight=2,
            popup=build_uncollected_popup(row),
            tooltip="Não recolhido",
        ).add_to(layer)

    layer.add_to(solution_map)


def build_solution_map(
    result: OptimizationResult,
    selected_vehicle_ids: list[int] | None = None,
    show_uncollected: bool = True,
    draw_roads: bool = True,
) -> folium.Map:
    sequence_df = result.route_sequence_df.copy()
    uncollected_df = get_uncollected_dataframe(result)

    if sequence_df.empty and not has_coordinates(uncollected_df):
        return folium.Map(
            location=[38.72, -9.40],
            zoom_start=12,
        )

    center_df = (
        sequence_df
        if not sequence_df.empty
        else uncollected_df
    )

    center = [
        center_df["latitude"].mean(),
        center_df["longitude"].mean(),
    ]

    is_dark = st.session_state.get("theme_mode") == "Escuro"
    base_tiles = (
        "cartodbdark_matter"
        if is_dark
        else "cartodbpositron"
    )

    solution_map = folium.Map(
        location=center,
        zoom_start=12,
        tiles=base_tiles,
    )

    folium.TileLayer(
        "openstreetmap",
        name="OpenStreetMap",
        show=False,
    ).add_to(solution_map)

    add_uncollected_markers(
        solution_map=solution_map,
        result=result,
        show_uncollected=show_uncollected,
    )

    if sequence_df.empty:
        return solution_map

    sequence_df = sequence_df.sort_values(
        ["vehicle_id", "sequence"]
    )

    if selected_vehicle_ids:
        sequence_df = sequence_df[
            sequence_df["vehicle_id"].isin(selected_vehicle_ids)
        ]

    for vehicle_index, (
        vehicle_id,
        vehicle_points,
    ) in enumerate(sequence_df.groupby("vehicle_id")):
        color = ROUTE_COLORS[
            vehicle_index % len(ROUTE_COLORS)
        ]

        coordinates = vehicle_points[
            ["latitude", "longitude"]
        ].values.tolist()

        route_layer = folium.FeatureGroup(
            name=f"Veículo {vehicle_id}",
            show=True,
        )

        if len(coordinates) >= 2:
            line_coordinates = (
                build_road_geometry(coordinates)
                if draw_roads
                else coordinates
            )

            folium.PolyLine(
                line_coordinates,
                color=color,
                weight=5,
                opacity=0.85,
                tooltip=f"Veículo {vehicle_id}",
            ).add_to(route_layer)

        for _, row in vehicle_points.iterrows():
            event_type = row["event_type"]

            if event_type == "base":
                icon = "home"
                marker_color = "green"

            elif event_type == "landfill":
                icon = "trash"
                marker_color = "red"

            else:
                folium.CircleMarker(
                    location=[
                        row["latitude"],
                        row["longitude"],
                    ],
                    radius=5,
                    color=color,
                    fill=True,
                    fill_color=color,
                    fill_opacity=0.85,
                    weight=2,
                    popup=(
                        f"{row['vehicle_name']}<br>"
                        f"Sequência: {row['sequence']}<br>"
                        f"Tipo: {event_type}<br>"
                        f"matrix_id: {row['matrix_id']}"
                    ),
                    tooltip=f"{row['vehicle_name']} · Seq. {row['sequence']}",
                ).add_to(route_layer)

                continue

            folium.Marker(
                location=[
                    row["latitude"],
                    row["longitude"],
                ],
                popup=(
                    f"{row['vehicle_name']}<br>"
                    f"Sequência: {row['sequence']}<br>"
                    f"Tipo: {event_type}<br>"
                    f"matrix_id: {row['matrix_id']}"
                ),
                icon=folium.Icon(
                    color=marker_color,
                    icon=icon,
                ),
            ).add_to(route_layer)

        route_layer.add_to(solution_map)

    folium.LayerControl(
        collapsed=False,
    ).add_to(solution_map)

    return solution_map


def render_solution_map(
    result: OptimizationResult,
) -> None:
    sequence_df = result.route_sequence_df.copy()

    available_vehicle_ids = (
        sequence_df["vehicle_id"]
        .drop_duplicates()
        .astype(int)
        .tolist()
        if not sequence_df.empty
        else []
    )

    control_1, control_2, control_3 = st.columns([2, 1, 1])

    with control_1:
        selected_vehicle_ids = st.multiselect(
            "Veículos visíveis",
            options=available_vehicle_ids,
            default=available_vehicle_ids,
            format_func=lambda vehicle_id: f"Veículo {vehicle_id}",
            help=(
                "Permite isolar uma ou várias rotas para facilitar "
                "a leitura do mapa."
            ),
        )

    with control_2:
        draw_roads = st.toggle(
            "Rota pelas estradas",
            value=True,
            help=(
                "Quando ativo, usa OSRM para desenhar a rota sobre "
                "as estradas. Quando inativo, liga os pontos diretamente."
            ),
        )

    with control_3:
        show_uncollected = st.toggle(
            "Não recolhidos",
            value=True,
            help=(
                "Mostra no mapa os contentores que ficaram fora da solução, "
                "assinalados a cinza."
            ),
        )

    st.caption(
        "As linhas pelas estradas usam OSRM. Se o serviço externo "
        "falhar, a app mantém a rota em linha direta como fallback."
    )

    st_folium(
        build_solution_map(
            result=result,
            selected_vehicle_ids=selected_vehicle_ids,
            show_uncollected=show_uncollected,
            draw_roads=draw_roads,
        ),
        width=None,
        height=620,
    )

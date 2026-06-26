from __future__ import annotations

import streamlit as st

from ui.charts import (
    render_grade_chart,
    render_history_chart,
    render_route_timeline,
    render_segment_chart,
    render_vehicle_charts,
)
from ui.map_view import render_solution_map
from ui.metrics import render_summary_metrics
from ui.state import initialize_session_state
from ui.theme import page_header


initialize_session_state()

page_header(
    title="Resultados",
    subtitle=(
        "Explora a solução calculada por mapa, métricas, veículos, "
        "segmentos e contentores não recolhidos."
    ),
    label="Análise da solução",
)

result = st.session_state.optimization_result

if result is None:
    st.info(
        "Ainda não existe uma otimização calculada."
    )
    st.stop()

render_summary_metrics(result)

if not result.summary["solucao_viavel"]:
    st.warning("A solução tem violações de restrições.")

    for violation in result.summary["violacoes"]:
        st.write(f"- {violation}")
else:
    st.success("Solução viável segundo as restrições configuradas.")

tabs = st.tabs(
    [
        "Mapa",
        "Dashboard",
        "Veículos",
        "Segmentos",
        "Sequência",
        "Não recolhidos",
    ]
)

with tabs[0]:
    render_solution_map(result)

with tabs[1]:
    render_vehicle_charts(result)
    render_segment_chart(result)
    render_grade_chart(result)
    render_route_timeline(result)
    render_history_chart(result)

with tabs[2]:
    st.dataframe(
        result.vehicles_df,
        use_container_width=True,
        hide_index=True,
    )

with tabs[3]:
    segments_df = result.segments_df.copy()

    if not segments_df.empty:
        vehicle_ids = (
            segments_df["vehicle_id"]
            .drop_duplicates()
            .astype(int)
            .tolist()
        )

        selected_vehicle_ids = st.multiselect(
            "Filtrar veículos",
            options=vehicle_ids,
            default=vehicle_ids,
            format_func=lambda vehicle_id: f"Veículo {vehicle_id}",
            key="segments_vehicle_filter",
        )

        event_types = (
            segments_df["event_type"]
            .drop_duplicates()
            .astype(str)
            .tolist()
        )

        selected_event_types = st.multiselect(
            "Filtrar tipo de evento",
            options=event_types,
            default=event_types,
            key="segments_event_filter",
        )

        segments_df = segments_df[
            segments_df["vehicle_id"].isin(selected_vehicle_ids)
            & segments_df["event_type"].isin(selected_event_types)
        ]

    st.dataframe(
        segments_df,
        use_container_width=True,
        hide_index=True,
    )

with tabs[4]:
    sequence_df = result.route_sequence_df.copy()

    if not sequence_df.empty:
        vehicle_ids = (
            sequence_df["vehicle_id"]
            .drop_duplicates()
            .astype(int)
            .tolist()
        )

        selected_vehicle_ids = st.multiselect(
            "Filtrar veículos",
            options=vehicle_ids,
            default=vehicle_ids,
            format_func=lambda vehicle_id: f"Veículo {vehicle_id}",
            key="sequence_vehicle_filter",
        )

        sequence_df = sequence_df[
            sequence_df["vehicle_id"].isin(selected_vehicle_ids)
        ]

    st.dataframe(
        sequence_df,
        use_container_width=True,
        hide_index=True,
    )

with tabs[5]:
    if result.uncollected_df.empty:
        st.success("Todos os contentores foram recolhidos.")
    else:
        st.dataframe(
            result.uncollected_df,
            use_container_width=True,
            hide_index=True,
        )

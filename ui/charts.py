from __future__ import annotations

import plotly.express as px
import streamlit as st

from core.models import OptimizationResult


COLOR_SEQUENCE = [
    "#0f7b55",
    "#16a36f",
    "#2f6f90",
    "#c9831f",
    "#b5413e",
]


def polish_chart(figure):
    is_dark = st.session_state.get("theme_mode") == "Escuro"
    text_color = "#f4fbf7" if is_dark else "#17231f"
    muted_color = "#b8c9c0" if is_dark else "#52665d"
    grid_color = "#32443c" if is_dark else "#d4e2db"

    figure.update_layout(
        template="plotly_dark" if is_dark else "plotly_white",
        margin=dict(l=10, r=10, t=55, b=10),
        title_font=dict(
            size=18,
            color=text_color,
        ),
        font=dict(
            family="Arial",
            color=text_color,
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(255,255,255,0)",
        hovermode="x unified",
        legend=dict(
            font=dict(color=text_color),
            title=dict(font=dict(color=text_color)),
        ),
    )

    figure.update_xaxes(
        title_font=dict(color=text_color),
        tickfont=dict(color=muted_color),
        linecolor=grid_color,
        gridcolor=grid_color,
        zerolinecolor=grid_color,
    )

    figure.update_yaxes(
        title_font=dict(color=text_color),
        tickfont=dict(color=muted_color),
        linecolor=grid_color,
        gridcolor=grid_color,
        zerolinecolor=grid_color,
    )

    return figure


def prepare_segments_df(result: OptimizationResult):
    segments_df = result.segments_df.copy()

    if (
        not segments_df.empty
        and "vehicle_name" not in segments_df.columns
        and "vehicle_id" in segments_df.columns
    ):
        segments_df["vehicle_name"] = (
            "Veículo "
            + segments_df["vehicle_id"].astype(str)
        )

    return segments_df


def render_vehicle_charts(
    result: OptimizationResult,
) -> None:
    vehicles_df = result.vehicles_df.copy()

    if vehicles_df.empty:
        st.info("Não existem dados de veículos para apresentar.")
        return

    left, right = st.columns(2)

    with left:
        figure = px.bar(
            vehicles_df,
            x="vehicle_name",
            y="contentores",
            title="Contentores por veículo",
            color="vehicle_name",
            color_discrete_sequence=COLOR_SEQUENCE,
            labels={
                "vehicle_name": "Veículo",
                "contentores": "Contentores",
            },
        )

        st.plotly_chart(
            polish_chart(figure),
            width="stretch",
        )

    with right:
        figure = px.bar(
            vehicles_df,
            x="vehicle_name",
            y="combustivel_l",
            title="Combustível por veículo",
            color="vehicle_name",
            color_discrete_sequence=COLOR_SEQUENCE,
            labels={
                "vehicle_name": "Veículo",
                "combustivel_l": "Combustível (L)",
            },
        )

        st.plotly_chart(
            polish_chart(figure),
            width="stretch",
        )

    left, right = st.columns(2)

    with left:
        figure = px.bar(
            vehicles_df,
            x="vehicle_name",
            y="tempo_h",
            title="Tempo por veículo",
            color="vehicle_name",
            color_discrete_sequence=COLOR_SEQUENCE,
            labels={
                "vehicle_name": "Veículo",
                "tempo_h": "Tempo (h)",
            },
        )

        st.plotly_chart(
            polish_chart(figure),
            width="stretch",
        )

    with right:
        figure = px.scatter(
            vehicles_df,
            x="combustivel_l",
            y="contentores",
            size="distancia_km",
            color="vehicle_name",
            title="Eficiência operacional",
            color_discrete_sequence=COLOR_SEQUENCE,
            labels={
                "vehicle_name": "Veículo",
                "combustivel_l": "Combustível (L)",
                "contentores": "Contentores",
                "distancia_km": "Distância (km)",
            },
        )

        st.plotly_chart(
            polish_chart(figure),
            width="stretch",
        )


def render_segment_chart(
    result: OptimizationResult,
) -> None:
    segments_df = prepare_segments_df(result)

    if segments_df.empty:
        return

    figure = px.line(
        segments_df,
        x="sequence",
        y="fuel_l",
        color="vehicle_name",
        markers=True,
        title="Combustível por segmento",
        color_discrete_sequence=COLOR_SEQUENCE,
        labels={
            "sequence": "Sequência",
            "fuel_l": "Combustível (L)",
            "vehicle_name": "Veículo",
        },
    )

    st.plotly_chart(
        polish_chart(figure),
        width="stretch",
    )


def render_grade_chart(
    result: OptimizationResult,
) -> None:
    segments_df = prepare_segments_df(result)

    if segments_df.empty or "grade" not in segments_df:
        return

    figure = px.bar(
        segments_df,
        x="sequence",
        y="grade",
        color="vehicle_name",
        title="Declive por segmento",
        color_discrete_sequence=COLOR_SEQUENCE,
        labels={
            "sequence": "Sequência",
            "grade": "Declive",
            "vehicle_name": "Veículo",
        },
    )

    st.plotly_chart(
        polish_chart(figure),
        width="stretch",
    )


def render_route_timeline(
    result: OptimizationResult,
) -> None:
    sequence_df = result.route_sequence_df.copy()

    if sequence_df.empty:
        return

    figure = px.scatter(
        sequence_df,
        x="sequence",
        y="vehicle_name",
        color="event_type",
        hover_data=[
            "matrix_id",
            "latitude",
            "longitude",
        ],
        title="Sequência de eventos por veículo",
        color_discrete_map={
            "base": "#0f7b55",
            "landfill": "#b5413e",
            "container": "#2f6f90",
        },
        labels={
            "sequence": "Sequência",
            "vehicle_name": "Veículo",
            "event_type": "Tipo",
        },
    )

    figure.update_traces(marker=dict(size=12))

    st.plotly_chart(
        polish_chart(figure),
        width="stretch",
    )


def render_history_chart(
    result: OptimizationResult,
) -> None:
    history = result.solver_output.history

    if not history:
        return

    history_df = result.solver_output.history

    if (
        not isinstance(history_df, list)
        or "global_best_score" not in history_df[0]
    ):
        return

    import pandas as pd

    dataframe = pd.DataFrame(history_df)

    figure = px.line(
        dataframe,
        x="iteration",
        y="global_best_score",
        title="Evolução do melhor score",
        markers=True,
        color_discrete_sequence=COLOR_SEQUENCE,
        labels={
            "iteration": "Iteração",
            "global_best_score": "Melhor score",
        },
    )

    st.plotly_chart(
        polish_chart(figure),
        width="stretch",
    )

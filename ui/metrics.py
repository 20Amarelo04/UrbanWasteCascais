from __future__ import annotations

import streamlit as st

from core.models import OptimizationResult


def render_summary_metrics(
    result: OptimizationResult,
) -> None:
    summary = result.summary

    collected = summary["contentores_recolhidos"]
    uncollected = summary["contentores_nao_recolhidos"]
    total_containers = collected + uncollected
    collection_rate = (
        collected / total_containers
        if total_containers
        else 0.0
    )

    columns = st.columns(4)

    columns[0].metric(
        "Contentores recolhidos",
        collected,
    )

    columns[1].metric(
        "Não recolhidos",
        uncollected,
    )

    columns[2].metric(
        "Distância total",
        f"{summary['distancia_total_km']:.2f} km",
    )

    columns[3].metric(
        "Combustível",
        f"{summary['combustivel_total_l']:.2f} L",
    )

    columns = st.columns(4)

    columns[0].metric(
        "Veículos usados",
        f"{summary['veiculos_utilizados']}/"
        f"{summary['veiculos_disponiveis']}",
    )

    columns[1].metric(
        "Maior rota",
        f"{summary['maior_tempo_veiculo_h']:.2f} h",
    )

    columns[2].metric(
        "Score",
        f"{summary['score_objetivo']:.4f}",
    )

    columns[3].metric(
        "Tempo de cálculo",
        f"{summary['runtime_s']:.2f} s",
    )

    st.progress(
        collection_rate,
        text=f"Cobertura da recolha: {collection_rate:.1%}",
    )

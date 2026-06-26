from __future__ import annotations

import numpy as np
import streamlit as st

from core.data_loader import load_data_bundle
from ui.theme import page_header


page_header(
    title="Validação dos dados",
    subtitle=(
        "Confirma se pontos, matrizes, base, aterro e declives "
        "estão prontos para alimentar os algoritmos."
    ),
    label="Qualidade dos dados",
)


try:
    data = load_data_bundle()

    st.success("Dados carregados com sucesso.")

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Nós",
        len(data.points),
    )

    col2.metric(
        "Contentores",
        len(data.container_matrix_ids),
    )

    col3.metric(
        "Dimensão da matriz",
        data.distance_matrix_m.shape[0],
    )

    col4, col5 = st.columns(2)
    col4.metric("Base", data.base_matrix_id)
    col5.metric("Aterro", data.landfill_matrix_id)

    slopes = data.slope_matrix[np.isfinite(data.slope_matrix)]

    if slopes.size:
        st.subheader("Declives")
        slope_col1, slope_col2, slope_col3 = st.columns(3)
        slope_col1.metric("Declive mínimo", f"{slopes.min():.2%}")
        slope_col2.metric("Declive médio", f"{slopes.mean():.2%}")
        slope_col3.metric("Declive máximo", f"{slopes.max():.2%}")

    tab_points, tab_matrices = st.tabs(
        ["Pontos", "Resumo das matrizes"]
    )

    with tab_points:
        selected_types = st.multiselect(
            "Tipos de ponto",
            options=sorted(data.points["type"].unique()),
            default=sorted(data.points["type"].unique()),
        )

        filtered_points = data.points[
            data.points["type"].isin(selected_types)
        ]

        st.dataframe(
            filtered_points,
            width="stretch",
            hide_index=True,
        )

    with tab_matrices:
        matrix_col1, matrix_col2 = st.columns(2)
        matrix_col1.metric(
            "Distância média",
            f"{data.distance_matrix_m[data.distance_matrix_m > 0].mean() / 1000:.2f} km",
        )
        matrix_col2.metric(
            "Tempo médio",
            f"{data.time_matrix_s[data.time_matrix_s > 0].mean() / 60:.2f} min",
        )

        st.write("Amostra da matriz de distâncias")
        st.dataframe(
            data.distance_matrix_m[:20, :20],
            width="stretch",
        )

except Exception as error:
    st.error(f"Erro na validação dos dados: {error}")

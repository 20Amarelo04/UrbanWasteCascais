from __future__ import annotations

import streamlit as st

from core.data_loader import load_data_bundle
from ui.theme import info_card, page_header


page_header(
    title="UrbanWasteCascais",
    subtitle=(
        "Planeamento inteligente de rotas de recolha urbana, "
        "com otimização de lixo não recolhido, combustível e distância."
    ),
    label="Painel operacional",
)

try:
    data = load_data_bundle()

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Pontos na rede", len(data.points))
    col2.metric("Contentores", len(data.container_matrix_ids))
    col3.metric("Base", data.base_matrix_id)
    col4.metric("Aterro", data.landfill_matrix_id)

except Exception as error:
    st.warning(f"Não foi possível carregar os dados: {error}")

st.divider()

left, middle, right = st.columns(3)

with left:
    info_card(
        title="Otimização",
        body=(
            "Escolhe OR-Tools ou MMAS, define veículos, pesos de "
            "combustível/distância e restrições operacionais."
        ),
        badge="Passo 1",
    )

with middle:
    info_card(
        title="Resultados",
        body=(
            "Analisa métricas, rotas por veículo, segmentos, "
            "sequência de recolha e contentores não recolhidos."
        ),
        badge="Passo 2",
    )

with right:
    info_card(
        title="Mapa interativo",
        body=(
            "Visualiza a rota pelas estradas, filtra veículos e "
            "mantém os pontos não recolhidos assinalados a cinza."
        ),
        badge="Passo 3",
    )

st.info(
    "Começa pela página Otimização. Depois de calcular, os resultados "
    "ficam disponíveis automaticamente na página Resultados."
)

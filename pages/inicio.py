from __future__ import annotations

import streamlit as st

from ui.theme import info_card, page_header


page_header(
    title="Urban Waste",
    subtitle=(
        "Sistema de otimização inteligente de rotas de recolha urbana "
        "com foco na minimização de lixo não recolhido, combustível e distância."
    ),
    label="Painel operacional",
)

st.markdown(
    """
    ## Problema de otimização

    O objetivo deste sistema é resolver o problema de **planeamento de rotas de recolha de resíduos urbanos**, 
    garantindo eficiência operacional e redução de custos.

    O problema consiste em decidir as melhores rotas para veículos de recolha, tendo em conta:

    - Minimização de lixo não recolhido
    - Minimização de consumo de combustível
    - Minimização de distância total percorrida

    
    O sistema respeita restrições reais como:

    - Capacidade dos veículos
    - Tempo máximo de operação
    - Necessidade de descarga no aterro
    - Estrutura base → recolha → aterro → base

    
    Dois algoritmos são utilizados:
    - MMAS (Meta-Heurística baseada em colónias de formigas)
    - OR-Tools
    """
)

st.divider()

left, middle, right = st.columns(3)

with left:
    info_card(
        title="Otimização",
        body=(
            "Escolhe o algoritmo (MMAS ou OR-Tools), define a frota e "
            "configura os pesos de otimização."
        ),
        badge="Passo 1",
    )

with middle:
    info_card(
        title="Resultados",
        body=(
            "Visualiza rotas por veículo, métricas de desempenho, "
            "e análise de contentores não recolhidos."
        ),
        badge="Passo 2",
    )

with right:
    info_card(
        title="Mapa interativo",
        body=(
            "Explora as rotas em mapa, visualiza estradas reais e "
            "identifica contentores não recolhidos a cinza."
        ),
        badge="Passo 3",
    )

st.info(
    "Começa na página de Otimização. Após execução, os resultados "
    "são automaticamente disponibilizados na secção de Resultados."
)
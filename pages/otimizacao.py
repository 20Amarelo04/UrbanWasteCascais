from __future__ import annotations

import streamlit as st

from core.data_loader import load_data_bundle
from services.optimization_service import run_optimization
from ui.forms import render_optimization_form
from ui.state import initialize_session_state
from ui.theme import page_header


initialize_session_state()

page_header(
    title="Otimização de rotas",
    subtitle=(
        "Configura a frota, escolhe o algoritmo e calcula rotas "
        "minimizando lixo não recolhido, combustível e distância."
    ),
    label="Motor de decisão",
)

request = render_optimization_form()

left, right = st.columns([2, 1])

with left:
    run_clicked = st.button(
        "Executar otimização",
        type="primary",
        width="stretch",
        disabled=st.session_state.is_optimizing,
    )

with right:
    if st.session_state.optimization_result is None:
        st.info("Sem resultados calculados nesta sessão.")
    else:
        st.success("Resultado disponível.")

if run_clicked and not st.session_state.is_optimizing:
    st.session_state.pending_optimization_request = request
    st.session_state.is_optimizing = True
    st.rerun()

if (
    st.session_state.is_optimizing
    and st.session_state.pending_optimization_request is not None
):
    request_to_run = st.session_state.pending_optimization_request

    try:
        with st.status(
            "A preparar dados e calcular rotas...",
            expanded=True,
        ) as status:
            st.write("A carregar matrizes, contentores e pontos.")
            data = load_data_bundle()

            st.write(
                "A executar o algoritmo "
                f"{request_to_run.algorithm.upper()}."
            )
            result = run_optimization(
                data=data,
                request=request_to_run,
            )

            st.session_state.optimization_result = result
            st.session_state.optimization_error = None

            status.update(
                label="Otimização concluída.",
                state="complete",
                expanded=False,
            )

        st.success(
            "Rotas calculadas. Abre a página Resultados para explorar "
            "o mapa, os veículos e os gráficos."
        )

    except Exception as error:
        st.session_state.optimization_error = str(error)
        st.error(f"Erro na otimização: {error}")

    finally:
        st.session_state.is_optimizing = False
        st.session_state.pending_optimization_request = None

if st.session_state.optimization_result is not None:
    summary = st.session_state.optimization_result.summary
    col1, col2, col3 = st.columns(3)
    col1.metric(
        "Contentores recolhidos",
        summary["contentores_recolhidos"],
    )
    col2.metric(
        "Distância total",
        f"{summary['distancia_total_km']:.2f} km",
    )
    col3.metric(
        "Combustível",
        f"{summary['combustivel_total_l']:.2f} L",
    )

from __future__ import annotations

import streamlit as st

from ui.theme import apply_theme, render_theme_switcher


st.set_page_config(
    page_title="UrbanWasteCascais",
    page_icon="UW",
    layout="wide",
    initial_sidebar_state="expanded",
)

theme_mode = render_theme_switcher()
apply_theme(theme_mode)


navigation = st.navigation(
    [
        st.Page(
            "pages/inicio.py",
            title="Início",
            icon=":material/home:",
            default=True,
        ),
        st.Page(
            "pages/otimizacao.py",
            title="Otimização",
            icon=":material/route:",
        ),
        st.Page(
            "pages/validacao.py",
            title="Validação dos dados",
            icon=":material/verified:",
        ),
        st.Page(
            "pages/resultados.py",
            title="Resultados",
            icon=":material/monitoring:",
        ),
        st.Page(
            "pages/ajuda.py",
            title="Ajuda",
            icon=":material/help:",
        ),
    ]
)

navigation.run()

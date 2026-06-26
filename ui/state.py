from __future__ import annotations

import streamlit as st


def initialize_session_state() -> None:
    defaults = {
        "optimization_result": None,
        "optimization_error": None,
        "loaded_data": None,
        "is_optimizing": False,
        "pending_optimization_request": None,
    }

    for key, default_value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default_value


def clear_optimization_result() -> None:
    st.session_state.optimization_result = None
    st.session_state.optimization_error = None

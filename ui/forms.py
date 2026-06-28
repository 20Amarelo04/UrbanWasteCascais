from __future__ import annotations

import streamlit as st

from config import CONTAINERS, OBJECTIVE_WEIGHTS, OPERATION
from core.models import (
    MMASConfig,
    ORToolsConfig,
    ObjectiveConfig,
    OptimizationRequest,
    VehicleSpec,
)


def render_slider_limits(
    minimum: float,
    maximum: float,
) -> None:
    st.markdown(
        f"""
        <div class="uw-slider-limits">
            <span>{minimum:.2f}</span>
            <span>{maximum:.2f}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_vehicle_inputs(
    number_of_vehicles: int,
) -> list[VehicleSpec]:
    vehicles: list[VehicleSpec] = []

    st.subheader("Frota")

    for index in range(number_of_vehicles):
        with st.expander(
            f"Camião {index + 1}",
            expanded=index == 0,
        ):
            col1, col2, col3 = st.columns(3)

            with col1:
                tare_mass_kg = st.number_input(
                    "Tara do veículo (kg)",
                    min_value=1000.0,
                    max_value=30000.0,
                    value=6000.0 + index * 500.0,
                    step=500.0,
                    key=f"vehicle_tare_{index}",
                    help=(
                        "Peso do camião vazio. Entra no cálculo do "
                        "combustível, juntamente com a carga recolhida."
                    ),
                )

            with col2:
                capacity_kg = st.number_input(
                    "Capacidade útil (kg)",
                    min_value=150.0,
                    max_value=20000.0,
                    value=3000.0,
                    step=150.0,
                    key=f"vehicle_capacity_{index}",
                    help=(
                        "Quantidade máxima de resíduos que o camião "
                        "consegue transportar antes de descarregar."
                    ),
                )

            with col3:
                shift_duration_h = st.number_input(
                    "Duração do turno (h)",
                    min_value=1.0,
                    max_value=24.0,
                    value=OPERATION.shift_duration_s / 3600,
                    step=0.5,
                    key=f"vehicle_shift_{index}",
                    help=(
                        "Tempo máximo disponível para esse veículo "
                        "sair da base, recolher, descarregar e regressar."
                    ),
                )

        vehicles.append(
            VehicleSpec(
                vehicle_id=index + 1,
                name=f"Camião {index + 1}",
                tare_mass_kg=tare_mass_kg,
                capacity_kg=capacity_kg,
                shift_duration_s=int(
                    shift_duration_h * 3600
                ),
            )
        )

    return vehicles


def render_objective_config() -> ObjectiveConfig:
    st.subheader("Função objetivo")

    st.info(
        "Objetivo: minimizar lixo não recolhido, combustível e distância."
    )

    st.markdown(
        """
        **Prioridade fixa**

        1. Minimizar contentores/lixo não recolhidos.
        2. Entre soluções equivalentes, minimizar combustível e distância.
        """
    )

    col1, col2 = st.columns(2)

    with col1:
        distance_weight = st.slider(
            "Peso da distância",
            min_value=0.0,
            max_value=1.0,
            value=float(OBJECTIVE_WEIGHTS.distance),
            step=0.05,
            help=(
                "Quanto maior este peso, mais o algoritmo tenta reduzir "
                "quilómetros percorridos."
            ),
        )
        render_slider_limits(0.0, 1.0)

    with col2:
        fuel_weight = st.slider(
            "Peso do combustível",
            min_value=0.0,
            max_value=1.0,
            value=float(OBJECTIVE_WEIGHTS.fuel),
            step=0.05,
            help=(
                "Quanto maior este peso, mais o algoritmo tenta reduzir "
                "litros consumidos, considerando carga e declive."
            ),
        )
        render_slider_limits(0.0, 1.0)

    total = distance_weight + fuel_weight

    if total <= 0:
        st.warning(
            "A soma dos pesos de distância e combustível tem de ser "
            "superior a zero."
        )
        total = 1.0

    objective = ObjectiveConfig(
        distance_weight=distance_weight / total,
        time_weight=0.0,
        fuel_weight=fuel_weight / total,
    )

    st.caption(
        "Pesos normalizados: "
        f"distância {objective.distance_weight:.0%}, "
        f"combustível {objective.fuel_weight:.0%}. "
        "Tempo = 0% na função objetivo."
    )

    return objective


def render_mmas_config() -> MMASConfig:
    with st.expander("Parâmetros MMAS", expanded=True):
        col1, col2, col3 = st.columns(3)

        with col1:
            num_ants = st.number_input(
                "Número de formigas",
                min_value=1,
                max_value=500,
                value=20,
                step=5,
                help=(
                    "Número de soluções testadas em cada iteração do MMAS. "
                    "Valores maiores exploram mais, mas demoram mais."
                ),
            )

            elite_ants = st.number_input(
                "Formigas elite",
                min_value=1,
                max_value=50,
                value=3,
                step=1,
                help=(
                    "Número de melhores soluções que reforçam os caminhos "
                    "promissores no MMAS."
                ),
            )

        with col2:
            num_iterations = st.number_input(
                "Número de iterações",
                min_value=1,
                max_value=500,
                value=50,
                step=5,
                help=(
                    "Quantidade de ciclos de procura do MMAS. Mais iterações "
                    "podem melhorar a solução, mas aumentam o tempo."
                ),
            )

            stagnation_limit = st.number_input(
                "Limite de estagnação",
                min_value=1,
                max_value=100,
                value=20,
                step=1,
                help=(
                    "Número de iterações sem melhoria antes de refrescar "
                    "a procura."
                ),
            )

        with col3:
            candidate_list_size = st.number_input(
                "Lista de candidatos",
                min_value=1,
                max_value=100,
                value=15,
                step=1,
                help=(
                    "Número de contentores próximos considerados em cada "
                    "decisão de rota do MMAS."
                ),
            )

    return MMASConfig(
        num_ants=num_ants,
        num_iterations=num_iterations,
        candidate_list_size=candidate_list_size,
        elite_ants=elite_ants,
        stagnation_limit=stagnation_limit,
        random_seed=42,
    )


def render_ortools_config() -> ORToolsConfig:
    with st.expander("Parâmetros OR-Tools", expanded=True):
        col1, col2 = st.columns(2)

        with col1:
            time_limit_s = st.number_input(
                "Tempo máximo de procura (s)",
                min_value=1,
                max_value=300,
                value=20,
                step=5,
                help=(
                    "Tempo máximo dado ao OR-Tools para procurar uma solução."
                ),
            )

        with col2:
            solution_penalty = st.number_input(
                "Penalização por contentor não recolhido",
                min_value=1000,
                max_value=100_000_000,
                value=1_000_000,
                step=100_000,
                help=(
                    "Custo artificial aplicado quando um contentor fica por "
                    "recolher. Valores maiores pressionam o solver a recolher "
                    "mais contentores."
                ),
            )

    return ORToolsConfig(
        time_limit_s=time_limit_s,
        solution_penalty=solution_penalty,
    )


def render_optimization_form() -> OptimizationRequest:
    st.sidebar.header("Configuração da corrida")
    st.sidebar.caption(
        "Define o algoritmo, a operação e a frota antes "
        "de lançar a otimização."
    )

    algorithm_label = st.sidebar.radio(
        "Algoritmo",
        options=["OR-Tools", "MMAS"],
        index=0,
        horizontal=True,
        help=(
            "OR-Tools é mais direto e estável. MMAS é uma metaheurística "
            "inspirada em colónias de formigas, útil para experimentar "
            "soluções alternativas."
        ),
    )

    algorithm = (
        "or-tools"
        if algorithm_label == "OR-Tools"
        else "mmas"
    )

    number_of_vehicles = st.sidebar.number_input(
        "Número de veículos",
        min_value=1,
        max_value=10,
        value=2,
        step=1,
        help="Quantidade de camiões disponíveis para a operação.",
    )

    st.sidebar.subheader("Operação")

    container_load_kg = st.sidebar.number_input(
        "Carga por contentor (kg)",
        min_value=1.0,
        max_value=2000.0,
        value=float(CONTAINERS.load_kg),
        step=10.0,
        help=(
            "Estimativa de resíduos recolhidos em cada contentor. "
            "Afeta capacidade, descargas e combustível."
        ),
    )

    service_time_min = st.sidebar.number_input(
        "Tempo de serviço por contentor (min)",
        min_value=0.0,
        max_value=60.0,
        value=CONTAINERS.service_time_s / 60,
        step=0.5,
        help=(
            "Tempo médio parado para recolher cada contentor."
        ),
    )

    unload_time_min = st.sidebar.number_input(
        "Tempo de descarga no aterro (min)",
        min_value=0.0,
        max_value=120.0,
        value=OPERATION.unload_time_s / 60,
        step=1.0,
        help=(
            "Tempo gasto sempre que o camião vai descarregar ao aterro."
        ),
    )

    max_unloads = st.sidebar.number_input(
        "Máximo de descargas por veículo",
        min_value=0,
        max_value=50,
        value=OPERATION.max_unloads_per_vehicle,
        step=1,
        help=(
            "Número máximo de viagens ao aterro permitidas por veículo."
        ),
    )

    st.markdown(
        '<div class="uw-section-label">Parâmetros da solução</div>',
        unsafe_allow_html=True,
    )

    vehicles = render_vehicle_inputs(int(number_of_vehicles))
    objective = render_objective_config()

    mmas = None
    ortools = None

    if algorithm == "mmas":
        mmas = render_mmas_config()

    else:
        ortools = render_ortools_config()

    return OptimizationRequest(
        algorithm=algorithm,
        vehicles=vehicles,
        container_load_kg=container_load_kg,
        service_time_s=int(service_time_min * 60),
        unload_time_s=int(unload_time_min * 60),
        max_unloads=int(max_unloads),
        objective=objective,
        mmas=mmas,
        ortools=ortools,
    )

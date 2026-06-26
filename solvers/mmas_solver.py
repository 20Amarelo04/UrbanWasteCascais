from __future__ import annotations

import time
from dataclasses import dataclass

import numpy as np

from core.fuel_model import calculate_segment_metrics
from core.models import (
    DataBundle,
    MMASConfig,
    OptimizationRequest,
    SolutionEvaluation,
    SolverOutput,
    VehicleSpec,
)
from core.objective import (
    ObjectiveScales,
    build_objective_scales,
    calculate_heuristic_value,
)
from core.route_evaluator import evaluate_solution


EPSILON = 1e-12
UNCOLLECTED_PENALTY = 1000.0
INFEASIBLE_PENALTY = 1_000_000.0


@dataclass
class AntSolution:
    routes: list[list[int]]
    evaluation: SolutionEvaluation


def validate_mmas_config(
    config: MMASConfig,
) -> None:
    if config.num_ants <= 0:
        raise ValueError(
            "O número de formigas deve ser positivo."
        )

    if config.num_iterations <= 0:
        raise ValueError(
            "O número de iterações deve ser positivo."
        )

    if config.alpha < 0:
        raise ValueError(
            "Alpha não pode ser negativo."
        )

    if config.beta < 0:
        raise ValueError(
            "Beta não pode ser negativo."
        )

    if not 0 < config.evaporation_rate < 1:
        raise ValueError(
            "A taxa de evaporação deve estar "
            "entre 0 e 1."
        )

    if config.elite_ants <= 0:
        raise ValueError(
            "O número de formigas elite "
            "deve ser positivo."
        )

    if config.candidate_list_size <= 0:
        raise ValueError(
            "A lista de candidatos deve "
            "ter tamanho positivo."
        )

    if not 0 < config.tau_min_ratio < 1:
        raise ValueError(
            "tau_min_ratio deve estar "
            "entre 0 e 1."
        )

    if config.stagnation_limit <= 0:
        raise ValueError(
            "O limite de estagnação "
            "deve ser positivo."
        )


def build_neighbour_lists(
    data: DataBundle,
    candidate_list_size: int,
) -> dict[int, list[int]]:
    container_ids = np.asarray(
        data.container_matrix_ids,
        dtype=int,
    )

    number_to_store = min(
        max(candidate_list_size * 3, candidate_list_size),
        len(container_ids),
    )

    neighbour_lists: dict[int, list[int]] = {}

    for current_node in range(
        data.distance_matrix_m.shape[0]
    ):
        distances = data.distance_matrix_m[
            current_node,
            container_ids,
        ]

        order = np.argsort(
            distances,
            kind="stable",
        )

        ordered_candidates = container_ids[
            order
        ]

        ordered_candidates = ordered_candidates[
            ordered_candidates != current_node
        ]

        neighbour_lists[current_node] = (
            ordered_candidates[
                :number_to_store
            ]
            .astype(int)
            .tolist()
        )

    return neighbour_lists


def build_candidate_pool(
    current_node: int,
    unvisited: set[int],
    neighbour_lists: dict[int, list[int]],
    candidate_list_size: int,
    rng: np.random.Generator,
) -> list[int]:
    local_candidates = [
        node
        for node in neighbour_lists[current_node]
        if node in unvisited
    ]

    selected = local_candidates[
        :candidate_list_size
    ]

    if len(selected) >= candidate_list_size:
        return selected

    selected_set = set(selected)

    remaining = np.asarray(
        list(unvisited - selected_set),
        dtype=int,
    )

    if remaining.size == 0:
        return selected

    number_to_add = min(
        candidate_list_size - len(selected),
        remaining.size,
    )

    random_candidates = rng.choice(
        remaining,
        size=number_to_add,
        replace=False,
    )

    selected.extend(
        int(node)
        for node in np.atleast_1d(
            random_candidates
        )
    )

    return selected


def can_visit_container(
    data: DataBundle,
    current_node: int,
    candidate_node: int,
    current_load_kg: float,
    current_time_s: float,
    number_of_unloads: int,
    vehicle: VehicleSpec,
    request: OptimizationRequest,
) -> bool:
    new_load_kg = (
        current_load_kg
        + request.container_load_kg
    )

    if new_load_kg > vehicle.capacity_kg + EPSILON:
        return False

    if number_of_unloads >= request.max_unloads:
        return False

    travel_to_container_s = float(
        data.time_matrix_s[
            current_node,
            candidate_node,
        ]
    )

    travel_to_landfill_s = float(
        data.time_matrix_s[
            candidate_node,
            data.landfill_matrix_id,
        ]
    )

    landfill_to_base_s = float(
        data.time_matrix_s[
            data.landfill_matrix_id,
            data.base_matrix_id,
        ]
    )

    minimum_completion_time_s = (
        current_time_s
        + travel_to_container_s
        + request.service_time_s
        + travel_to_landfill_s
        + request.unload_time_s
        + landfill_to_base_s
    )

    return (
        minimum_completion_time_s
        <= vehicle.shift_duration_s + EPSILON
    )


def select_next_container(
    data: DataBundle,
    current_node: int,
    current_load_kg: float,
    current_time_s: float,
    number_of_unloads: int,
    unvisited: set[int],
    vehicle: VehicleSpec,
    request: OptimizationRequest,
    scales: ObjectiveScales,
    pheromone: np.ndarray,
    neighbour_lists: dict[int, list[int]],
    config: MMASConfig,
    rng: np.random.Generator,
) -> int | None:
    candidate_pool = build_candidate_pool(
        current_node=current_node,
        unvisited=unvisited,
        neighbour_lists=neighbour_lists,
        candidate_list_size=(
            config.candidate_list_size
        ),
        rng=rng,
    )

    feasible_candidates: list[int] = []
    desirabilities: list[float] = []

    for candidate_node in candidate_pool:
        if not can_visit_container(
            data=data,
            current_node=current_node,
            candidate_node=candidate_node,
            current_load_kg=current_load_kg,
            current_time_s=current_time_s,
            number_of_unloads=number_of_unloads,
            vehicle=vehicle,
            request=request,
        ):
            continue

        metrics = calculate_segment_metrics(
            data=data,
            from_matrix_id=current_node,
            to_matrix_id=candidate_node,
            tare_mass_kg=vehicle.tare_mass_kg,
            current_load_kg=current_load_kg,
        )

        heuristic = calculate_heuristic_value(
            distance_m=metrics["distance_m"],
            time_s=metrics["time_s"],
            fuel_l=metrics["fuel_l"],
            scales=scales,
            objective=request.objective,
        )

        tau = max(
            float(
                pheromone[
                    current_node,
                    candidate_node,
                ]
            ),
            EPSILON,
        )

        desirability = (
            tau**config.alpha
            * heuristic**config.beta
        )

        feasible_candidates.append(
            candidate_node
        )

        desirabilities.append(
            float(desirability)
        )

    if not feasible_candidates:
        return None

    probabilities = np.asarray(
        desirabilities,
        dtype=float,
    )

    probability_sum = float(
        probabilities.sum()
    )

    if (
        probability_sum <= 0
        or not np.isfinite(probability_sum)
    ):
        return int(
            feasible_candidates[
                int(np.argmax(probabilities))
            ]
        )

    probabilities /= probability_sum

    selected_index = int(
        rng.choice(
            len(feasible_candidates),
            p=probabilities,
        )
    )

    return int(
        feasible_candidates[selected_index]
    )


def can_unload_and_return(
    data: DataBundle,
    current_node: int,
    current_time_s: float,
    vehicle: VehicleSpec,
    request: OptimizationRequest,
) -> bool:
    travel_to_landfill_s = float(
        data.time_matrix_s[
            current_node,
            data.landfill_matrix_id,
        ]
    )

    landfill_to_base_s = float(
        data.time_matrix_s[
            data.landfill_matrix_id,
            data.base_matrix_id,
        ]
    )

    completion_time_s = (
        current_time_s
        + travel_to_landfill_s
        + request.unload_time_s
        + landfill_to_base_s
    )

    return (
        completion_time_s
        <= vehicle.shift_duration_s + EPSILON
    )


def construct_vehicle_route(
    data: DataBundle,
    vehicle: VehicleSpec,
    request: OptimizationRequest,
    scales: ObjectiveScales,
    pheromone: np.ndarray,
    neighbour_lists: dict[int, list[int]],
    unvisited: set[int],
    config: MMASConfig,
    rng: np.random.Generator,
) -> list[int]:
    route = [
        data.base_matrix_id
    ]

    current_node = data.base_matrix_id
    current_load_kg = 0.0
    current_time_s = 0.0
    number_of_unloads = 0

    while unvisited:
        next_container = select_next_container(
            data=data,
            current_node=current_node,
            current_load_kg=current_load_kg,
            current_time_s=current_time_s,
            number_of_unloads=number_of_unloads,
            unvisited=unvisited,
            vehicle=vehicle,
            request=request,
            scales=scales,
            pheromone=pheromone,
            neighbour_lists=neighbour_lists,
            config=config,
            rng=rng,
        )

        if next_container is not None:
            travel_time_s = float(
                data.time_matrix_s[
                    current_node,
                    next_container,
                ]
            )

            route.append(
                next_container
            )

            current_time_s += (
                travel_time_s
                + request.service_time_s
            )

            current_load_kg += (
                request.container_load_kg
            )

            current_node = next_container

            unvisited.remove(
                next_container
            )

            continue

        if (
            current_load_kg > EPSILON
            and number_of_unloads
            < request.max_unloads
            and can_unload_and_return(
                data=data,
                current_node=current_node,
                current_time_s=current_time_s,
                vehicle=vehicle,
                request=request,
            )
        ):
            travel_to_landfill_s = float(
                data.time_matrix_s[
                    current_node,
                    data.landfill_matrix_id,
                ]
            )

            route.append(
                data.landfill_matrix_id
            )

            current_time_s += (
                travel_to_landfill_s
                + request.unload_time_s
            )

            current_node = (
                data.landfill_matrix_id
            )

            current_load_kg = 0.0
            number_of_unloads += 1

            if (
                number_of_unloads
                >= request.max_unloads
            ):
                break

            continue

        break

    if current_load_kg > EPSILON:
        if (
            number_of_unloads
            < request.max_unloads
            and can_unload_and_return(
                data=data,
                current_node=current_node,
                current_time_s=current_time_s,
                vehicle=vehicle,
                request=request,
            )
        ):
            route.append(
                data.landfill_matrix_id
            )

            current_time_s += float(
                data.time_matrix_s[
                    current_node,
                    data.landfill_matrix_id,
                ]
            )

            current_time_s += (
                request.unload_time_s
            )

            current_node = (
                data.landfill_matrix_id
            )

            current_load_kg = 0.0
            number_of_unloads += 1

    if current_node != data.base_matrix_id:
        route.append(
            data.base_matrix_id
        )

    elif len(route) == 1:
        route.append(
            data.base_matrix_id
        )

    return route


def construct_ant_solution(
    data: DataBundle,
    request: OptimizationRequest,
    scales: ObjectiveScales,
    pheromone: np.ndarray,
    neighbour_lists: dict[int, list[int]],
    config: MMASConfig,
    rng: np.random.Generator,
) -> AntSolution:
    unvisited = set(
        data.container_matrix_ids
    )

    routes = [
        [
            data.base_matrix_id,
            data.base_matrix_id,
        ]
        for _ in request.vehicles
    ]

    vehicle_order = rng.permutation(
        len(request.vehicles)
    )

    for vehicle_index in vehicle_order:
        vehicle = request.vehicles[
            int(vehicle_index)
        ]

        route = construct_vehicle_route(
            data=data,
            vehicle=vehicle,
            request=request,
            scales=scales,
            pheromone=pheromone,
            neighbour_lists=neighbour_lists,
            unvisited=unvisited,
            config=config,
            rng=rng,
        )

        routes[int(vehicle_index)] = route

    evaluation = evaluate_solution(
        data=data,
        routes=routes,
        request=request,
        scales=scales,
    )

    return AntSolution(
        routes=routes,
        evaluation=evaluation,
    )


def evaluation_key(
    evaluation: SolutionEvaluation,
) -> tuple:
    feasibility_rank = (
        0 if evaluation.is_feasible else 1
    )

    return (
        feasibility_rank,
        *evaluation.solution_key,
    )


def pheromone_cost(
    evaluation: SolutionEvaluation,
) -> float:
    cost = (
        1.0
        + UNCOLLECTED_PENALTY
        * len(
            evaluation.uncollected_containers
        )
        + evaluation.objective_score
    )

    if not evaluation.is_feasible:
        cost += INFEASIBLE_PENALTY

    return float(cost)


def update_pheromones(
    pheromone: np.ndarray,
    ranked_solutions: list[AntSolution],
    global_best: AntSolution,
    config: MMASConfig,
) -> tuple[float, float]:
    evaporation_factor = (
        1.0 - config.evaporation_rate
    )

    pheromone *= evaporation_factor

    elite_count = min(
        config.elite_ants,
        len(ranked_solutions),
    )

    for rank, solution in enumerate(
        ranked_solutions[:elite_count],
        start=1,
    ):
        quality = (
            elite_count - rank + 1
        )

        deposit = (
            quality
            / pheromone_cost(
                solution.evaluation
            )
        )

        for route in solution.routes:
            for origin, destination in zip(
                route[:-1],
                route[1:],
            ):
                pheromone[
                    origin,
                    destination,
                ] += deposit

    global_best_cost = pheromone_cost(
        global_best.evaluation
    )

    global_deposit = (
        elite_count + 1
    ) / global_best_cost

    for route in global_best.routes:
        for origin, destination in zip(
            route[:-1],
            route[1:],
        ):
            pheromone[
                origin,
                destination,
            ] += global_deposit

    tau_max = max(
        1.0 / (
            config.evaporation_rate
            * global_best_cost
        ),
        EPSILON,
    )

    tau_min = max(
        tau_max * config.tau_min_ratio,
        EPSILON,
    )

    np.clip(
        pheromone,
        tau_min,
        tau_max,
        out=pheromone,
    )

    return tau_min, tau_max


def solve_with_mmas(
    data: DataBundle,
    request: OptimizationRequest,
) -> SolverOutput:
    if request.mmas is None:
        raise ValueError(
            "A configuração MMAS não foi fornecida."
        )

    config = request.mmas

    validate_mmas_config(config)

    start_time = time.perf_counter()

    rng = np.random.default_rng(
        config.random_seed
    )

    maximum_vehicle_mass_kg = max(
        vehicle.tare_mass_kg
        + vehicle.capacity_kg
        for vehicle in request.vehicles
    )

    scales = build_objective_scales(
        data=data,
        reference_vehicle_mass_kg=(
            maximum_vehicle_mass_kg
        ),
    )

    neighbour_lists = build_neighbour_lists(
        data=data,
        candidate_list_size=(
            config.candidate_list_size
        ),
    )

    matrix_size = (
        data.distance_matrix_m.shape[0]
    )

    pheromone = np.ones(
        (matrix_size, matrix_size),
        dtype=float,
    )

    global_best: AntSolution | None = None
    iterations_without_improvement = 0

    history: list[dict] = []

    for iteration in range(
        1,
        config.num_iterations + 1,
    ):
        ant_solutions = [
            construct_ant_solution(
                data=data,
                request=request,
                scales=scales,
                pheromone=pheromone,
                neighbour_lists=neighbour_lists,
                config=config,
                rng=rng,
            )
            for _ in range(
                config.num_ants
            )
        ]

        ant_solutions.sort(
            key=lambda solution: evaluation_key(
                solution.evaluation
            )
        )

        iteration_best = ant_solutions[0]

        improved = (
            global_best is None
            or evaluation_key(
                iteration_best.evaluation
            )
            < evaluation_key(
                global_best.evaluation
            )
        )

        if improved:
            global_best = iteration_best
            iterations_without_improvement = 0

        else:
            iterations_without_improvement += 1

        if global_best is None:
            raise RuntimeError(
                "O MMAS não conseguiu construir "
                "nenhuma solução."
            )

        tau_min, tau_max = update_pheromones(
            pheromone=pheromone,
            ranked_solutions=ant_solutions,
            global_best=global_best,
            config=config,
        )

        pheromone_reset = False

        if (
            iterations_without_improvement
            >= config.stagnation_limit
        ):
            pheromone.fill(
                tau_max
            )

            iterations_without_improvement = 0
            pheromone_reset = True

        history.append(
            {
                "iteration": iteration,
                "iteration_best_score": (
                    iteration_best
                    .evaluation
                    .objective_score
                ),
                "global_best_score": (
                    global_best
                    .evaluation
                    .objective_score
                ),
                "collected_containers": len(
                    global_best
                    .evaluation
                    .collected_containers
                ),
                "uncollected_containers": len(
                    global_best
                    .evaluation
                    .uncollected_containers
                ),
                "distance_m": (
                    global_best
                    .evaluation
                    .total_distance_m
                ),
                "operation_time_s": (
                    global_best
                    .evaluation
                    .maximum_route_time_s
                ),
                "total_vehicle_time_s": (
                    global_best
                    .evaluation
                    .total_time_s
                ),
                "fuel_l": (
                    global_best
                    .evaluation
                    .total_fuel_l
                ),
                "tau_min": tau_min,
                "tau_max": tau_max,
                "pheromone_reset": (
                    pheromone_reset
                ),
            }
        )

    if global_best is None:
        raise RuntimeError(
            "O MMAS terminou sem solução."
        )

    runtime_s = (
        time.perf_counter() - start_time
    )

    return SolverOutput(
        routes=[
            route.copy()
            for route in global_best.routes
        ],
        uncollected_nodes=(
            global_best
            .evaluation
            .uncollected_containers
            .copy()
        ),
        solver_cost=(
            global_best
            .evaluation
            .objective_score
        ),
        runtime_s=runtime_s,
        history=history,
    )
from __future__ import annotations

import math
import time
from dataclasses import dataclass

from core.fuel_model import calculate_fuel_liters
from core.models import (
    DataBundle,
    ORToolsConfig,
    OptimizationRequest,
    SolverOutput,
    VehicleSpec,
)
from core.objective import (
    ObjectiveScales,
    build_objective_scales,
    calculate_objective,
)
from core.route_evaluator import evaluate_solution


COST_SCALE = 1_000_000
WEIGHT_SCALE = 1_000
EPSILON = 1e-9


@dataclass(frozen=True)
class RoutingProblem:
    manager: object
    routing: object
    matrix_ids: list[int]


def load_ortools_modules() -> tuple[object, object]:
    try:
        from ortools.constraint_solver import pywrapcp
        from ortools.constraint_solver import routing_enums_pb2

    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "O solver OR-Tools requer a dependência 'ortools'. "
            "Instala com: pip install -r requirements.txt"
        ) from exc

    return pywrapcp, routing_enums_pb2


def validate_ortools_request(
    request: OptimizationRequest,
) -> ORToolsConfig:
    config = request.ortools or ORToolsConfig()
    config.validate()

    if not request.vehicles:
        raise ValueError(
            "O OR-Tools precisa de pelo menos um veículo."
        )

    if request.container_load_kg <= 0:
        raise ValueError(
            "A carga de cada contentor deve ser positiva."
        )

    if request.max_unloads < 0:
        raise ValueError(
            "O número máximo de descargas não pode ser negativo."
        )

    for vehicle in request.vehicles:
        if vehicle.capacity_kg <= 0:
            raise ValueError(
                f"A capacidade do veículo {vehicle.vehicle_id} "
                "deve ser positiva."
            )

        if vehicle.shift_duration_s <= 0:
            raise ValueError(
                f"A duração do turno do veículo {vehicle.vehicle_id} "
                "deve ser positiva."
            )

    return config


def build_solver_node_list(
    data: DataBundle,
) -> list[int]:
    containers = [
        int(matrix_id)
        for matrix_id in data.container_matrix_ids
        if int(matrix_id) != data.base_matrix_id
    ]

    return [
        int(data.base_matrix_id),
        *containers,
    ]


def build_arc_cost_matrix(
    data: DataBundle,
    matrix_ids: list[int],
    scales: ObjectiveScales,
    request: OptimizationRequest,
    reference_vehicle_mass_kg: float,
) -> list[list[int]]:
    matrix: list[list[int]] = []

    for origin in matrix_ids:
        row: list[int] = []

        for destination in matrix_ids:
            if origin == destination:
                row.append(0)
                continue

            distance_m = float(
                data.distance_matrix_m[
                    origin,
                    destination,
                ]
            )

            time_s = float(
                data.time_matrix_s[
                    origin,
                    destination,
                ]
            )

            grade = float(
                data.slope_matrix[
                    origin,
                    destination,
                ]
            )

            fuel_l = calculate_fuel_liters(
                distance_m=distance_m,
                time_s=time_s,
                grade=grade,
                vehicle_mass_kg=reference_vehicle_mass_kg,
            )

            objective = calculate_objective(
                distance_m=distance_m,
                time_s=time_s,
                fuel_l=fuel_l,
                scales=scales,
                objective=request.objective,
            )

            cost = max(
                1,
                int(round(objective.score * COST_SCALE)),
            )

            row.append(cost)

        matrix.append(row)

    return matrix


def weight_to_units(
    weight_kg: float,
) -> int:
    return int(
        math.ceil(weight_kg * WEIGHT_SCALE)
    )


def vehicle_total_capacity_units(
    vehicle: VehicleSpec,
    request: OptimizationRequest,
) -> int:
    return weight_to_units(
        vehicle.capacity_kg * request.max_unloads
    )


def build_routing_problem(
    data: DataBundle,
    request: OptimizationRequest,
    config: ORToolsConfig,
    scales: ObjectiveScales,
    pywrapcp: object,
) -> RoutingProblem:
    matrix_ids = build_solver_node_list(data)

    manager = pywrapcp.RoutingIndexManager(
        len(matrix_ids),
        len(request.vehicles),
        0,
    )

    routing = pywrapcp.RoutingModel(manager)

    reference_vehicle_mass_kg = max(
        vehicle.tare_mass_kg + vehicle.capacity_kg
        for vehicle in request.vehicles
    )

    cost_matrix = build_arc_cost_matrix(
        data=data,
        matrix_ids=matrix_ids,
        scales=scales,
        request=request,
        reference_vehicle_mass_kg=reference_vehicle_mass_kg,
    )

    def cost_callback(
        from_index: int,
        to_index: int,
    ) -> int:
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)

        return cost_matrix[from_node][to_node]

    cost_callback_index = routing.RegisterTransitCallback(
        cost_callback
    )

    routing.SetArcCostEvaluatorOfAllVehicles(
        cost_callback_index
    )

    def demand_callback(
        from_index: int,
    ) -> int:
        node = manager.IndexToNode(from_index)
        matrix_id = matrix_ids[node]

        if matrix_id == data.base_matrix_id:
            return 0

        return weight_to_units(
            request.container_load_kg
        )

    demand_callback_index = (
        routing.RegisterUnaryTransitCallback(
            demand_callback
        )
    )

    vehicle_capacities = [
        vehicle_total_capacity_units(
            vehicle=vehicle,
            request=request,
        )
        for vehicle in request.vehicles
    ]

    routing.AddDimensionWithVehicleCapacity(
        demand_callback_index,
        0,
        vehicle_capacities,
        True,
        "Capacity",
    )

    def time_callback(
        from_index: int,
        to_index: int,
    ) -> int:
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)

        from_matrix_id = matrix_ids[from_node]
        to_matrix_id = matrix_ids[to_node]

        travel_time_s = float(
            data.time_matrix_s[
                from_matrix_id,
                to_matrix_id,
            ]
        )

        service_time_s = (
            request.service_time_s
            if to_matrix_id != data.base_matrix_id
            else 0
        )

        return int(
            math.ceil(
                travel_time_s + service_time_s
            )
        )

    time_callback_index = routing.RegisterTransitCallback(
        time_callback
    )

    routing.AddDimensionWithVehicleCapacity(
        time_callback_index,
        0,
        [
            int(vehicle.shift_duration_s)
            for vehicle in request.vehicles
        ],
        True,
        "Time",
    )

    for node in range(1, len(matrix_ids)):
        routing.AddDisjunction(
            [manager.NodeToIndex(node)],
            int(config.solution_penalty),
        )

    return RoutingProblem(
        manager=manager,
        routing=routing,
        matrix_ids=matrix_ids,
    )


def extract_container_sequences(
    problem: RoutingProblem,
    solution: object,
    data: DataBundle,
) -> list[list[int]]:
    manager = problem.manager
    routing = problem.routing

    sequences: list[list[int]] = []

    for vehicle_index in range(routing.vehicles()):
        sequence: list[int] = []
        index = routing.Start(vehicle_index)

        while not routing.IsEnd(index):
            node = manager.IndexToNode(index)
            matrix_id = problem.matrix_ids[node]

            if matrix_id in data.container_matrix_ids:
                sequence.append(int(matrix_id))

            index = solution.Value(
                routing.NextVar(index)
            )

        sequences.append(sequence)

    return sequences


def insert_landfill_visits(
    container_sequence: list[int],
    data: DataBundle,
    vehicle: VehicleSpec,
    request: OptimizationRequest,
) -> tuple[list[int], list[int]]:
    route = [data.base_matrix_id]

    skipped: list[int] = []
    current_load_kg = 0.0
    unloads = 0

    for container in container_sequence:
        if (
            request.container_load_kg
            > vehicle.capacity_kg + EPSILON
        ):
            skipped.append(container)
            continue

        projected_load_kg = (
            current_load_kg
            + request.container_load_kg
        )

        if projected_load_kg > vehicle.capacity_kg + EPSILON:
            if unloads < request.max_unloads:
                route.append(data.landfill_matrix_id)
                current_load_kg = 0.0
                unloads += 1

            else:
                skipped.append(container)
                continue

        route.append(container)
        current_load_kg += request.container_load_kg

    if current_load_kg > EPSILON:
        if unloads < request.max_unloads:
            route.append(data.landfill_matrix_id)
            current_load_kg = 0.0
            unloads += 1

        else:
            while (
                route
                and route[-1]
                not in {
                    data.base_matrix_id,
                    data.landfill_matrix_id,
                }
            ):
                skipped.append(route.pop())
                current_load_kg -= request.container_load_kg

    route.append(data.base_matrix_id)

    return route, skipped


def build_routes_from_sequences(
    sequences: list[list[int]],
    data: DataBundle,
    request: OptimizationRequest,
) -> tuple[list[list[int]], list[int]]:
    routes: list[list[int]] = []
    skipped: list[int] = []

    for sequence, vehicle in zip(
        sequences,
        request.vehicles,
    ):
        route, skipped_for_vehicle = insert_landfill_visits(
            container_sequence=sequence,
            data=data,
            vehicle=vehicle,
            request=request,
        )

        routes.append(route)
        skipped.extend(skipped_for_vehicle)

    return routes, skipped


def repair_routes_until_feasible(
    sequences: list[list[int]],
    data: DataBundle,
    request: OptimizationRequest,
    scales: ObjectiveScales,
) -> tuple[list[list[int]], list[int]]:
    skipped: list[int] = []

    routes, initially_skipped = build_routes_from_sequences(
        sequences=sequences,
        data=data,
        request=request,
    )

    skipped.extend(initially_skipped)

    while True:
        evaluation = evaluate_solution(
            data=data,
            routes=routes,
            request=request,
            scales=scales,
        )

        if evaluation.is_feasible:
            return routes, skipped

        changed = False

        for route_index, route_evaluation in enumerate(
            evaluation.routes
        ):
            if route_evaluation.is_feasible:
                continue

            if not sequences[route_index]:
                continue

            skipped.append(
                sequences[route_index].pop()
            )

            routes, additional_skipped = (
                build_routes_from_sequences(
                    sequences=sequences,
                    data=data,
                    request=request,
                )
            )

            skipped.extend(additional_skipped)
            changed = True
            break

        if not changed:
            return routes, skipped


def build_empty_routes(
    data: DataBundle,
    request: OptimizationRequest,
) -> list[list[int]]:
    return [
        [
            data.base_matrix_id,
            data.base_matrix_id,
        ]
        for _ in request.vehicles
    ]


def solve_with_ortools(
    data: DataBundle,
    request: OptimizationRequest,
) -> SolverOutput:
    config = validate_ortools_request(request)
    pywrapcp, routing_enums_pb2 = load_ortools_modules()

    start_time = time.perf_counter()

    maximum_vehicle_mass_kg = max(
        vehicle.tare_mass_kg + vehicle.capacity_kg
        for vehicle in request.vehicles
    )

    scales = build_objective_scales(
        data=data,
        reference_vehicle_mass_kg=maximum_vehicle_mass_kg,
    )

    problem = build_routing_problem(
        data=data,
        request=request,
        config=config,
        scales=scales,
        pywrapcp=pywrapcp,
    )

    search_parameters = (
        pywrapcp.DefaultRoutingSearchParameters()
    )

    search_parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy
        .PATH_CHEAPEST_ARC
    )

    search_parameters.local_search_metaheuristic = (
        routing_enums_pb2.LocalSearchMetaheuristic
        .GUIDED_LOCAL_SEARCH
    )

    search_parameters.time_limit.FromSeconds(
        int(config.time_limit_s)
    )

    solution = problem.routing.SolveWithParameters(
        search_parameters
    )

    if solution is None:
        routes = build_empty_routes(
            data=data,
            request=request,
        )

        evaluation = evaluate_solution(
            data=data,
            routes=routes,
            request=request,
            scales=scales,
        )

        runtime_s = time.perf_counter() - start_time

        return SolverOutput(
            routes=routes,
            uncollected_nodes=(
                evaluation.uncollected_containers.copy()
            ),
            solver_cost=float("inf"),
            runtime_s=runtime_s,
            history=[
                {
                    "solver": "or-tools",
                    "status": "no_solution",
                    "collected_containers": 0,
                    "uncollected_containers": len(
                        evaluation.uncollected_containers
                    ),
                }
            ],
        )

    sequences = extract_container_sequences(
        problem=problem,
        solution=solution,
        data=data,
    )

    routes, skipped = repair_routes_until_feasible(
        sequences=sequences,
        data=data,
        request=request,
        scales=scales,
    )

    evaluation = evaluate_solution(
        data=data,
        routes=routes,
        request=request,
        scales=scales,
    )

    runtime_s = time.perf_counter() - start_time

    uncollected_nodes = sorted(
        set(evaluation.uncollected_containers)
        | set(skipped)
    )

    return SolverOutput(
        routes=routes,
        uncollected_nodes=uncollected_nodes,
        solver_cost=evaluation.objective_score,
        runtime_s=runtime_s,
        history=[
            {
                "solver": "or-tools",
                "status": "solution_found",
                "is_feasible": evaluation.is_feasible,
                "collected_containers": len(
                    evaluation.collected_containers
                ),
                "uncollected_containers": len(
                    evaluation.uncollected_containers
                ),
                "skipped_after_postprocessing": len(skipped),
                "distance_m": evaluation.total_distance_m,
                "operation_time_s": (
                    evaluation.maximum_route_time_s
                ),
                "total_vehicle_time_s": (
                    evaluation.total_time_s
                ),
                "fuel_l": evaluation.total_fuel_l,
            }
        ],
    )
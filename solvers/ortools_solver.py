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
from core.route_evaluator import (
    evaluate_solution,
    get_container_waste_kg,
)


COST_SCALE = 1_000_000
WEIGHT_SCALE = 1_000
EPSILON = 1e-9


@dataclass(frozen=True)
class RoutingProblem:
    manager: object
    routing: object
    matrix_ids: list[int]
    trips: list["RoutingTrip"]


@dataclass(frozen=True)
class RoutingTrip:
    physical_vehicle_index: int
    trip_index: int


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
        if int(matrix_id)
        not in {
            data.base_matrix_id,
            data.landfill_matrix_id,
        }
    ]

    return [
        int(data.base_matrix_id),
        int(data.landfill_matrix_id),
        *containers,
    ]


def build_routing_trips(
    request: OptimizationRequest,
) -> list[RoutingTrip]:
    trip_count = max(1, int(request.max_unloads))

    return [
        RoutingTrip(
            physical_vehicle_index=vehicle_index,
            trip_index=trip_index,
        )
        for vehicle_index, _ in enumerate(request.vehicles)
        for trip_index in range(trip_count)
    ]


def container_waste_to_units(
    data: DataBundle,
    matrix_id: int,
    request: OptimizationRequest,
) -> int:
    return weight_to_units(
        get_container_waste_kg(
            data=data,
            matrix_id=matrix_id,
            fallback_kg=request.container_load_kg,
        )
    )


def uncollected_penalty_for_container(
    data: DataBundle,
    matrix_id: int,
    request: OptimizationRequest,
    config: ORToolsConfig,
) -> int:
    waste_kg = get_container_waste_kg(
        data=data,
        matrix_id=matrix_id,
        fallback_kg=request.container_load_kg,
    )

    reference_kg = max(
        float(request.container_load_kg),
        EPSILON,
    )

    return max(
        int(config.solution_penalty),
        int(
            round(
                config.solution_penalty
                * waste_kg
                / reference_kg
            )
        ),
    )


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
    trips = build_routing_trips(request)
    base_node_index = matrix_ids.index(
        int(data.base_matrix_id)
    )
    landfill_node_index = matrix_ids.index(
        int(data.landfill_matrix_id)
    )

    starts = [
        (
            base_node_index
            if trip.trip_index == 0
            else landfill_node_index
        )
        for trip in trips
    ]

    ends = [
        landfill_node_index
        for _ in trips
    ]

    manager = pywrapcp.RoutingIndexManager(
        len(matrix_ids),
        len(trips),
        starts,
        ends,
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

        if matrix_id == data.landfill_matrix_id:
            return 0

        return container_waste_to_units(
            data=data,
            matrix_id=matrix_id,
            request=request,
        )

    demand_callback_index = (
        routing.RegisterUnaryTransitCallback(
            demand_callback
        )
    )

    vehicle_capacities = [
        weight_to_units(
            request.vehicles[
                trip.physical_vehicle_index
            ].capacity_kg
        )
        for trip in trips
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
            if to_matrix_id in data.container_matrix_ids
            else 0
        )

        unload_time_s = (
            request.unload_time_s
            if to_matrix_id == data.landfill_matrix_id
            else 0
        )

        return int(
            math.ceil(
                travel_time_s
                + service_time_s
                + unload_time_s
            )
        )

    time_callback_index = routing.RegisterTransitCallback(
        time_callback
    )

    routing.AddDimensionWithVehicleCapacity(
        time_callback_index,
        0,
        [
            int(
                request.vehicles[
                    trip.physical_vehicle_index
                ].shift_duration_s
            )
            for trip in trips
        ],
        True,
        "Time",
    )

    for node in range(1, len(matrix_ids)):
        matrix_id = matrix_ids[node]
        if matrix_id == data.landfill_matrix_id:
            continue

        routing.AddDisjunction(
            [manager.NodeToIndex(node)],
            uncollected_penalty_for_container(
                data=data,
                matrix_id=matrix_id,
                request=request,
                config=config,
            ),
        )

    for vehicle_index, trip in enumerate(trips):
        routing.SetFixedCostOfVehicle(
            int(
                trip.trip_index
                * max(
                    1,
                    config.solution_penalty // 2,
                )
            ),
            vehicle_index,
        )

    return RoutingProblem(
        manager=manager,
        routing=routing,
        matrix_ids=matrix_ids,
        trips=trips,
    )


def extract_trip_sequences(
    problem: RoutingProblem,
    solution: object,
    data: DataBundle,
) -> list[list[int]]:
    manager = problem.manager
    routing = problem.routing

    sequences: list[list[int]] = []

    for trip_index in range(routing.vehicles()):
        sequence: list[int] = []
        index = routing.Start(trip_index)

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


def build_routes_from_trip_sequences(
    trip_sequences: list[list[int]],
    data: DataBundle,
    request: OptimizationRequest,
) -> list[list[int]]:
    trips = build_routing_trips(request)

    routes = [
        [data.base_matrix_id]
        for _ in request.vehicles
    ]

    for trip, sequence in zip(trips, trip_sequences):
        if not sequence:
            continue

        route = routes[trip.physical_vehicle_index]

        expected_start = (
            data.base_matrix_id
            if trip.trip_index == 0
            else data.landfill_matrix_id
        )

        if route[-1] != expected_start:
            route.append(expected_start)

        route.extend(sequence)
        route.append(data.landfill_matrix_id)

    for route in routes:
        if route[-1] != data.base_matrix_id:
            route.append(data.base_matrix_id)
        else:
            route.append(data.base_matrix_id)

    return routes


def repair_routes_until_feasible(
    trip_sequences: list[list[int]],
    data: DataBundle,
    request: OptimizationRequest,
    scales: ObjectiveScales,
) -> tuple[list[list[int]], list[int]]:
    skipped: list[int] = []

    routes = build_routes_from_trip_sequences(
        trip_sequences=trip_sequences,
        data=data,
        request=request,
    )

    trips = build_routing_trips(request)

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

            candidate_trip_indexes = [
                trip_index
                for trip_index, trip in enumerate(trips)
                if (
                    trip.physical_vehicle_index
                    == route_index
                    and trip_sequences[trip_index]
                )
            ]

            if not candidate_trip_indexes:
                continue

            trip_index = candidate_trip_indexes[-1]

            skipped.append(
                trip_sequences[trip_index].pop()
            )

            routes = (
                build_routes_from_trip_sequences(
                    trip_sequences=trip_sequences,
                    data=data,
                    request=request,
                )
            )

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

    trip_sequences = extract_trip_sequences(
        problem=problem,
        solution=solution,
        data=data,
    )

    routes, skipped = repair_routes_until_feasible(
        trip_sequences=trip_sequences,
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

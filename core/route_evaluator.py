from __future__ import annotations

from collections import Counter
import math

from core.fuel_model import calculate_segment_metrics
from core.models import (
    DataBundle,
    OptimizationRequest,
    RouteEvaluation,
    SegmentEvaluation,
    SolutionEvaluation,
    VehicleSpec,
)
from core.objective import (
    ObjectiveScales,
    build_solution_key,
    calculate_objective,
)


def get_container_waste_kg(
    data: DataBundle,
    matrix_id: int,
    fallback_kg: float,
) -> float:
    if "waste_kg" not in data.points.columns:
        return float(fallback_kg)

    matches = data.points.loc[
        data.points["matrix_id"].astype(int) == int(matrix_id),
        "waste_kg",
    ]

    if matches.empty:
        return float(fallback_kg)

    try:
        waste_kg = float(matches.iloc[0])
    except (TypeError, ValueError):
        return float(fallback_kg)

    if not math.isfinite(waste_kg) or waste_kg <= 0:
        return float(fallback_kg)

    return waste_kg


def sum_container_waste_kg(
    data: DataBundle,
    container_ids: list[int],
    fallback_kg: float,
) -> float:
    return sum(
        get_container_waste_kg(
            data=data,
            matrix_id=container_id,
            fallback_kg=fallback_kg,
        )
        for container_id in container_ids
    )


def validate_request(
    request: OptimizationRequest,
) -> None:
    if not request.vehicles:
        raise ValueError(
            "A otimização deve possuir pelo menos um veículo."
        )

    vehicle_ids = [
        vehicle.vehicle_id
        for vehicle in request.vehicles
    ]

    if len(vehicle_ids) != len(set(vehicle_ids)):
        raise ValueError(
            "Existem veículos com identificadores repetidos."
        )

    if request.container_load_kg <= 0:
        raise ValueError(
            "A carga de cada contentor deve ser positiva."
        )

    if request.service_time_s < 0:
        raise ValueError(
            "O tempo de serviço não pode ser negativo."
        )

    if request.unload_time_s < 0:
        raise ValueError(
            "O tempo de descarga não pode ser negativo."
        )

    if request.max_unloads < 0:
        raise ValueError(
            "O número máximo de descargas não pode ser negativo."
        )

    request.objective.validate()

    for vehicle in request.vehicles:
        if vehicle.tare_mass_kg <= 0:
            raise ValueError(
                f"A tara do veículo {vehicle.vehicle_id} "
                "deve ser positiva."
            )

        if vehicle.capacity_kg <= 0:
            raise ValueError(
                f"A capacidade do veículo {vehicle.vehicle_id} "
                "deve ser positiva."
            )

        if vehicle.shift_duration_s <= 0:
            raise ValueError(
                f"A duração do turno do veículo "
                f"{vehicle.vehicle_id} deve ser positiva."
            )


def validate_route_node_ids(
    route: list[int],
    matrix_size: int,
) -> list[int]:
    invalid_nodes = [
        int(node)
        for node in route
        if not 0 <= int(node) < matrix_size
    ]

    return invalid_nodes


def identify_event_type(
    matrix_id: int,
    data: DataBundle,
) -> str:
    if matrix_id == data.base_matrix_id:
        return "base"

    if matrix_id == data.landfill_matrix_id:
        return "landfill"

    if matrix_id in data.container_matrix_ids:
        return "container"

    return "unknown"


def evaluate_route(
    data: DataBundle,
    route: list[int],
    vehicle: VehicleSpec,
    request: OptimizationRequest,
    scales: ObjectiveScales,
) -> RouteEvaluation:
    route = [
        int(matrix_id)
        for matrix_id in route
    ]

    violations: list[str] = []
    segments: list[SegmentEvaluation] = []

    collected_containers: list[int] = []
    collected_set: set[int] = set()

    matrix_size = data.distance_matrix_m.shape[0]

    if len(route) < 2:
        violations.append(
            "A rota deve conter pelo menos uma origem "
            "e um destino."
        )

        return RouteEvaluation(
            vehicle_id=vehicle.vehicle_id,
            vehicle_name=vehicle.name,
            route=route,
            segments=[],
            collected_containers=[],
            total_distance_m=0.0,
            total_travel_time_s=0.0,
            total_service_time_s=0.0,
            total_unload_time_s=0.0,
            total_time_s=0.0,
            total_fuel_l=0.0,
            number_of_unloads=0,
            final_load_kg=0.0,
            objective_score=float("inf"),
            is_feasible=False,
            violations=violations,
        )

    invalid_nodes = validate_route_node_ids(
        route=route,
        matrix_size=matrix_size,
    )

    if invalid_nodes:
        raise ValueError(
            "A rota contém matrix_id inválidos: "
            f"{invalid_nodes[:20]}"
        )

    if route[0] != data.base_matrix_id:
        violations.append(
            "A rota não começa na base."
        )

    if route[-1] != data.base_matrix_id:
        violations.append(
            "A rota não termina na base."
        )

    current_load_kg = 0.0

    total_distance_m = 0.0
    total_travel_time_s = 0.0
    total_service_time_s = 0.0
    total_unload_time_s = 0.0
    total_fuel_l = 0.0

    number_of_unloads = 0

    for sequence, (
        from_matrix_id,
        to_matrix_id,
    ) in enumerate(
        zip(
            route[:-1],
            route[1:],
        ),
        start=1,
    ):
        load_before_kg = current_load_kg

        metrics = calculate_segment_metrics(
            data=data,
            from_matrix_id=from_matrix_id,
            to_matrix_id=to_matrix_id,
            tare_mass_kg=vehicle.tare_mass_kg,
            current_load_kg=load_before_kg,
        )

        event_type = identify_event_type(
            matrix_id=to_matrix_id,
            data=data,
        )

        service_time_s = 0.0
        unload_time_s = 0.0
        load_after_kg = load_before_kg

        if event_type == "container":
            if to_matrix_id in collected_set:
                violations.append(
                    f"O contentor {to_matrix_id} foi visitado "
                    "mais do que uma vez pelo mesmo veículo."
                )

            else:
                container_waste_kg = get_container_waste_kg(
                    data=data,
                    matrix_id=to_matrix_id,
                    fallback_kg=request.container_load_kg,
                )

                service_time_s = float(
                    request.service_time_s
                )

                load_after_kg = (
                    load_before_kg
                    + container_waste_kg
                )

                collected_set.add(
                    to_matrix_id
                )

                collected_containers.append(
                    to_matrix_id
                )

                if (
                    load_after_kg
                    > vehicle.capacity_kg + 1e-9
                ):
                    violations.append(
                        f"A capacidade do veículo foi excedida "
                        f"ao recolher o contentor {to_matrix_id}: "
                        f"{load_after_kg:.2f} kg para uma capacidade "
                        f"de {vehicle.capacity_kg:.2f} kg."
                    )

        elif event_type == "landfill":
            if load_before_kg > 0:
                unload_time_s = float(
                    request.unload_time_s
                )

                number_of_unloads += 1
                load_after_kg = 0.0

        elif event_type == "base":
            is_last_segment = (
                sequence == len(route) - 1
            )

            if not is_last_segment:
                violations.append(
                    "A rota regressa à base antes de terminar."
                )

        else:
            violations.append(
                f"O nó {to_matrix_id} não possui um tipo válido."
            )

        total_segment_time_s = (
            metrics["time_s"]
            + service_time_s
            + unload_time_s
        )

        segments.append(
            SegmentEvaluation(
                vehicle_id=vehicle.vehicle_id,
                sequence=sequence,
                from_matrix_id=from_matrix_id,
                to_matrix_id=to_matrix_id,
                event_type=event_type,
                distance_m=metrics["distance_m"],
                travel_time_s=metrics["time_s"],
                service_time_s=service_time_s,
                unload_time_s=unload_time_s,
                total_segment_time_s=(
                    total_segment_time_s
                ),
                speed_kmh=metrics["speed_kmh"],
                grade=metrics["grade"],
                load_before_kg=load_before_kg,
                load_after_kg=load_after_kg,
                vehicle_mass_kg=(
                    metrics["vehicle_mass_kg"]
                ),
                fuel_l=metrics["fuel_l"],
            )
        )

        total_distance_m += metrics["distance_m"]
        total_travel_time_s += metrics["time_s"]
        total_service_time_s += service_time_s
        total_unload_time_s += unload_time_s
        total_fuel_l += metrics["fuel_l"]

        current_load_kg = load_after_kg

    total_time_s = (
        total_travel_time_s
        + total_service_time_s
        + total_unload_time_s
    )

    if number_of_unloads > request.max_unloads:
        violations.append(
            "O número máximo de descargas foi excedido: "
            f"{number_of_unloads} descargas para um máximo "
            f"de {request.max_unloads}."
        )

    if total_time_s > vehicle.shift_duration_s + 1e-9:
        violations.append(
            "A duração máxima do turno foi excedida: "
            f"{total_time_s / 3600:.2f} horas para um turno "
            f"de {vehicle.shift_duration_s / 3600:.2f} horas."
        )

    if (
        route[-1] == data.base_matrix_id
        and current_load_kg > 1e-9
    ):
        violations.append(
            "O veículo regressou à base com "
            f"{current_load_kg:.2f} kg de resíduos. "
            "Deveria descarregar primeiro no aterro."
        )

    objective_breakdown = calculate_objective(
        distance_m=total_distance_m,
        time_s=total_time_s,
        fuel_l=total_fuel_l,
        scales=scales,
        objective=request.objective,
    )

    return RouteEvaluation(
        vehicle_id=vehicle.vehicle_id,
        vehicle_name=vehicle.name,
        route=route,
        segments=segments,
        collected_containers=collected_containers,
        total_distance_m=total_distance_m,
        total_travel_time_s=total_travel_time_s,
        total_service_time_s=total_service_time_s,
        total_unload_time_s=total_unload_time_s,
        total_time_s=total_time_s,
        total_fuel_l=total_fuel_l,
        number_of_unloads=number_of_unloads,
        final_load_kg=current_load_kg,
        objective_score=objective_breakdown.score,
        is_feasible=len(violations) == 0,
        violations=violations,
    )


def evaluate_solution(
    data: DataBundle,
    routes: list[list[int]],
    request: OptimizationRequest,
    scales: ObjectiveScales,
) -> SolutionEvaluation:
    validate_request(request)

    if len(routes) != len(request.vehicles):
        raise ValueError(
            "O número de rotas deve ser igual "
            "ao número de veículos: "
            f"{len(routes)} rotas para "
            f"{len(request.vehicles)} veículos."
        )

    route_evaluations = [
        evaluate_route(
            data=data,
            route=route,
            vehicle=vehicle,
            request=request,
            scales=scales,
        )
        for route, vehicle in zip(
            routes,
            request.vehicles,
        )
    ]

    all_collected_containers = [
        container
        for route_evaluation in route_evaluations
        for container in (
            route_evaluation.collected_containers
        )
    ]

    container_counter = Counter(
        all_collected_containers
    )

    duplicated_containers = sorted(
        container
        for container, count
        in container_counter.items()
        if count > 1
    )

    collected_containers = sorted(
        container_counter.keys()
    )

    all_container_ids = set(
        data.container_matrix_ids
    )

    collected_container_ids = set(
        collected_containers
    )

    uncollected_containers = sorted(
        all_container_ids
        - collected_container_ids
    )

    total_distance_m = sum(
        route.total_distance_m
        for route in route_evaluations
    )

    total_travel_time_s = sum(
        route.total_travel_time_s
        for route in route_evaluations
    )

    total_service_time_s = sum(
        route.total_service_time_s
        for route in route_evaluations
    )

    total_unload_time_s = sum(
        route.total_unload_time_s
        for route in route_evaluations
    )

    total_time_s = sum(
        route.total_time_s
        for route in route_evaluations
    )

    maximum_route_time_s = max(
        (
            route.total_time_s
            for route in route_evaluations
        ),
        default=0.0,
    )

    total_fuel_l = sum(
        route.total_fuel_l
        for route in route_evaluations
    )

    total_collected_waste_kg = (
        sum_container_waste_kg(
            data=data,
            container_ids=collected_containers,
            fallback_kg=request.container_load_kg,
        )
    )

    total_uncollected_waste_kg = (
        sum_container_waste_kg(
            data=data,
            container_ids=uncollected_containers,
            fallback_kg=request.container_load_kg,
        )
    )

    objective_breakdown = calculate_objective(
        distance_m=total_distance_m,
        time_s=maximum_route_time_s,
        fuel_l=total_fuel_l,
        scales=scales,
        objective=request.objective,
    )

    solution_key = build_solution_key(
        total_containers=len(
            data.container_matrix_ids
        ),
        collected_containers=len(
            collected_containers
        ),
        uncollected_waste_kg=(
            total_uncollected_waste_kg
        ),
        objective_score=(
            objective_breakdown.score
        ),
        fuel_l=total_fuel_l,
        time_s=maximum_route_time_s,
        distance_m=total_distance_m,
    )

    violations: list[str] = []

    for route_evaluation in route_evaluations:
        for violation in route_evaluation.violations:
            violations.append(
                f"Veículo "
                f"{route_evaluation.vehicle_id}: "
                f"{violation}"
            )

    if duplicated_containers:
        violations.append(
            "Existem contentores recolhidos "
            "por mais do que um veículo: "
            f"{duplicated_containers[:20]}"
        )

    return SolutionEvaluation(
        routes=route_evaluations,
        collected_containers=collected_containers,
        uncollected_containers=uncollected_containers,
        duplicated_containers=duplicated_containers,
        total_distance_m=total_distance_m,
        total_travel_time_s=total_travel_time_s,
        total_service_time_s=total_service_time_s,
        total_unload_time_s=total_unload_time_s,
        total_time_s=total_time_s,
        maximum_route_time_s=maximum_route_time_s,
        total_fuel_l=total_fuel_l,
        total_collected_waste_kg=(
            total_collected_waste_kg
        ),
        total_uncollected_waste_kg=(
            total_uncollected_waste_kg
        ),
        objective_score=objective_breakdown.score,
        solution_key=solution_key,
        is_feasible=len(violations) == 0,
        violations=violations,
    )

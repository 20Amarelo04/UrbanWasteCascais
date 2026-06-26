from __future__ import annotations

from dataclasses import replace
from time import perf_counter

from config import CONTAINERS, OPERATION
from core.data_loader import load_data_bundle
from core.models import (
    MMASConfig,
    ObjectiveConfig,
    OptimizationRequest,
    VehicleSpec,
)
from core.objective import build_objective_scales
from core.route_evaluator import evaluate_solution
from solvers.mmas_solver import solve_with_mmas


def build_vehicles(
    number_of_vehicles: int,
) -> list[VehicleSpec]:
    return [
        VehicleSpec(
            vehicle_id=index + 1,
            name=f"Camião {index + 1}",
            tare_mass_kg=6000.0,
            capacity_kg=9000.0,
            shift_duration_s=(
                OPERATION.shift_duration_s
            ),
        )
        for index in range(number_of_vehicles)
    ]


def build_test_configuration(
    number_of_containers: int,
) -> tuple[int, int, int, int]:
    if number_of_containers <= 100:
        return 2, 10, 30, 15

    if number_of_containers <= 300:
        return 3, 10, 25, 20

    return 4, 8, 20, 25


def run_benchmark(
    complete_data,
    number_of_containers: int,
) -> dict:
    (
        number_of_vehicles,
        number_of_ants,
        number_of_iterations,
        candidate_list_size,
    ) = build_test_configuration(
        number_of_containers
    )

    test_data = replace(
        complete_data,
        container_matrix_ids=(
            complete_data.container_matrix_ids[
                :number_of_containers
            ]
        ),
    )

    vehicles = build_vehicles(
        number_of_vehicles
    )

    request = OptimizationRequest(
        algorithm="mmas",
        vehicles=vehicles,
        container_load_kg=CONTAINERS.load_kg,
        service_time_s=CONTAINERS.service_time_s,
        unload_time_s=OPERATION.unload_time_s,
        max_unloads=(
            OPERATION.max_unloads_per_vehicle
        ),
        objective=ObjectiveConfig(
            distance_weight=0.30,
            time_weight=0.30,
            fuel_weight=0.40,
        ),
        mmas=MMASConfig(
            num_ants=number_of_ants,
            num_iterations=number_of_iterations,
            candidate_list_size=(
                candidate_list_size
            ),
            elite_ants=min(
                3,
                number_of_ants,
            ),
            stagnation_limit=10,
            random_seed=42,
        ),
    )

    maximum_vehicle_mass_kg = max(
        vehicle.tare_mass_kg
        + vehicle.capacity_kg
        for vehicle in vehicles
    )

    scales = build_objective_scales(
        data=test_data,
        reference_vehicle_mass_kg=(
            maximum_vehicle_mass_kg
        ),
    )

    start_time = perf_counter()

    solver_output = solve_with_mmas(
        data=test_data,
        request=request,
    )

    evaluation = evaluate_solution(
        data=test_data,
        routes=solver_output.routes,
        request=request,
        scales=scales,
    )

    total_runtime_s = (
        perf_counter() - start_time
    )

    used_vehicles = sum(
        1
        for route in evaluation.routes
        if route.collected_containers
    )

    return {
        "number_of_containers": (
            number_of_containers
        ),
        "number_of_vehicles": (
            number_of_vehicles
        ),
        "used_vehicles": used_vehicles,
        "number_of_ants": number_of_ants,
        "number_of_iterations": (
            number_of_iterations
        ),
        "collected": len(
            evaluation.collected_containers
        ),
        "uncollected": len(
            evaluation.uncollected_containers
        ),
        "distance_km": (
            evaluation.total_distance_m
            / 1000
        ),
        "operation_time_min": (
            evaluation.maximum_route_time_s
            / 60
        ),
        "total_vehicle_time_min": (
            evaluation.total_time_s
            / 60
        ),
        "fuel_l": (
            evaluation.total_fuel_l
        ),
        "score": (
            evaluation.objective_score
        ),
        "runtime_s": total_runtime_s,
        "feasible": (
            evaluation.is_feasible
        ),
        "violations": (
            evaluation.violations
        ),
        "routes": (
            solver_output.routes
        ),
    }


def print_result(
    result: dict,
) -> None:
    print("\n" + "=" * 75)

    print(
        f"TESTE COM "
        f"{result['number_of_containers']} "
        "CONTENTORES"
    )

    print("=" * 75)

    print(
        f"Veículos disponíveis: "
        f"{result['number_of_vehicles']}"
    )

    print(
        f"Veículos utilizados: "
        f"{result['used_vehicles']}"
    )

    print(
        f"Formigas: "
        f"{result['number_of_ants']}"
    )

    print(
        f"Iterações: "
        f"{result['number_of_iterations']}"
    )

    print(
        f"Contentores recolhidos: "
        f"{result['collected']}"
    )

    print(
        f"Contentores não recolhidos: "
        f"{result['uncollected']}"
    )

    print(
        f"Distância total: "
        f"{result['distance_km']:.2f} km"
    )

    print(
        f"Duração da operação: "
        f"{result['operation_time_min']:.2f} min"
    )

    print(
        f"Soma dos tempos: "
        f"{result['total_vehicle_time_min']:.2f} min"
    )

    print(
        f"Combustível total: "
        f"{result['fuel_l']:.4f} L"
    )

    print(
        f"Score: "
        f"{result['score']:.4f}"
    )

    print(
        f"Tempo de execução: "
        f"{result['runtime_s']:.2f} s"
    )

    print(
        f"Solução viável: "
        f"{result['feasible']}"
    )

    if result["violations"]:
        print("Violações:")

        for violation in result["violations"]:
            print(
                f"  - {violation}"
            )

        for vehicle_index, route in enumerate(
            result["routes"],
            start=1,
        ):
            container_count = sum(
                1
                for node in route
                if node not in {
                    complete_data.base_matrix_id,
                    complete_data.landfill_matrix_id,
                }
            )

            landfill_visits = route.count(
                complete_data.landfill_matrix_id
            )

            print(
                f"Rota {vehicle_index}: "
                f"{container_count} contentores | "
                f"{landfill_visits} descargas"
            )


def main() -> None:
    complete_data = load_data_bundle()

    test_sizes = [
        100,
        300,
        877,
    ]

    results: list[dict] = []

    for test_size in test_sizes:
        result = run_benchmark(
            complete_data=complete_data,
            number_of_containers=test_size,
        )

        results.append(result)

        print_result(result)

    print("\n" + "=" * 75)
    print("RESUMO DOS TESTES")
    print("=" * 75)

    print(
        f"{'Pontos':>8} | "
        f"{'Recolhidos':>10} | "
        f"{'Não recolhidos':>14} | "
        f"{'Veículos':>9} | "
        f"{'Tempo algoritmo':>15}"
    )

    print("-" * 75)

    for result in results:
        print(
            f"{result['number_of_containers']:>8} | "
            f"{result['collected']:>10} | "
            f"{result['uncollected']:>14} | "
            f"{result['used_vehicles']:>9} | "
            f"{result['runtime_s']:>13.2f} s"
        )


if __name__ == "__main__":
    main()
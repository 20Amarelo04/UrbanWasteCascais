from __future__ import annotations

from dataclasses import replace

from config import CONTAINERS, OPERATION
from core.data_loader import load_data_bundle
from core.models import (
    ORToolsConfig,
    ObjectiveConfig,
    OptimizationRequest,
    VehicleSpec,
)
from core.objective import build_objective_scales
from core.route_evaluator import evaluate_solution
from solvers.ortools_solver import solve_with_ortools


def main() -> None:
    complete_data = load_data_bundle()

    test_data = replace(
        complete_data,
        container_matrix_ids=(
            complete_data.container_matrix_ids[:12]
        ),
    )

    vehicle = VehicleSpec(
        vehicle_id=1,
        name="Camião 1",
        tare_mass_kg=6000.0,
        capacity_kg=750.0,
        shift_duration_s=OPERATION.shift_duration_s,
    )

    request = OptimizationRequest(
        algorithm="or-tools",
        vehicles=[vehicle],
        container_load_kg=CONTAINERS.load_kg,
        service_time_s=CONTAINERS.service_time_s,
        unload_time_s=OPERATION.unload_time_s,
        max_unloads=5,
        objective=ObjectiveConfig(
            distance_weight=0.30,
            time_weight=0.30,
            fuel_weight=0.40,
        ),
        ortools=ORToolsConfig(
            time_limit_s=10,
            solution_penalty=1_000_000,
        ),
    )

    result = solve_with_ortools(
        data=test_data,
        request=request,
    )

    maximum_vehicle_mass_kg = (
        vehicle.tare_mass_kg + vehicle.capacity_kg
    )

    scales = build_objective_scales(
        data=test_data,
        reference_vehicle_mass_kg=maximum_vehicle_mass_kg,
    )

    evaluation = evaluate_solution(
        data=test_data,
        routes=result.routes,
        request=request,
        scales=scales,
    )

    print("=" * 75)
    print("TESTE DO SOLVER OR-TOOLS")
    print("=" * 75)

    print(f"Rotas: {result.routes}")
    print(f"Contentores recolhidos: {len(evaluation.collected_containers)}")
    print(f"Contentores não recolhidos: {len(evaluation.uncollected_containers)}")
    print(f"Contentores duplicados: {len(evaluation.duplicated_containers)}")
    print(f"Descargas: {evaluation.routes[0].number_of_unloads}")
    print(f"Distância total: {evaluation.total_distance_m / 1000:.2f} km")
    print(f"Tempo total: {evaluation.total_time_s / 60:.2f} min")
    print(f"Combustível total: {evaluation.total_fuel_l:.4f} L")
    print(f"Score: {evaluation.objective_score:.4f}")
    print(f"Tempo de execução: {result.runtime_s:.2f} s")
    print(f"Solução viável: {evaluation.is_feasible}")

    if evaluation.violations:
        print("\nViolações:")
        for violation in evaluation.violations:
            print(f"  - {violation}")

    if not evaluation.is_feasible:
        raise AssertionError(
            "O OR-Tools devolveu uma solução inválida."
        )

    if evaluation.duplicated_containers:
        raise AssertionError(
            "Existem contentores duplicados."
        )

    print("\nOR-Tools validado com sucesso no conjunto reduzido.")


if __name__ == "__main__":
    main()
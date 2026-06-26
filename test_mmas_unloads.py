from __future__ import annotations

from dataclasses import replace

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


def main() -> None:
    complete_data = load_data_bundle()

    test_data = replace(
        complete_data,
        container_matrix_ids=(
            complete_data.container_matrix_ids[:20]
        ),
    )

    vehicle = VehicleSpec(
        vehicle_id=1,
        name="Camião 1",
        tare_mass_kg=6000.0,

        # Apenas 5 contentores por carga.
        capacity_kg=750.0,

        shift_duration_s=(
            OPERATION.shift_duration_s
        ),
    )

    request = OptimizationRequest(
        algorithm="mmas",
        vehicles=[vehicle],
        container_load_kg=CONTAINERS.load_kg,
        service_time_s=CONTAINERS.service_time_s,
        unload_time_s=OPERATION.unload_time_s,
        max_unloads=10,
        objective=ObjectiveConfig(
            distance_weight=0.30,
            time_weight=0.30,
            fuel_weight=0.40,
        ),
        mmas=MMASConfig(
            num_ants=10,
            num_iterations=30,
            candidate_list_size=10,
            elite_ants=3,
            stagnation_limit=12,
            random_seed=42,
        ),
    )

    result = solve_with_mmas(
        data=test_data,
        request=request,
    )

    scales = build_objective_scales(
        data=test_data,
        reference_vehicle_mass_kg=6750.0,
    )

    evaluation = evaluate_solution(
        data=test_data,
        routes=result.routes,
        request=request,
        scales=scales,
    )

    route_evaluation = evaluation.routes[0]

    print("=" * 75)
    print("TESTE DO MMAS COM VÁRIAS DESCARGAS")
    print("=" * 75)

    print(f"Rota: {result.routes[0]}")
    print(
        f"Contentores recolhidos: "
        f"{len(evaluation.collected_containers)}"
    )
    print(
        f"Contentores não recolhidos: "
        f"{len(evaluation.uncollected_containers)}"
    )
    print(
        f"Descargas realizadas: "
        f"{route_evaluation.number_of_unloads}"
    )
    print(
        f"Carga final: "
        f"{route_evaluation.final_load_kg:.0f} kg"
    )
    print(
        f"Distância: "
        f"{evaluation.total_distance_m / 1000:.2f} km"
    )
    print(
        f"Tempo: "
        f"{evaluation.total_time_s / 60:.2f} min"
    )
    print(
        f"Combustível: "
        f"{evaluation.total_fuel_l:.4f} L"
    )
    print(
        f"Viável: {evaluation.is_feasible}"
    )

    if evaluation.violations:
        print("Violações:")

        for violation in evaluation.violations:
            print(f"  - {violation}")

    if not evaluation.is_feasible:
        raise AssertionError(
            "O MMAS devolveu uma solução inválida."
        )

    if len(evaluation.collected_containers) != 20:
        raise AssertionError(
            "O MMAS deveria recolher os 20 contentores."
        )

    if route_evaluation.number_of_unloads != 4:
        raise AssertionError(
            "Com capacidade para 5 contentores, "
            "deveriam existir 4 descargas."
        )

    if route_evaluation.final_load_kg != 0.0:
        raise AssertionError(
            "O veículo deveria regressar sem carga."
        )

    landfill_visits = result.routes[0].count(
        test_data.landfill_matrix_id
    )

    if landfill_visits != 4:
        raise AssertionError(
            "A rota deveria visitar o aterro 4 vezes."
        )

    print(
        "\nMMAS validado com várias descargas."
    )


if __name__ == "__main__":
    main()
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
            complete_data.container_matrix_ids[
                :40
            ]
        ),
    )

    vehicles = [
        VehicleSpec(
            vehicle_id=1,
            name="Camião 1",
            tare_mass_kg=6000.0,
            capacity_kg=3000.0,
            shift_duration_s=(
                OPERATION.shift_duration_s
            ),
        ),
        VehicleSpec(
            vehicle_id=2,
            name="Camião 2",
            tare_mass_kg=6500.0,
            capacity_kg=3000.0,
            shift_duration_s=(
                OPERATION.shift_duration_s
            ),
        ),
    ]

    request = OptimizationRequest(
        algorithm="mmas",
        vehicles=vehicles,
        container_load_kg=(
            CONTAINERS.load_kg
        ),
        service_time_s=(
            CONTAINERS.service_time_s
        ),
        unload_time_s=(
            OPERATION.unload_time_s
        ),

        # Cada veículo só pode descarregar uma vez.
        max_unloads=1,

        objective=ObjectiveConfig(
            distance_weight=0.30,
            time_weight=0.30,
            fuel_weight=0.40,
        ),
        mmas=MMASConfig(
            num_ants=15,
            num_iterations=50,
            candidate_list_size=15,
            elite_ants=4,
            stagnation_limit=20,
            random_seed=42,
        ),
    )

    result = solve_with_mmas(
        data=test_data,
        request=request,
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

    evaluation = evaluate_solution(
        data=test_data,
        routes=result.routes,
        request=request,
        scales=scales,
    )

    print("=" * 75)
    print("TESTE DO MMAS COM VÁRIOS VEÍCULOS")
    print("=" * 75)

    for route_evaluation in evaluation.routes:
        print(
            f"\n{route_evaluation.vehicle_name}:"
        )

        print(
            f"  Rota: "
            f"{route_evaluation.route}"
        )

        print(
            f"  Contentores: "
            f"{len(route_evaluation.collected_containers)}"
        )

        print(
            f"  Resíduos: "
            f"{len(route_evaluation.collected_containers) * CONTAINERS.load_kg:.0f} kg"
        )

        print(
            f"  Distância: "
            f"{route_evaluation.total_distance_m / 1000:.2f} km"
        )

        print(
            f"  Tempo: "
            f"{route_evaluation.total_time_s / 60:.2f} min"
        )

        print(
            f"  Combustível: "
            f"{route_evaluation.total_fuel_l:.4f} L"
        )

        print(
            f"  Descargas: "
            f"{route_evaluation.number_of_unloads}"
        )

        print(
            f"  Carga final: "
            f"{route_evaluation.final_load_kg:.0f} kg"
        )

        print(
            f"  Viável: "
            f"{route_evaluation.is_feasible}"
        )

    print("\nTotais:")

    print(
        f"  Contentores recolhidos: "
        f"{len(evaluation.collected_containers)}"
    )

    print(
        f"  Contentores não recolhidos: "
        f"{len(evaluation.uncollected_containers)}"
    )

    print(
        f"  Contentores duplicados: "
        f"{len(evaluation.duplicated_containers)}"
    )

    print(
        f"  Resíduos recolhidos: "
        f"{evaluation.total_collected_waste_kg:.0f} kg"
    )

    print(
        f"  Distância total: "
        f"{evaluation.total_distance_m / 1000:.2f} km"
    )

    print(
        f"  Duração da operação: "
        f"{evaluation.maximum_route_time_s / 60:.2f} min"
    )

    print(
        f"  Soma dos tempos dos veículos: "
        f"{evaluation.total_time_s / 60:.2f} min"
    )

    print(
        f"  Combustível total: "
        f"{evaluation.total_fuel_l:.4f} L"
    )

    print(
        f"  Score: "
        f"{evaluation.objective_score:.4f}"
    )

    print(
        f"  Tempo de execução: "
        f"{result.runtime_s:.2f} s"
    )

    print(
        f"  Solução viável: "
        f"{evaluation.is_feasible}"
    )

    if evaluation.violations:
        print("\nViolações:")

        for violation in evaluation.violations:
            print(
                f"  - {violation}"
            )

    if not evaluation.is_feasible:
        raise AssertionError(
            "O MMAS devolveu uma solução inválida: "
            f"{evaluation.violations}"
        )

    if len(result.routes) != 2:
        raise AssertionError(
            "O MMAS deveria devolver duas rotas."
        )

    if evaluation.duplicated_containers:
        raise AssertionError(
            "Existem contentores atribuídos "
            "a mais do que um veículo."
        )

    if len(
        evaluation.collected_containers
    ) != 40:
        raise AssertionError(
            "Os 40 contentores deveriam ser recolhidos."
        )

    containers_per_vehicle = [
        len(
            route_evaluation.collected_containers
        )
        for route_evaluation in evaluation.routes
    ]

    if any(
        count == 0
        for count in containers_per_vehicle
    ):
        raise AssertionError(
            "Os dois veículos deveriam ser utilizados."
        )

    if sum(containers_per_vehicle) != 40:
        raise AssertionError(
            "Os veículos deveriam recolher "
            "um total de 40 contentores."
        )

    for route_evaluation in evaluation.routes:
        if len(
            route_evaluation.collected_containers
        ) != 20:
            raise AssertionError(
                "Cada veículo deveria recolher "
                "20 contentores."
            )

        if (
            route_evaluation.number_of_unloads
            != 1
        ):
            raise AssertionError(
                "Cada veículo deveria efetuar "
                "uma descarga."
            )

        if route_evaluation.final_load_kg != 0.0:
            raise AssertionError(
                "Cada veículo deveria regressar "
                "à base sem carga."
            )

        if (
            route_evaluation.route[0]
            != test_data.base_matrix_id
        ):
            raise AssertionError(
                "Uma rota não começa na base."
            )

        if (
            route_evaluation.route[-1]
            != test_data.base_matrix_id
        ):
            raise AssertionError(
                "Uma rota não termina na base."
            )

        landfill_visits = (
            route_evaluation.route.count(
                test_data.landfill_matrix_id
            )
        )

        if landfill_visits != 1:
            raise AssertionError(
                "Cada rota deveria visitar "
                "o aterro uma vez."
            )

    if len(result.history) != 50:
        raise AssertionError(
            "O histórico deveria conter "
            "50 iterações."
        )

    print(
        "\nMMAS validado com vários veículos."
    )


if __name__ == "__main__":
    main()
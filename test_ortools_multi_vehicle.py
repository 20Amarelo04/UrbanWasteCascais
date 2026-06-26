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
            complete_data.container_matrix_ids[:40]
        ),
    )

    vehicles = [
        VehicleSpec(
            vehicle_id=1,
            name="Camião 1",
            tare_mass_kg=6000.0,
            capacity_kg=1500.0,
            shift_duration_s=OPERATION.shift_duration_s,
        ),
        VehicleSpec(
            vehicle_id=2,
            name="Camião 2",
            tare_mass_kg=6500.0,
            capacity_kg=1500.0,
            shift_duration_s=OPERATION.shift_duration_s,
        ),
    ]

    request = OptimizationRequest(
        algorithm="or-tools",
        vehicles=vehicles,
        container_load_kg=CONTAINERS.load_kg,
        service_time_s=CONTAINERS.service_time_s,
        unload_time_s=OPERATION.unload_time_s,
        max_unloads=2,
        objective=ObjectiveConfig(
            distance_weight=0.30,
            time_weight=0.30,
            fuel_weight=0.40,
        ),
        ortools=ORToolsConfig(
            time_limit_s=20,
            solution_penalty=1_000_000,
        ),
    )

    result = solve_with_ortools(
        data=test_data,
        request=request,
    )

    maximum_vehicle_mass_kg = max(
        vehicle.tare_mass_kg + vehicle.capacity_kg
        for vehicle in vehicles
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
    print("TESTE OR-TOOLS COM VÁRIOS VEÍCULOS")
    print("=" * 75)

    for route_evaluation in evaluation.routes:
        print(f"\n{route_evaluation.vehicle_name}:")
        print(f"  Rota: {route_evaluation.route}")
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
            print(f"  - {violation}")

    if not evaluation.is_feasible:
        raise AssertionError(
            "O OR-Tools devolveu uma solução inválida."
        )

    if len(result.routes) != 2:
        raise AssertionError(
            "O OR-Tools deveria devolver duas rotas."
        )

    if evaluation.duplicated_containers:
        raise AssertionError(
            "Existem contentores atribuídos a mais do que um veículo."
        )

    if len(evaluation.collected_containers) != 40:
        raise AssertionError(
            "Os 40 contentores deveriam ser recolhidos."
        )

    containers_per_vehicle = [
        len(route_evaluation.collected_containers)
        for route_evaluation in evaluation.routes
    ]

    if any(count == 0 for count in containers_per_vehicle):
        raise AssertionError(
            "Cada veículo deveria recolher pelo menos um contentor."
        )

    print(
        "\nOR-Tools validado com vários veículos."
    )


if __name__ == "__main__":
    main()
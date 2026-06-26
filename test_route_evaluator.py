from __future__ import annotations

from config import CONTAINERS, OPERATION
from core.data_loader import load_data_bundle
from core.models import (
    ObjectiveConfig,
    OptimizationRequest,
    VehicleSpec,
)
from core.objective import build_objective_scales
from core.route_evaluator import evaluate_solution


def build_request(
    capacity_kg: float = 9000.0,
) -> OptimizationRequest:
    vehicle = VehicleSpec(
        vehicle_id=1,
        name="Camião 1",
        tare_mass_kg=6000.0,
        capacity_kg=capacity_kg,
        shift_duration_s=(
            OPERATION.shift_duration_s
        ),
    )

    return OptimizationRequest(
        algorithm="test",
        vehicles=[vehicle],
        container_load_kg=(
            CONTAINERS.load_kg
        ),
        service_time_s=(
            CONTAINERS.service_time_s
        ),
        unload_time_s=(
            OPERATION.unload_time_s
        ),
        max_unloads=(
            OPERATION.max_unloads_per_vehicle
        ),
        objective=ObjectiveConfig(
            distance_weight=0.30,
            time_weight=0.30,
            fuel_weight=0.40,
        ),
    )


def main() -> None:
    data = load_data_bundle()

    request = build_request()

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

    valid_route = [
        data.base_matrix_id,
        2,
        3,
        data.landfill_matrix_id,
        data.base_matrix_id,
    ]

    valid_solution = evaluate_solution(
        data=data,
        routes=[valid_route],
        request=request,
        scales=scales,
    )

    print("=" * 75)
    print("TESTE DO AVALIADOR DE ROTAS")
    print("=" * 75)

    print("\nRota válida:")
    print(
        f"  Sequência: {valid_route}"
    )
    print(
        f"  Contentores recolhidos: "
        f"{len(valid_solution.collected_containers)}"
    )
    print(
        f"  Resíduos recolhidos: "
        f"{valid_solution.total_collected_waste_kg:.0f} kg"
    )
    print(
        f"  Distância: "
        f"{valid_solution.total_distance_m / 1000:.2f} km"
    )
    print(
        f"  Tempo: "
        f"{valid_solution.total_time_s / 60:.2f} min"
    )
    print(
        f"  Combustível: "
        f"{valid_solution.total_fuel_l:.4f} L"
    )
    print(
        f"  Score: "
        f"{valid_solution.objective_score:.4f}"
    )
    print(
        f"  Viável: "
        f"{valid_solution.is_feasible}"
    )

    if not valid_solution.is_feasible:
        raise AssertionError(
            "A rota válida foi considerada inválida: "
            f"{valid_solution.violations}"
        )

    if len(
        valid_solution.collected_containers
    ) != 2:
        raise AssertionError(
            "A rota deveria recolher dois contentores."
        )

    if (
        valid_solution.total_collected_waste_kg
        != 300.0
    ):
        raise AssertionError(
            "A quantidade recolhida deveria ser 300 kg."
        )

    route_result = valid_solution.routes[0]

    if route_result.number_of_unloads != 1:
        raise AssertionError(
            "A rota deveria realizar uma descarga."
        )

    if route_result.final_load_kg != 0.0:
        raise AssertionError(
            "O veículo deveria terminar sem carga."
        )

    invalid_route = [
        data.base_matrix_id,
        2,
        3,
        data.base_matrix_id,
    ]

    invalid_solution = evaluate_solution(
        data=data,
        routes=[invalid_route],
        request=request,
        scales=scales,
    )

    print("\nRota inválida:")
    print(
        f"  Sequência: {invalid_route}"
    )
    print(
        f"  Viável: "
        f"{invalid_solution.is_feasible}"
    )
    print("  Violações:")

    for violation in invalid_solution.violations:
        print(
            f"    - {violation}"
        )

    if invalid_solution.is_feasible:
        raise AssertionError(
            "A rota que regressa carregada à base "
            "deveria ser considerada inválida."
        )

    low_capacity_request = build_request(
        capacity_kg=150.0,
    )

    low_capacity_solution = evaluate_solution(
        data=data,
        routes=[
            [
                data.base_matrix_id,
                2,
                3,
                data.landfill_matrix_id,
                data.base_matrix_id,
            ]
        ],
        request=low_capacity_request,
        scales=scales,
    )

    print("\nRota com capacidade excedida:")
    print(
        f"  Viável: "
        f"{low_capacity_solution.is_feasible}"
    )
    print("  Violações:")

    for violation in (
        low_capacity_solution.violations
    ):
        print(
            f"    - {violation}"
        )

    if low_capacity_solution.is_feasible:
        raise AssertionError(
            "A rota deveria exceder a capacidade."
        )

    print(
        "\nAvaliador de rotas validado com sucesso."
    )


if __name__ == "__main__":
    main()
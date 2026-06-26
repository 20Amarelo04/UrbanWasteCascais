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
from services.optimization_service import run_optimization


def main() -> None:
    complete_data = load_data_bundle()

    data = replace(
        complete_data,
        container_matrix_ids=complete_data.container_matrix_ids[:20],
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
        objective=ObjectiveConfig(),
        ortools=ORToolsConfig(
            time_limit_s=10,
            solution_penalty=1_000_000,
        ),
    )

    result = run_optimization(
        data=data,
        request=request,
    )

    print("=" * 75)
    print("TESTE DO SERVIÇO COM OR-TOOLS")
    print("=" * 75)

    print("\nResumo:")
    for key, value in result.summary.items():
        print(f"  {key}: {value}")

    print("\nVeículos:")
    print(result.vehicles_df)

    print("\nTabelas:")
    print(f"  Segmentos: {result.segments_df.shape}")
    print(f"  Sequência: {result.route_sequence_df.shape}")
    print(f"  Não recolhidos: {result.uncollected_df.shape}")

    if not result.summary["solucao_viavel"]:
        raise AssertionError("A solução deveria ser viável.")

    if result.summary["contentores_recolhidos"] != 20:
        raise AssertionError("Deveria recolher os 20 contentores.")

    if result.summary["contentores_duplicados"] != 0:
        raise AssertionError("Não deveria haver contentores duplicados.")

    print("\nServiço validado com OR-Tools.")


if __name__ == "__main__":
    main()
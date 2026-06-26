from __future__ import annotations

from core.data_loader import load_data_bundle
from core.fuel_model import calculate_segment_metrics
from core.models import ObjectiveConfig
from core.objective import (
    build_objective_scales,
    build_solution_key,
    calculate_heuristic_value,
    calculate_objective,
)


def main() -> None:
    data = load_data_bundle()

    objective_config = ObjectiveConfig(
        distance_weight=0.30,
        time_weight=0.30,
        fuel_weight=0.40,
    )

    maximum_vehicle_mass_kg = (
        6000.0 + 9000.0
    )

    scales = build_objective_scales(
        data=data,
        reference_vehicle_mass_kg=(
            maximum_vehicle_mass_kg
        ),
    )

    print("=" * 70)
    print("TESTE DA FUNÇÃO OBJETIVO")
    print("=" * 70)

    print(
        f"Escala da distância: "
        f"{scales.distance_m / 1000:.2f} km"
    )

    print(
        f"Escala do tempo: "
        f"{scales.time_s / 60:.2f} min"
    )

    print(
        f"Escala do combustível: "
        f"{scales.fuel_l:.4f} L"
    )

    empty_metrics = calculate_segment_metrics(
        data=data,
        from_matrix_id=data.base_matrix_id,
        to_matrix_id=data.landfill_matrix_id,
        tare_mass_kg=6000.0,
        current_load_kg=0.0,
    )

    loaded_metrics = calculate_segment_metrics(
        data=data,
        from_matrix_id=data.base_matrix_id,
        to_matrix_id=data.landfill_matrix_id,
        tare_mass_kg=6000.0,
        current_load_kg=9000.0,
    )

    empty_objective = calculate_objective(
        distance_m=empty_metrics["distance_m"],
        time_s=empty_metrics["time_s"],
        fuel_l=empty_metrics["fuel_l"],
        scales=scales,
        objective=objective_config,
    )

    loaded_objective = calculate_objective(
        distance_m=loaded_metrics["distance_m"],
        time_s=loaded_metrics["time_s"],
        fuel_l=loaded_metrics["fuel_l"],
        scales=scales,
        objective=objective_config,
    )

    print("\nVeículo vazio:")
    print(
        f"  Distância normalizada: "
        f"{empty_objective.normalized_distance:.4f}"
    )
    print(
        f"  Tempo normalizado: "
        f"{empty_objective.normalized_time:.4f}"
    )
    print(
        f"  Combustível normalizado: "
        f"{empty_objective.normalized_fuel:.4f}"
    )
    print(
        f"  Score: "
        f"{empty_objective.score:.4f}"
    )

    print("\nVeículo carregado:")
    print(
        f"  Distância normalizada: "
        f"{loaded_objective.normalized_distance:.4f}"
    )
    print(
        f"  Tempo normalizado: "
        f"{loaded_objective.normalized_time:.4f}"
    )
    print(
        f"  Combustível normalizado: "
        f"{loaded_objective.normalized_fuel:.4f}"
    )
    print(
        f"  Score: "
        f"{loaded_objective.score:.4f}"
    )

    if (
        loaded_objective.score
        <= empty_objective.score
    ):
        raise AssertionError(
            "O veículo carregado deveria apresentar "
            "um score superior no mesmo percurso."
        )

    heuristic = calculate_heuristic_value(
        distance_m=empty_metrics["distance_m"],
        time_s=empty_metrics["time_s"],
        fuel_l=empty_metrics["fuel_l"],
        scales=scales,
        objective=objective_config,
    )

    if heuristic <= 0:
        raise AssertionError(
            "O valor heurístico deve ser positivo."
        )

    solution_more_containers = build_solution_key(
        total_containers=877,
        collected_containers=877,
        objective_score=20.0,
        fuel_l=100.0,
        time_s=25_000.0,
        distance_m=200_000.0,
    )

    solution_fewer_containers = build_solution_key(
        total_containers=877,
        collected_containers=876,
        objective_score=1.0,
        fuel_l=20.0,
        time_s=10_000.0,
        distance_m=50_000.0,
    )

    if not (
        solution_more_containers
        < solution_fewer_containers
    ):
        raise AssertionError(
            "A solução que recolhe mais contentores "
            "deveria ser considerada melhor."
        )

    print(
        f"\nValor heurístico do percurso: "
        f"{heuristic:.6f}"
    )

    print(
        "\nFunção objetivo validada com sucesso."
    )


if __name__ == "__main__":
    main()
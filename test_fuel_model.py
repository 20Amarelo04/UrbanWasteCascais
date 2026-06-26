from __future__ import annotations

from core.data_loader import load_data_bundle
from core.fuel_model import calculate_segment_metrics
from core.validation import validate_data_bundle


def main() -> None:
    data = load_data_bundle()

    report = validate_data_bundle(data)

    if not report["valid"]:
        raise RuntimeError(
            "Os dados não passaram na validação."
        )

    tare_mass_kg = 6000.0

    test_loads_kg = [
        0.0,
        3000.0,
        9000.0,
    ]

    print("=" * 75)
    print("TESTE DO MODELO DINÂMICO DE COMBUSTÍVEL")
    print("=" * 75)

    fuel_values: list[float] = []

    for load_kg in test_loads_kg:
        metrics = calculate_segment_metrics(
            data=data,
            from_matrix_id=data.base_matrix_id,
            to_matrix_id=data.landfill_matrix_id,
            tare_mass_kg=tare_mass_kg,
            current_load_kg=load_kg,
        )

        fuel_values.append(
            metrics["fuel_l"]
        )

        print(
            f"Carga: {load_kg:>7.0f} kg | "
            f"Massa total: "
            f"{metrics['vehicle_mass_kg']:>7.0f} kg | "
            f"Distância: "
            f"{metrics['distance_m'] / 1000:>6.2f} km | "
            f"Tempo: "
            f"{metrics['time_s'] / 60:>6.2f} min | "
            f"Velocidade: "
            f"{metrics['speed_kmh']:>6.2f} km/h | "
            f"Declive: "
            f"{metrics['grade'] * 100:>7.3f}% | "
            f"Consumo: "
            f"{metrics['fuel_l']:>8.4f} L"
        )

    if not (
        fuel_values[0]
        <= fuel_values[1]
        <= fuel_values[2]
    ):
        raise AssertionError(
            "O consumo não aumentou com a massa "
            "do veículo."
        )

    same_node_metrics = calculate_segment_metrics(
        data=data,
        from_matrix_id=data.base_matrix_id,
        to_matrix_id=data.base_matrix_id,
        tare_mass_kg=tare_mass_kg,
        current_load_kg=0.0,
    )

    if same_node_metrics["distance_m"] != 0.0:
        raise AssertionError(
            "A distância entre o mesmo nó deve ser zero."
        )

    if same_node_metrics["time_s"] != 0.0:
        raise AssertionError(
            "O tempo entre o mesmo nó deve ser zero."
        )

    if same_node_metrics["fuel_l"] != 0.0:
        raise AssertionError(
            "O consumo entre o mesmo nó deve ser zero."
        )

    print("\nResultados do consumo:")

    for load_kg, fuel_l in zip(
        test_loads_kg,
        fuel_values,
    ):
        print(
            f"  Carga {load_kg:>7.0f} kg: "
            f"{fuel_l:.4f} L"
        )

    print(
        "\nModelo de combustível validado com sucesso."
    )


if __name__ == "__main__":
    main()
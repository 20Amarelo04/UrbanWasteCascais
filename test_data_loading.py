from pprint import pprint

from core.data_loader import load_data_bundle
from core.validation import validate_data_bundle


def main() -> None:
    data = load_data_bundle()

    report = validate_data_bundle(data)

    print("=" * 70)
    print("CARREGAMENTO DOS DADOS")
    print("=" * 70)

    print(
        f"Nós: {len(data.points)}"
    )

    print(
        f"Contentores: "
        f"{len(data.container_matrix_ids)}"
    )

    print(
        f"Base matrix_id: "
        f"{data.base_matrix_id}"
    )

    print(
        f"Aterro matrix_id: "
        f"{data.landfill_matrix_id}"
    )

    print(
        "Matriz de distâncias: "
        f"{data.distance_matrix_m.shape}"
    )

    print(
        "Matriz de tempos: "
        f"{data.time_matrix_s.shape}"
    )

    print("\nRelatório:")
    pprint(report)

    if not report["valid"]:
        raise SystemExit(
            "\nA validação falhou."
        )

    print(
        "\nDados carregados e validados com sucesso."
    )


if __name__ == "__main__":
    main()
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from config import CONTAINERS, NODES
from core.models import DataBundle


REQUIRED_POINT_COLUMNS = {
    "id",
    "matrix_id",
    "latitude",
    "longitude",
    "type",
    "elevation_m",
}


def validate_square_matrix(
    matrix: np.ndarray,
    matrix_name: str,
    *,
    allow_negative: bool = False,
    require_zero_diagonal: bool = True,
) -> list[str]:
    errors: list[str] = []

    if matrix.ndim != 2:
        errors.append(
            f"{matrix_name} deve ter duas dimensões. "
            f"Dimensão atual: {matrix.ndim}."
        )
        return errors

    rows, columns = matrix.shape

    if rows != columns:
        errors.append(
            f"{matrix_name} não é quadrada: "
            f"{rows} × {columns}."
        )

    finite_mask = np.isfinite(matrix)

    if not np.all(finite_mask):
        invalid_count = int(
            matrix.size - finite_mask.sum()
        )

        errors.append(
            f"{matrix_name} contém "
            f"{invalid_count} valores NaN ou infinitos."
        )

    if not allow_negative:
        negative_count = int(
            np.count_nonzero(matrix < 0)
        )

        if negative_count > 0:
            errors.append(
                f"{matrix_name} contém "
                f"{negative_count} valores negativos."
            )

    if (
        require_zero_diagonal
        and rows == columns
    ):
        diagonal = np.diag(matrix)

        if not np.allclose(
            diagonal,
            0.0,
            atol=1e-8,
            equal_nan=False,
        ):
            errors.append(
                f"A diagonal de {matrix_name} "
                "não contém apenas zeros."
            )

    return errors


def validate_points(
    points: pd.DataFrame,
    matrix_size: int,
) -> list[str]:
    errors: list[str] = []

    missing_columns = (
        REQUIRED_POINT_COLUMNS - set(points.columns)
    )

    if missing_columns:
        errors.append(
            "Faltam colunas obrigatórias nos pontos: "
            f"{sorted(missing_columns)}"
        )
        return errors

    if points["matrix_id"].duplicated().any():
        duplicate_ids = (
            points.loc[
                points["matrix_id"].duplicated(
                    keep=False
                ),
                "matrix_id",
            ]
            .astype(int)
            .unique()
            .tolist()
        )

        errors.append(
            "Existem matrix_id duplicados: "
            f"{duplicate_ids[:10]}"
        )

    if points["id"].duplicated().any():
        duplicate_ids = (
            points.loc[
                points["id"].duplicated(
                    keep=False
                ),
                "id",
            ]
            .astype(int)
            .unique()
            .tolist()
        )

        errors.append(
            "Existem IDs de nós duplicados: "
            f"{duplicate_ids[:10]}"
        )

    if len(points) != matrix_size:
        errors.append(
            "O número de pontos não corresponde "
            "à dimensão das matrizes: "
            f"{len(points)} pontos para uma matriz "
            f"{matrix_size} × {matrix_size}."
        )

    expected_matrix_ids = set(
        range(matrix_size)
    )

    actual_matrix_ids = set(
        points["matrix_id"].astype(int)
    )

    missing_ids = (
        expected_matrix_ids - actual_matrix_ids
    )

    unexpected_ids = (
        actual_matrix_ids - expected_matrix_ids
    )

    if missing_ids:
        errors.append(
            "Faltam matrix_id na sequência: "
            f"{sorted(missing_ids)[:20]}"
        )

    if unexpected_ids:
        errors.append(
            "Existem matrix_id fora das matrizes: "
            f"{sorted(unexpected_ids)[:20]}"
        )

    latitude = pd.to_numeric(
        points["latitude"],
        errors="coerce",
    )

    longitude = pd.to_numeric(
        points["longitude"],
        errors="coerce",
    )

    elevation = pd.to_numeric(
        points["elevation_m"],
        errors="coerce",
    )

    if latitude.isna().any():
        errors.append(
            "Existem pontos com latitude inválida."
        )

    if longitude.isna().any():
        errors.append(
            "Existem pontos com longitude inválida."
        )

    if elevation.isna().any():
        errors.append(
            "Existem pontos com elevação inválida."
        )

    if (
        latitude.notna().any()
        and not latitude.dropna().between(
            -90,
            90,
        ).all()
    ):
        errors.append(
            "Existem latitudes fora do intervalo "
            "válido entre -90 e 90 graus."
        )

    if (
        longitude.notna().any()
        and not longitude.dropna().between(
            -180,
            180,
        ).all()
    ):
        errors.append(
            "Existem longitudes fora do intervalo "
            "válido entre -180 e 180 graus."
        )

    empty_types = (
        points["type"]
        .astype(str)
        .str.strip()
        .eq("")
    )

    if empty_types.any():
        errors.append(
            "Existem pontos sem tipo definido."
        )

    return errors


def validate_special_nodes(
    data: DataBundle,
) -> list[str]:
    errors: list[str] = []

    matrix_size = data.distance_matrix_m.shape[0]

    if not (
        0 <= data.base_matrix_id < matrix_size
    ):
        errors.append(
            "O matrix_id da base está fora "
            "dos limites das matrizes."
        )

    if not (
        0 <= data.landfill_matrix_id < matrix_size
    ):
        errors.append(
            "O matrix_id do aterro está fora "
            "dos limites das matrizes."
        )

    if (
        data.base_matrix_id
        == data.landfill_matrix_id
    ):
        errors.append(
            "A base e o aterro não podem ter "
            "o mesmo matrix_id."
        )

    if (
        data.base_matrix_id
        in data.container_matrix_ids
    ):
        errors.append(
            "A base foi identificada como contentor."
        )

    if (
        data.landfill_matrix_id
        in data.container_matrix_ids
    ):
        errors.append(
            "O aterro foi identificado como contentor."
        )

    base_rows = data.points.loc[
        data.points["matrix_id"]
        == data.base_matrix_id
    ]

    if len(base_rows) != 1:
        errors.append(
            "Não foi encontrado exatamente um "
            "registo correspondente à base."
        )

    elif (
        str(base_rows.iloc[0]["type"]).lower()
        != NODES.base_type
    ):
        errors.append(
            "O tipo do nó da base não corresponde "
            f"a '{NODES.base_type}'."
        )

    landfill_rows = data.points.loc[
        data.points["matrix_id"]
        == data.landfill_matrix_id
    ]

    if len(landfill_rows) != 1:
        errors.append(
            "Não foi encontrado exatamente um "
            "registo correspondente ao aterro."
        )

    elif (
        str(landfill_rows.iloc[0]["type"]).lower()
        != NODES.landfill_type
    ):
        errors.append(
            "O tipo do nó do aterro não corresponde "
            f"a '{NODES.landfill_type}'."
        )

    return errors


def validate_container_nodes(
    data: DataBundle,
) -> list[str]:
    errors: list[str] = []

    if not data.container_matrix_ids:
        errors.append(
            "Não foram encontrados contentores."
        )
        return errors

    if (
        len(data.container_matrix_ids)
        != len(set(data.container_matrix_ids))
    ):
        errors.append(
            "Existem contentores repetidos na lista "
            "de container_matrix_ids."
        )

    matrix_size = data.distance_matrix_m.shape[0]

    invalid_container_ids = [
        matrix_id
        for matrix_id in data.container_matrix_ids
        if not 0 <= matrix_id < matrix_size
    ]

    if invalid_container_ids:
        errors.append(
            "Existem contentores com matrix_id "
            "fora das matrizes: "
            f"{invalid_container_ids[:20]}"
        )

    expected_container_ids = set(
        data.points.loc[
            data.points["type"]
            == NODES.container_type,
            "matrix_id",
        ].astype(int)
    )

    actual_container_ids = set(
        data.container_matrix_ids
    )

    if actual_container_ids != expected_container_ids:
        missing_ids = (
            expected_container_ids
            - actual_container_ids
        )

        unexpected_ids = (
            actual_container_ids
            - expected_container_ids
        )

        errors.append(
            "A lista de contentores não corresponde "
            "aos pontos do tipo contentor. "
            f"Em falta: {sorted(missing_ids)[:10]}. "
            f"Inesperados: "
            f"{sorted(unexpected_ids)[:10]}."
        )

    return errors


def count_off_diagonal_zeros(
    matrix: np.ndarray,
) -> int:
    if (
        matrix.ndim != 2
        or matrix.shape[0] != matrix.shape[1]
    ):
        return 0

    off_diagonal_mask = ~np.eye(
        matrix.shape[0],
        dtype=bool,
    )

    return int(
        np.count_nonzero(
            (matrix == 0)
            & off_diagonal_mask
        )
    )


def validate_distance_time_consistency(
    distance_matrix_m: np.ndarray,
    time_matrix_s: np.ndarray,
) -> list[str]:
    errors: list[str] = []

    if (
        distance_matrix_m.shape
        != time_matrix_s.shape
    ):
        return errors

    distance_without_time = (
        (distance_matrix_m > 0)
        & (time_matrix_s <= 0)
    )

    time_without_distance = (
        (time_matrix_s > 0)
        & (distance_matrix_m <= 0)
    )

    distance_without_time_count = int(
        np.count_nonzero(
            distance_without_time
        )
    )

    time_without_distance_count = int(
        np.count_nonzero(
            time_without_distance
        )
    )

    if distance_without_time_count > 0:
        errors.append(
            "Existem "
            f"{distance_without_time_count} ligações "
            "com distância positiva e tempo nulo."
        )

    if time_without_distance_count > 0:
        errors.append(
            "Existem "
            f"{time_without_distance_count} ligações "
            "com tempo positivo e distância nula."
        )

    return errors


def calculate_speed_statistics(
    distance_matrix_m: np.ndarray,
    time_matrix_s: np.ndarray,
) -> dict[str, float | int | None]:
    valid_segments = (
        (distance_matrix_m > 0)
        & (time_matrix_s > 0)
        & np.isfinite(distance_matrix_m)
        & np.isfinite(time_matrix_s)
    )

    if not np.any(valid_segments):
        return {
            "segment_count": 0,
            "minimum_kmh": None,
            "median_kmh": None,
            "maximum_kmh": None,
            "above_130_kmh": 0,
            "below_1_kmh": 0,
        }

    speeds_kmh = (
        distance_matrix_m[valid_segments]
        / time_matrix_s[valid_segments]
        * 3.6
    )

    return {
        "segment_count": int(
            speeds_kmh.size
        ),
        "minimum_kmh": float(
            np.min(speeds_kmh)
        ),
        "median_kmh": float(
            np.median(speeds_kmh)
        ),
        "maximum_kmh": float(
            np.max(speeds_kmh)
        ),
        "above_130_kmh": int(
            np.count_nonzero(
                speeds_kmh > 130
            )
        ),
        "below_1_kmh": int(
            np.count_nonzero(
                speeds_kmh < 1
            )
        ),
    }


def calculate_slope_statistics(
    slope_matrix: np.ndarray,
) -> dict[str, float | int | None]:
    if slope_matrix.size == 0:
        return {
            "minimum": None,
            "median": None,
            "maximum": None,
            "minimum_percent": None,
            "median_percent": None,
            "maximum_percent": None,
            "at_lower_limit": 0,
            "at_upper_limit": 0,
        }

    finite_slopes = slope_matrix[
        np.isfinite(slope_matrix)
    ]

    if finite_slopes.size == 0:
        return {
            "minimum": None,
            "median": None,
            "maximum": None,
            "minimum_percent": None,
            "median_percent": None,
            "maximum_percent": None,
            "at_lower_limit": 0,
            "at_upper_limit": 0,
        }

    minimum = float(
        np.min(finite_slopes)
    )

    median = float(
        np.median(finite_slopes)
    )

    maximum = float(
        np.max(finite_slopes)
    )

    return {
        "minimum": minimum,
        "median": median,
        "maximum": maximum,
        "minimum_percent": minimum * 100,
        "median_percent": median * 100,
        "maximum_percent": maximum * 100,
        "at_lower_limit": int(
            np.count_nonzero(
                finite_slopes <= -0.30
            )
        ),
        "at_upper_limit": int(
            np.count_nonzero(
                finite_slopes >= 0.30
            )
        ),
    }


def validate_data_bundle(
    data: DataBundle,
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    errors.extend(
        validate_square_matrix(
            data.distance_matrix_m,
            "A matriz de distâncias",
            allow_negative=False,
        )
    )

    errors.extend(
        validate_square_matrix(
            data.time_matrix_s,
            "A matriz de tempos",
            allow_negative=False,
        )
    )

    # Declives negativos representam descidas,
    # pelo que são valores válidos.
    errors.extend(
        validate_square_matrix(
            data.slope_matrix,
            "A matriz de declives",
            allow_negative=True,
        )
    )

    if (
        data.distance_matrix_m.shape
        != data.time_matrix_s.shape
    ):
        errors.append(
            "As matrizes de distância e tempo "
            "têm dimensões diferentes: "
            f"{data.distance_matrix_m.shape} e "
            f"{data.time_matrix_s.shape}."
        )

    if (
        data.slope_matrix.shape
        != data.distance_matrix_m.shape
    ):
        errors.append(
            "A matriz de declives não tem "
            "a mesma dimensão da matriz de distâncias: "
            f"{data.slope_matrix.shape} e "
            f"{data.distance_matrix_m.shape}."
        )

    if data.distance_matrix_m.ndim == 2:
        errors.extend(
            validate_points(
                points=data.points,
                matrix_size=(
                    data.distance_matrix_m.shape[0]
                ),
            )
        )

    errors.extend(
        validate_special_nodes(data)
    )

    errors.extend(
        validate_container_nodes(data)
    )

    errors.extend(
        validate_distance_time_consistency(
            distance_matrix_m=(
                data.distance_matrix_m
            ),
            time_matrix_s=data.time_matrix_s,
        )
    )

    if CONTAINERS.load_kg <= 0:
        errors.append(
            "A carga fixa dos contentores "
            "deve ser superior a zero."
        )

    if CONTAINERS.service_time_s < 0:
        errors.append(
            "O tempo de serviço dos contentores "
            "não pode ser negativo."
        )

    distance_zero_count = (
        count_off_diagonal_zeros(
            data.distance_matrix_m
        )
    )

    time_zero_count = (
        count_off_diagonal_zeros(
            data.time_matrix_s
        )
    )

    if distance_zero_count > 0:
        warnings.append(
            "A matriz de distâncias contém "
            f"{distance_zero_count} zeros "
            "fora da diagonal."
        )

    if time_zero_count > 0:
        warnings.append(
            "A matriz de tempos contém "
            f"{time_zero_count} zeros "
            "fora da diagonal."
        )

    speed_statistics = (
        calculate_speed_statistics(
            data.distance_matrix_m,
            data.time_matrix_s,
        )
    )

    if speed_statistics["above_130_kmh"] > 0:
        warnings.append(
            "Existem "
            f"{speed_statistics['above_130_kmh']} "
            "ligações com velocidade calculada "
            "superior a 130 km/h."
        )

    if speed_statistics["below_1_kmh"] > 0:
        warnings.append(
            "Existem "
            f"{speed_statistics['below_1_kmh']} "
            "ligações com velocidade calculada "
            "inferior a 1 km/h."
        )

    slope_statistics = (
        calculate_slope_statistics(
            data.slope_matrix
        )
    )

    if slope_statistics["at_lower_limit"] > 0:
        warnings.append(
            "Existem "
            f"{slope_statistics['at_lower_limit']} "
            "ligações no limite mínimo "
            "de declive de -30%."
        )

    if slope_statistics["at_upper_limit"] > 0:
        warnings.append(
            "Existem "
            f"{slope_statistics['at_upper_limit']} "
            "ligações no limite máximo "
            "de declive de 30%."
        )

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "number_of_nodes": len(
            data.points
        ),
        "number_of_containers": len(
            data.container_matrix_ids
        ),
        "base_matrix_id": (
            data.base_matrix_id
        ),
        "landfill_matrix_id": (
            data.landfill_matrix_id
        ),
        "container_load_kg": (
            CONTAINERS.load_kg
        ),
        "distance_matrix_shape": (
            data.distance_matrix_m.shape
        ),
        "time_matrix_shape": (
            data.time_matrix_s.shape
        ),
        "slope_matrix_shape": (
            data.slope_matrix.shape
        ),
        "speed_statistics": (
            speed_statistics
        ),
        "slope_statistics": (
            slope_statistics
        ),
    }
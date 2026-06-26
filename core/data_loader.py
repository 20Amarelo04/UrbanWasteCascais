from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from config import (
    DISTANCE_MATRIX_FILE,
    NODES,
    NODES_FILE,
    TIME_MATRIX_FILE,
)
from core.models import DataBundle


REQUIRED_NODE_COLUMNS = {
    "id",
    "latitude",
    "longitude",
    "matrix_id",
    "type",
    "elevation_m",
}


def load_nodes(
    path: Path = NODES_FILE,
) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(
            f"Ficheiro de nós não encontrado: {path}"
        )

    points = pd.read_csv(path)

    missing_columns = (
        REQUIRED_NODE_COLUMNS - set(points.columns)
    )

    if missing_columns:
        raise ValueError(
            "Faltam colunas obrigatórias em nodes.csv: "
            f"{sorted(missing_columns)}"
        )

    points = points.copy()

    points["id"] = pd.to_numeric(
        points["id"],
        errors="raise",
    ).astype(int)

    points["matrix_id"] = pd.to_numeric(
        points["matrix_id"],
        errors="raise",
    ).astype(int)

    points["latitude"] = pd.to_numeric(
        points["latitude"],
        errors="raise",
    )

    points["longitude"] = pd.to_numeric(
        points["longitude"],
        errors="raise",
    )

    points["elevation_m"] = pd.to_numeric(
        points["elevation_m"],
        errors="raise",
    )

    points["type"] = (
        points["type"]
        .astype(str)
        .str.strip()
        .str.lower()
    )

    points = (
        points
        .sort_values("matrix_id")
        .reset_index(drop=True)
    )

    return points


def load_matrix(
    path: Path,
) -> np.ndarray:
    if not path.exists():
        raise FileNotFoundError(
            f"Ficheiro de matriz não encontrado: {path}"
        )

    dataframe = pd.read_csv(
        path,
        index_col=0,
    )

    if dataframe.shape[0] != dataframe.shape[1]:
        raise ValueError(
            f"A matriz '{path.name}' não é quadrada: "
            f"{dataframe.shape}"
        )

    matrix = dataframe.to_numpy(
        dtype=float,
        copy=True,
    )

    if not np.all(np.isfinite(matrix)):
        raise ValueError(
            f"A matriz '{path.name}' contém "
            "valores NaN ou infinitos."
        )

    if np.any(matrix < 0):
        raise ValueError(
            f"A matriz '{path.name}' contém "
            "valores negativos."
        )

    return np.asarray(
        matrix,
        dtype=float,
    )


def validate_matrix_dimensions(
    points: pd.DataFrame,
    distance_matrix_m: np.ndarray,
    time_matrix_s: np.ndarray,
) -> None:
    if distance_matrix_m.shape != time_matrix_s.shape:
        raise ValueError(
            "As matrizes de distância e tempo "
            "têm dimensões diferentes: "
            f"{distance_matrix_m.shape} e "
            f"{time_matrix_s.shape}."
        )

    number_of_nodes = len(points)
    matrix_size = distance_matrix_m.shape[0]

    if number_of_nodes != matrix_size:
        raise ValueError(
            "O número de nós não corresponde "
            "à dimensão das matrizes: "
            f"{number_of_nodes} nós e matriz "
            f"{matrix_size} × {matrix_size}."
        )

    expected_matrix_ids = set(
        range(matrix_size)
    )

    actual_matrix_ids = set(
        points["matrix_id"].astype(int)
    )

    if actual_matrix_ids != expected_matrix_ids:
        missing_ids = (
            expected_matrix_ids - actual_matrix_ids
        )

        unexpected_ids = (
            actual_matrix_ids - expected_matrix_ids
        )

        raise ValueError(
            "Os matrix_id não correspondem "
            "às posições das matrizes. "
            f"Em falta: {sorted(missing_ids)[:10]}. "
            f"Inesperados: {sorted(unexpected_ids)[:10]}."
        )


def build_slope_matrix(
    points: pd.DataFrame,
    distance_matrix_m: np.ndarray,
) -> np.ndarray:
    ordered_points = points.sort_values(
        "matrix_id"
    )

    elevations_m = ordered_points[
        "elevation_m"
    ].to_numpy(
        dtype=float,
        copy=True,
    )

    if elevations_m.size != distance_matrix_m.shape[0]:
        raise ValueError(
            "O número de elevações não corresponde "
            "à dimensão da matriz de distâncias."
        )

    if not np.all(np.isfinite(elevations_m)):
        raise ValueError(
            "Existem valores de elevação inválidos."
        )

    elevation_difference_m = (
        elevations_m[np.newaxis, :]
        - elevations_m[:, np.newaxis]
    )

    slope_matrix = np.divide(
        elevation_difference_m,
        distance_matrix_m,
        out=np.zeros_like(
            distance_matrix_m,
            dtype=float,
        ),
        where=distance_matrix_m > 0,
    )

    slope_matrix = np.clip(
        slope_matrix,
        -0.30,
        0.30,
    )

    np.fill_diagonal(
        slope_matrix,
        0.0,
    )

    return slope_matrix


def build_node_mappings(
    points: pd.DataFrame,
) -> tuple[dict[int, int], dict[int, int]]:
    matrix_id_to_node_id = dict(
        zip(
            points["matrix_id"].astype(int),
            points["id"].astype(int),
        )
    )

    node_id_to_matrix_id = dict(
        zip(
            points["id"].astype(int),
            points["matrix_id"].astype(int),
        )
    )

    return (
        matrix_id_to_node_id,
        node_id_to_matrix_id,
    )


def get_special_node(
    points: pd.DataFrame,
    expected_type: str,
    fallback_matrix_id: int,
) -> int:
    matches = (
        points.loc[
            points["type"] == expected_type,
            "matrix_id",
        ]
        .astype(int)
        .tolist()
    )

    if len(matches) == 1:
        return matches[0]

    if len(matches) > 1:
        raise ValueError(
            f"Foram encontrados vários nós "
            f"do tipo '{expected_type}': {matches}"
        )

    fallback_row = points.loc[
        points["matrix_id"] == fallback_matrix_id
    ]

    if len(fallback_row) == 1:
        return int(fallback_matrix_id)

    raise ValueError(
        f"Não foi possível identificar "
        f"o nó '{expected_type}'."
    )


def load_data_bundle() -> DataBundle:
    points = load_nodes()

    distance_matrix_m = load_matrix(
        DISTANCE_MATRIX_FILE
    )

    time_matrix_s = load_matrix(
        TIME_MATRIX_FILE
    )

    validate_matrix_dimensions(
        points=points,
        distance_matrix_m=distance_matrix_m,
        time_matrix_s=time_matrix_s,
    )

    slope_matrix = build_slope_matrix(
        points=points,
        distance_matrix_m=distance_matrix_m,
    )

    base_matrix_id = get_special_node(
        points=points,
        expected_type=NODES.base_type,
        fallback_matrix_id=NODES.base_matrix_id,
    )

    landfill_matrix_id = get_special_node(
        points=points,
        expected_type=NODES.landfill_type,
        fallback_matrix_id=NODES.landfill_matrix_id,
    )

    if base_matrix_id == landfill_matrix_id:
        raise ValueError(
            "A base e o aterro não podem "
            "ter o mesmo matrix_id."
        )

    container_matrix_ids = (
        points.loc[
            points["type"] == NODES.container_type,
            "matrix_id",
        ]
        .astype(int)
        .tolist()
    )

    if not container_matrix_ids:
        raise ValueError(
            "Não foram encontrados contentores."
        )

    (
        matrix_id_to_node_id,
        node_id_to_matrix_id,
    ) = build_node_mappings(points)

    return DataBundle(
        points=points,
        distance_matrix_m=distance_matrix_m,
        time_matrix_s=time_matrix_s,
        slope_matrix=slope_matrix,
        base_matrix_id=base_matrix_id,
        landfill_matrix_id=landfill_matrix_id,
        container_matrix_ids=container_matrix_ids,
        matrix_id_to_node_id=matrix_id_to_node_id,
        node_id_to_matrix_id=node_id_to_matrix_id,
    )
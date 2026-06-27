from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from core.fuel_model import calculate_fuel_liters
from core.models import DataBundle, ObjectiveConfig


@dataclass(frozen=True)
class ObjectiveScales:
    distance_m: float
    time_s: float
    fuel_l: float

    def validate(self) -> None:
        if self.distance_m <= 0:
            raise ValueError(
                "A escala da distância deve ser positiva."
            )

        if self.time_s <= 0:
            raise ValueError(
                "A escala do tempo deve ser positiva."
            )

        if self.fuel_l <= 0:
            raise ValueError(
                "A escala do combustível deve ser positiva."
            )


@dataclass(frozen=True)
class ObjectiveBreakdown:
    distance_m: float
    time_s: float
    fuel_l: float

    normalized_distance: float
    normalized_time: float
    normalized_fuel: float

    distance_component: float
    time_component: float
    fuel_component: float

    score: float


def positive_percentile(
    values: np.ndarray,
    percentile: float,
) -> float:
    valid_values = values[
        np.isfinite(values)
        & (values > 0)
    ]

    if valid_values.size == 0:
        raise ValueError(
            "Não existem valores positivos válidos "
            "para calcular a escala."
        )

    return float(
        np.percentile(
            valid_values,
            percentile,
        )
    )


def build_objective_scales(
    data: DataBundle,
    reference_vehicle_mass_kg: float,
    percentile: float = 95.0,
    fuel_sample_size: int = 20_000,
) -> ObjectiveScales:
    if reference_vehicle_mass_kg <= 0:
        raise ValueError(
            "A massa de referência do veículo "
            "deve ser positiva."
        )

    if not 0 < percentile <= 100:
        raise ValueError(
            "O percentil deve estar entre 0 e 100."
        )

    distance_scale = positive_percentile(
        data.distance_matrix_m,
        percentile,
    )

    time_scale = positive_percentile(
        data.time_matrix_s,
        percentile,
    )

    valid_segments = (
        (data.distance_matrix_m > 0)
        & (data.time_matrix_s > 0)
        & np.isfinite(data.distance_matrix_m)
        & np.isfinite(data.time_matrix_s)
        & np.isfinite(data.slope_matrix)
    )

    valid_positions = np.flatnonzero(
        valid_segments
    )

    if valid_positions.size == 0:
        raise ValueError(
            "Não existem segmentos válidos "
            "para calcular a escala de combustível."
        )

    number_of_samples = min(
        fuel_sample_size,
        valid_positions.size,
    )

    sample_positions = np.linspace(
        0,
        valid_positions.size - 1,
        num=number_of_samples,
        dtype=int,
    )

    selected_positions = valid_positions[
        sample_positions
    ]

    distance_values = (
        data.distance_matrix_m.ravel()[
            selected_positions
        ]
    )

    time_values = (
        data.time_matrix_s.ravel()[
            selected_positions
        ]
    )

    slope_values = (
        data.slope_matrix.ravel()[
            selected_positions
        ]
    )

    fuel_values = np.fromiter(
        (
            calculate_fuel_liters(
                distance_m=float(distance_m),
                time_s=float(time_s),
                grade=float(grade),
                vehicle_mass_kg=(
                    reference_vehicle_mass_kg
                ),
            )
            for distance_m, time_s, grade in zip(
                distance_values,
                time_values,
                slope_values,
            )
        ),
        dtype=float,
        count=number_of_samples,
    )

    fuel_scale = positive_percentile(
        fuel_values,
        percentile,
    )

    scales = ObjectiveScales(
        distance_m=distance_scale,
        time_s=time_scale,
        fuel_l=fuel_scale,
    )

    scales.validate()

    return scales


def calculate_objective(
    distance_m: float,
    time_s: float,
    fuel_l: float,
    scales: ObjectiveScales,
    objective: ObjectiveConfig,
) -> ObjectiveBreakdown:
    scales.validate()
    objective.validate()

    if distance_m < 0:
        raise ValueError(
            "A distância não pode ser negativa."
        )

    if time_s < 0:
        raise ValueError(
            "O tempo não pode ser negativo."
        )

    if fuel_l < 0:
        raise ValueError(
            "O combustível não pode ser negativo."
        )

    normalized_distance = (
        distance_m / scales.distance_m
    )

    normalized_time = (
        time_s / scales.time_s
    )

    normalized_fuel = (
        fuel_l / scales.fuel_l
    )

    distance_component = (
        objective.distance_weight
        * normalized_distance
    )

    time_component = (
        objective.time_weight
        * normalized_time
    )

    fuel_component = (
        objective.fuel_weight
        * normalized_fuel
    )

    score = (
        distance_component
        + time_component
        + fuel_component
    )

    return ObjectiveBreakdown(
        distance_m=float(distance_m),
        time_s=float(time_s),
        fuel_l=float(fuel_l),
        normalized_distance=float(
            normalized_distance
        ),
        normalized_time=float(
            normalized_time
        ),
        normalized_fuel=float(
            normalized_fuel
        ),
        distance_component=float(
            distance_component
        ),
        time_component=float(
            time_component
        ),
        fuel_component=float(
            fuel_component
        ),
        score=float(score),
    )


def calculate_heuristic_value(
    distance_m: float,
    time_s: float,
    fuel_l: float,
    scales: ObjectiveScales,
    objective: ObjectiveConfig,
    epsilon: float = 1e-12,
) -> float:
    breakdown = calculate_objective(
        distance_m=distance_m,
        time_s=time_s,
        fuel_l=fuel_l,
        scales=scales,
        objective=objective,
    )

    return float(
        1.0 / max(
            breakdown.score,
            epsilon,
        )
    )


def build_solution_key(
    total_containers: int,
    collected_containers: int,
    objective_score: float,
    fuel_l: float,
    time_s: float,
    distance_m: float,
) -> tuple:
    if total_containers < 0:
        raise ValueError(
            "O número total de contentores "
            "não pode ser negativo."
        )

    if not 0 <= collected_containers <= total_containers:
        raise ValueError(
            "O número de contentores recolhidos "
            "é inválido."
        )

    uncollected_containers = (
        total_containers
        - collected_containers
    )

    return (
        uncollected_containers,
        objective_score,
        fuel_l,
        distance_m,
        time_s,
    )

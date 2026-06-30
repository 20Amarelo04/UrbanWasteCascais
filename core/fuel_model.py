from __future__ import annotations

import math
from dataclasses import dataclass
import numpy as np

from core.models import DataBundle


@dataclass(frozen=True)
class FuelParameters:
    lam: float = 3.08e-5
    k: float = 0.2
    engine_speed_rps: float = 36.67
    engine_displacement_l: float = 6.9

    gravity_m_s2: float = 9.8
    rolling_resistance: float = 0.01

    drag_coefficient: float = 0.7
    frontal_area_m2: float = 8.0
    air_density_kg_m3: float = 1.2041

    engine_efficiency: float = 0.45
    drivetrain_efficiency: float = 0.45

    minimum_speed_m_s: float = 0.1
    minimum_grade: float = -0.25
    maximum_grade: float = 0.25


DEFAULT_FUEL_PARAMETERS = FuelParameters()


def calculate_beta_coefficients(
    parameters: FuelParameters = DEFAULT_FUEL_PARAMETERS,
) -> tuple[float, float, float]:

    beta_1 = (
        parameters.lam
        * parameters.k
        * parameters.engine_speed_rps
        * parameters.engine_displacement_l
    )

    efficiency = (
        parameters.engine_efficiency
        * parameters.drivetrain_efficiency
    )

    beta_2 = (
        parameters.lam
        * parameters.gravity_m_s2
        / (1000.0 * efficiency)
    )

    beta_3 = (
        0.5
        * parameters.lam
        * parameters.drag_coefficient
        * parameters.frontal_area_m2
        * parameters.air_density_kg_m3
        / (1000.0 * efficiency)
    )

    return beta_1, beta_2, beta_3


def calculate_fuel_liters(
    distance_m: float,
    time_s: float,
    grade: float,
    vehicle_mass_kg: float,
    current_load_kg: float = 0.0,
    parameters: FuelParameters = DEFAULT_FUEL_PARAMETERS,
) -> float:

    if distance_m <= 0 or time_s <= 0:
        return 0.0

    if vehicle_mass_kg <= 0:
        raise ValueError("Massa inválida")

    speed_m_s = max(
        distance_m / max(time_s, 1.0),
        parameters.minimum_speed_m_s,
    )

    load_factor = 1.0 + (current_load_kg / max(vehicle_mass_kg, 1.0))
    vehicle_mass_kg *= load_factor

    safe_grade = float(
        np.clip(grade,
                parameters.minimum_grade,
                parameters.maximum_grade)
    )

    theta = math.atan(safe_grade)

    resistance = (
        math.sin(theta)
        + parameters.rolling_resistance * math.cos(theta)
    )

    beta_1, beta_2, beta_3 = calculate_beta_coefficients(parameters)

    engine_consumption_l = (
        beta_1 * distance_m / speed_m_s
    )

    movement_consumption_l = (
        beta_2 * resistance * vehicle_mass_kg * distance_m
        + beta_3 * distance_m * speed_m_s**2
    )

    total_fuel_l = engine_consumption_l + max(movement_consumption_l, 0.0)

    return float(max(total_fuel_l, 0.0))


def calculate_segment_metrics(
    data: DataBundle,
    from_matrix_id: int,
    to_matrix_id: int,
    tare_mass_kg: float,
    current_load_kg: float,
    parameters: FuelParameters = DEFAULT_FUEL_PARAMETERS,
) -> dict[str, float]:

    matrix_size = data.distance_matrix_m.shape[0]

    if not 0 <= from_matrix_id < matrix_size:
        raise IndexError("origem inválida")

    if not 0 <= to_matrix_id < matrix_size:
        raise IndexError("destino inválido")

    distance_m = float(data.distance_matrix_m[from_matrix_id, to_matrix_id])
    time_s = float(data.time_matrix_s[from_matrix_id, to_matrix_id])
    grade = float(data.slope_matrix[from_matrix_id, to_matrix_id])

    vehicle_mass_kg = tare_mass_kg + current_load_kg

    fuel_l = calculate_fuel_liters(
        distance_m=distance_m,
        time_s=time_s,
        grade=grade,
        vehicle_mass_kg=vehicle_mass_kg,
        current_load_kg=current_load_kg,
        parameters=parameters,
    )

    speed_m_s = distance_m / max(time_s, 1.0)

    return {
        "distance_m": distance_m,
        "time_s": time_s,
        "speed_m_s": speed_m_s,
        "speed_kmh": speed_m_s * 3.6,
        "grade": grade,
        "tare_mass_kg": tare_mass_kg,
        "load_kg": current_load_kg,
        "vehicle_mass_kg": vehicle_mass_kg,
        "fuel_l": fuel_l,
    }
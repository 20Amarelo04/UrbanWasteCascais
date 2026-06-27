from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class VehicleSpec:
    vehicle_id: int
    name: str
    tare_mass_kg: float
    capacity_kg: float
    shift_duration_s: int


@dataclass(frozen=True)
class MMASConfig:
    num_ants: int = 10
    num_iterations: int = 40

    alpha: float = 1.0
    beta: float = 3.0
    evaporation_rate: float = 0.20

    elite_ants: int = 3
    candidate_list_size: int = 15

    tau_min_ratio: float = 0.05
    stagnation_limit: int = 20

    random_seed: int | None = 42

@dataclass(frozen=True)
class ORToolsConfig:
    time_limit_s: int = 10
    solution_penalty: int = 1_000_000

    def validate(self) -> None:
        if self.time_limit_s <= 0:
            raise ValueError(
                "O limite de tempo do OR-Tools deve ser positivo."
            )

        if self.solution_penalty <= 0:
            raise ValueError(
                "A penalização do OR-Tools deve ser positiva."
            )

@dataclass(frozen=True)
class ObjectiveConfig:
    distance_weight: float = 0.50
    time_weight: float = 0.0
    fuel_weight: float = 0.50

    def validate(self) -> None:
        weights = (
            self.distance_weight,
            self.time_weight,
            self.fuel_weight,
        )

        if any(weight < 0 for weight in weights):
            raise ValueError(
                "Os pesos da função objetivo não podem ser negativos."
            )

        if abs(sum(weights) - 1.0) > 1e-9:
            raise ValueError(
                "A soma dos pesos da função objetivo deve ser 1."
            )


@dataclass(frozen=True)
class OptimizationRequest:
    algorithm: str
    vehicles: list[VehicleSpec]

    container_load_kg: float
    service_time_s: int
    unload_time_s: int
    max_unloads: int

    objective: ObjectiveConfig
    mmas: MMASConfig | None = None
    ortools: ORToolsConfig | None = None


@dataclass
class DataBundle:
    points: pd.DataFrame

    distance_matrix_m: np.ndarray
    time_matrix_s: np.ndarray
    slope_matrix: np.ndarray

    base_matrix_id: int
    landfill_matrix_id: int
    container_matrix_ids: list[int]

    matrix_id_to_node_id: dict[int, int]
    node_id_to_matrix_id: dict[int, int]


@dataclass
class SolverOutput:
    routes: list[list[int]]
    uncollected_nodes: list[int]

    solver_cost: float
    runtime_s: float

    history: list[dict[str, Any]] = field(
        default_factory=list
    )


@dataclass
class OptimizationResult:
    solver_output: SolverOutput

    summary: dict[str, Any]

    vehicles_df: pd.DataFrame
    segments_df: pd.DataFrame
    route_sequence_df: pd.DataFrame
    uncollected_df: pd.DataFrame

    map_object: Any | None = None

@dataclass(frozen=True)
class SegmentEvaluation:
    vehicle_id: int
    sequence: int

    from_matrix_id: int
    to_matrix_id: int
    event_type: str

    distance_m: float
    travel_time_s: float
    service_time_s: float
    unload_time_s: float
    total_segment_time_s: float

    speed_kmh: float
    grade: float

    load_before_kg: float
    load_after_kg: float
    vehicle_mass_kg: float

    fuel_l: float


@dataclass
class RouteEvaluation:
    vehicle_id: int
    vehicle_name: str
    route: list[int]

    segments: list[SegmentEvaluation]
    collected_containers: list[int]

    total_distance_m: float
    total_travel_time_s: float
    total_service_time_s: float
    total_unload_time_s: float
    total_time_s: float
    total_fuel_l: float

    number_of_unloads: int
    final_load_kg: float

    objective_score: float

    is_feasible: bool
    violations: list[str]


@dataclass
class SolutionEvaluation:
    routes: list[RouteEvaluation]

    collected_containers: list[int]
    uncollected_containers: list[int]
    duplicated_containers: list[int]

    total_distance_m: float
    total_travel_time_s: float
    total_service_time_s: float
    total_unload_time_s: float
    total_time_s: float
    maximum_route_time_s: float
    total_fuel_l: float
    total_collected_waste_kg: float

    objective_score: float
    solution_key: tuple[
        int,
        float,
        float,
        float,
        float,
    ]

    is_feasible: bool
    violations: list[str]

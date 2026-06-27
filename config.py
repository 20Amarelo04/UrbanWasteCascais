from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
RESULTS_DIR = BASE_DIR / "results"

NODES_FILE = DATA_DIR / "nodes.csv"
DISTANCE_MATRIX_FILE = DATA_DIR / "distance_matrix.csv"
TIME_MATRIX_FILE = DATA_DIR / "time_matrix.csv"
GRAPH_FILE = DATA_DIR / "cascais_osmnx_graph.graphml"


@dataclass(frozen=True)
class NodeConfig:
    base_matrix_id: int = 0
    landfill_matrix_id: int = 1

    base_type: str = "start_point"
    landfill_type: str = "collection_point"
    container_type: str = "container"


@dataclass(frozen=True)
class ContainerConfig:
    load_kg: float = 150.0
    service_time_s: int = 120


@dataclass(frozen=True)
class OperationConfig:
    shift_duration_s: int = 8 * 60 * 60
    unload_time_s: int = 30 * 60
    max_unloads_per_vehicle: int = 15


@dataclass(frozen=True)
class ObjectiveWeights:
    distance: float = 0.50
    time: float = 0.0
    fuel: float = 0.50

    def validate(self) -> None:
        weights = (
            self.distance,
            self.time,
            self.fuel,
        )

        if any(weight < 0 for weight in weights):
            raise ValueError(
                "Os pesos não podem ser negativos."
            )

        if abs(sum(weights) - 1.0) > 1e-9:
            raise ValueError(
                "A soma dos pesos deve ser igual a 1."
            )


NODES = NodeConfig()
CONTAINERS = ContainerConfig()
OPERATION = OperationConfig()
OBJECTIVE_WEIGHTS = ObjectiveWeights()

OBJECTIVE_WEIGHTS.validate()
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

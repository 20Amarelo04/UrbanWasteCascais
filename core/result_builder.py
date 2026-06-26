from __future__ import annotations

from dataclasses import asdict
from typing import Any

import pandas as pd

from core.models import (
    DataBundle,
    OptimizationRequest,
    OptimizationResult,
    SolverOutput,
)
from core.objective import build_objective_scales
from core.route_evaluator import (
    evaluate_solution,
    identify_event_type,
)


def build_optimization_result(
    data: DataBundle,
    request: OptimizationRequest,
    solver_output: SolverOutput,
) -> OptimizationResult:
    maximum_vehicle_mass_kg = max(
        vehicle.tare_mass_kg + vehicle.capacity_kg
        for vehicle in request.vehicles
    )

    scales = build_objective_scales(
        data=data,
        reference_vehicle_mass_kg=maximum_vehicle_mass_kg,
    )

    evaluation = evaluate_solution(
        data=data,
        routes=solver_output.routes,
        request=request,
        scales=scales,
    )

    vehicles_df = pd.DataFrame(
        [
            {
                "vehicle_id": route.vehicle_id,
                "vehicle_name": route.vehicle_name,
                "contentores": len(route.collected_containers),
                "lixo_recolhido_kg": (
                    len(route.collected_containers)
                    * request.container_load_kg
                ),
                "distancia_km": route.total_distance_m / 1000,
                "tempo_h": route.total_time_s / 3600,
                "combustivel_l": route.total_fuel_l,
                "descargas": route.number_of_unloads,
                "carga_final_kg": route.final_load_kg,
                "viavel": route.is_feasible,
                "violacoes": "; ".join(route.violations),
            }
            for route in evaluation.routes
        ]
    )

    segments_df = pd.DataFrame(
        [
            asdict(segment)
            for route in evaluation.routes
            for segment in route.segments
        ]
    )

    points_lookup = data.points.set_index("matrix_id", drop=False)

    route_sequence_df = pd.DataFrame(
        [
            {
                "vehicle_id": route.vehicle_id,
                "vehicle_name": route.vehicle_name,
                "sequence": sequence,
                "matrix_id": int(matrix_id),
                "node_id": int(points_lookup.loc[matrix_id, "id"]),
                "event_type": identify_event_type(
                    matrix_id=int(matrix_id),
                    data=data,
                ),
                "latitude": float(points_lookup.loc[matrix_id, "latitude"]),
                "longitude": float(points_lookup.loc[matrix_id, "longitude"]),
            }
            for route in evaluation.routes
            for sequence, matrix_id in enumerate(route.route)
        ]
    )

    uncollected_df = (
        data.points.loc[
            data.points["matrix_id"].isin(
                evaluation.uncollected_containers
            )
        ]
        .copy()
        .reset_index(drop=True)
    )

    summary: dict[str, Any] = {
        "algorithm": request.algorithm,
        "veiculos_disponiveis": len(request.vehicles),
        "veiculos_utilizados": int(
            (vehicles_df["contentores"] > 0).sum()
        ),
        "contentores_recolhidos": len(
            evaluation.collected_containers
        ),
        "contentores_nao_recolhidos": len(
            evaluation.uncollected_containers
        ),
        "contentores_duplicados": len(
            evaluation.duplicated_containers
        ),
        "lixo_recolhido_kg": evaluation.total_collected_waste_kg,
        "distancia_total_km": evaluation.total_distance_m / 1000,
        "combustivel_total_l": evaluation.total_fuel_l,
        "maior_tempo_veiculo_h": (
            evaluation.maximum_route_time_s / 3600
        ),
        "score_objetivo": evaluation.objective_score,
        "solver_cost": solver_output.solver_cost,
        "runtime_s": solver_output.runtime_s,
        "solucao_viavel": evaluation.is_feasible,
        "violacoes": evaluation.violations,
    }

    return OptimizationResult(
        solver_output=solver_output,
        summary=summary,
        vehicles_df=vehicles_df,
        segments_df=segments_df,
        route_sequence_df=route_sequence_df,
        uncollected_df=uncollected_df,
        map_object=None,
    )
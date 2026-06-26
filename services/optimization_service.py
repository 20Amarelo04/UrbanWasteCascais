from __future__ import annotations

from core.models import (
    DataBundle,
    OptimizationRequest,
    OptimizationResult,
    SolverOutput,
)
from core.result_builder import build_optimization_result
from solvers.mmas_solver import solve_with_mmas
from solvers.ortools_solver import solve_with_ortools


def run_optimization(
    data: DataBundle,
    request: OptimizationRequest,
) -> OptimizationResult:
    algorithm = request.algorithm.strip().lower()

    if algorithm == "mmas":
        solver_output = solve_with_mmas(
            data=data,
            request=request,
        )

    elif algorithm in {"or-tools", "ortools"}:
        solver_output = solve_with_ortools(
            data=data,
            request=request,
        )

    else:
        raise ValueError(
            f"Algoritmo não suportado: {request.algorithm}"
        )

    validate_solver_output(solver_output)

    return build_optimization_result(
        data=data,
        request=request,
        solver_output=solver_output,
    )


def validate_solver_output(
    output: SolverOutput,
) -> None:
    if not output.routes:
        raise ValueError(
            "O algoritmo não devolveu nenhuma rota."
        )

    if output.runtime_s < 0:
        raise ValueError(
            "O tempo de execução não pode ser negativo."
        )

    for route in output.routes:
        if len(route) < 2:
            raise ValueError(
                "Foi devolvida uma rota inválida."
            )
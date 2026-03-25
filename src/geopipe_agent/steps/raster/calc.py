"""raster.calc — Raster band calculation using expressions."""

from __future__ import annotations

from geopipe_agent.steps.registry import step
from geopipe_agent.engine.context import StepContext
from geopipe_agent.models.result import StepResult


@step(
    id="raster.calc",
    name="栅格计算",
    description="对栅格波段执行数学运算（如 NDVI = (B4-B3)/(B4+B3)）",
    category="raster",
    params={
        "input": {
            "type": "raster_info",
            "required": True,
            "description": "输入栅格数据",
        },
        "expression": {
            "type": "string",
            "required": True,
            "description": "计算表达式，使用 B1, B2, ... 引用波段（如 '(B4-B3)/(B4+B3)'）",
        },
    },
    outputs={
        "output": {"type": "raster_info", "description": "计算结果栅格"},
    },
    examples=[
        {
            "description": "计算 NDVI",
            "params": {
                "input": "$satellite.output",
                "expression": "(B4-B3)/(B4+B3)",
            },
        },
    ],
)
def raster_calc(ctx: StepContext) -> StepResult:
    import ast
    import numpy as np
    import re

    from geopipe_agent.utils.safe_eval import validate_calc_ast

    raster = ctx.input("input")
    expression = ctx.param("expression")

    data = raster["data"]

    # Build a namespace with band references B1, B2, ...
    band_vars = {}
    for i in range(data.shape[0]):
        band_vars[f"B{i + 1}"] = data[i].astype(np.float64)

    # Validate that only allowed names are referenced
    used_names = set(re.findall(r"\b(B\d+)\b", expression))
    available = set(band_vars.keys())
    unknown = used_names - available
    if unknown:
        raise ValueError(
            f"Expression references unknown bands: {unknown}. "
            f"Available bands: {sorted(available)}"
        )

    # AST-based whitelist validation — only allow safe numeric operations
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise ValueError(f"Invalid expression syntax: {exc}") from exc

    validate_calc_ast(tree, available)

    # Safe evaluation with numpy functions
    safe_ns = {"__builtins__": {}, "np": np}
    safe_ns.update(band_vars)

    with np.errstate(divide="ignore", invalid="ignore"):
        result_data = eval(  # noqa: S307
            compile(tree, "<raster_calc>", "eval"), safe_ns
        )

    # Ensure result is a numpy array
    result_data = np.asarray(result_data, dtype=np.float64)

    # Handle NaN/inf
    result_data = np.where(np.isfinite(result_data), result_data, np.nan)

    # Result is a single-band raster
    if result_data.ndim == 2:
        result_data = result_data[np.newaxis, :, :]

    profile = raster["profile"].copy()
    profile.update({
        "count": result_data.shape[0],
        "dtype": "float64",
    })

    result = {
        "data": result_data,
        "transform": raster["transform"],
        "crs": raster["crs"],
        "profile": profile,
    }

    valid = result_data[np.isfinite(result_data)]
    stats = {
        "expression": expression,
        "min": float(valid.min()) if valid.size > 0 else None,
        "max": float(valid.max()) if valid.size > 0 else None,
        "mean": float(valid.mean()) if valid.size > 0 else None,
    }

    return StepResult(output=result, stats=stats)

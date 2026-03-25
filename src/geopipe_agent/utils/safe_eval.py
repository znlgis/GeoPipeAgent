"""Safe expression evaluation utilities.

Provides AST-based validation to ensure only safe constructs
are evaluated. Used by both ``when`` conditions and ``raster.calc``.
"""

from __future__ import annotations

import ast
from typing import Any

# AST nodes considered safe for simple comparison/boolean expressions
# (used by ``when`` conditions in the executor).
SAFE_CONDITION_NODES: tuple[type, ...] = (
    ast.Expression, ast.Compare, ast.BoolOp, ast.UnaryOp, ast.BinOp,
    ast.Constant, ast.Name, ast.Load,
    ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE,
    ast.Is, ast.IsNot, ast.In, ast.NotIn,
    ast.And, ast.Or, ast.Not,
    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod,
)

# AST nodes considered safe for numeric band-math expressions
# (used by ``raster.calc``).
SAFE_CALC_NODES: tuple[type, ...] = (
    ast.Expression, ast.BinOp, ast.UnaryOp, ast.Compare, ast.BoolOp,
    ast.Constant, ast.Name, ast.Load,
    # Arithmetic operators
    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow,
    ast.USub, ast.UAdd,
    # Comparison operators (for masking)
    ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE,
    ast.And, ast.Or, ast.Not,
    # Function calls restricted to np.* below
    ast.Call, ast.Attribute,
)

# Numpy functions allowed in raster.calc expressions.
SAFE_NP_FUNCS: frozenset[str] = frozenset({
    "abs", "sqrt", "log", "log2", "log10", "exp",
    "sin", "cos", "tan", "arcsin", "arccos", "arctan",
    "minimum", "maximum", "where", "clip", "nan_to_num",
})


def validate_condition_ast(tree: ast.AST) -> str | None:
    """Validate an AST tree for safe condition evaluation.

    Returns ``None`` if the tree is safe, or a description of the
    first unsafe node encountered.
    """
    for node in ast.walk(tree):
        if not isinstance(node, SAFE_CONDITION_NODES):
            return f"Unsafe AST node '{type(node).__name__}'"
    return None


def validate_calc_ast(tree: ast.AST, allowed_names: set[str]) -> None:
    """Validate an AST tree for safe raster band-math evaluation.

    Args:
        tree: Parsed AST in ``eval`` mode.
        allowed_names: Set of valid band variable names (e.g. {"B1", "B2"}).

    Raises:
        ValueError: If the tree contains disallowed constructs.
    """
    for node in ast.walk(tree):
        if not isinstance(node, SAFE_CALC_NODES):
            raise ValueError(
                f"Expression contains disallowed construct: {type(node).__name__}. "
                "Only numeric/band operations and np.* math functions are allowed."
            )
        # Validate function calls: only np.<safe_func> allowed
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
                if func.value.id == "np" and func.attr in SAFE_NP_FUNCS:
                    continue
            if isinstance(func, ast.Name) and func.id in allowed_names:
                continue  # band name used in expression context
            raise ValueError(
                f"Expression contains disallowed function call. "
                f"Only np.{{{', '.join(sorted(SAFE_NP_FUNCS))}}} are allowed."
            )
        # Validate attribute access: only np.<attr> allowed
        if isinstance(node, ast.Attribute):
            if isinstance(node.value, ast.Name) and node.value.id == "np":
                continue
            raise ValueError(
                "Expression contains disallowed attribute access. "
                "Only np.* attributes are allowed."
            )
        # Validate Name nodes: must be band references or 'np'
        if isinstance(node, ast.Name) and node.id not in allowed_names and node.id != "np":
            raise ValueError(
                f"Expression references unknown name '{node.id}'. "
                f"Allowed: {sorted(allowed_names)} and np.*"
            )


def safe_eval(code: str, namespace: dict[str, Any] | None = None) -> Any:
    """Compile and evaluate an expression in a restricted namespace.

    The caller is responsible for validating the AST before calling this.
    """
    tree = ast.parse(code, mode="eval")
    return eval(  # noqa: S307
        compile(tree, "<safe_eval>", "eval"),
        {"__builtins__": {}},
        namespace or {},
    )

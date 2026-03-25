"""qc.topology — Check topological rules (overlaps, gaps, dangles)."""

from __future__ import annotations

from geopipe_agent.steps.registry import step
from geopipe_agent.engine.context import StepContext
from geopipe_agent.models.result import StepResult
from geopipe_agent.models.qc import QcIssue
from geopipe_agent.steps.qc._helpers import make_vector_qc_result


@step(
    id="qc.topology",
    name="拓扑关系检查",
    description="检查矢量数据的拓扑关系，检测缝隙(gaps)、重叠(overlaps)、悬挂线(dangles)等问题",
    category="qc",
    params={
        "input": {
            "type": "geodataframe",
            "required": True,
            "description": "输入矢量数据",
        },
        "rules": {
            "type": "list",
            "required": True,
            "description": "要检查的拓扑规则列表: no_overlaps, no_gaps, no_dangles",
        },
        "tolerance": {
            "type": "number",
            "required": False,
            "default": 0.0,
            "description": "容差值（用于判定是否重叠/缝隙）",
        },
        "severity": {
            "type": "string",
            "required": False,
            "default": "error",
            "enum": ["error", "warning", "info"],
            "description": "问题严重级别",
        },
    },
    outputs={
        "output": {"type": "geodataframe", "description": "透传的输入数据"},
        "issues": {"type": "list", "description": "质检问题列表"},
    },
    examples=[
        {
            "description": "检查地块数据无重叠",
            "params": {
                "input": "$parcels.output",
                "rules": ["no_overlaps"],
                "tolerance": 0.001,
            },
        },
    ],
)
def qc_topology(ctx: StepContext) -> StepResult:
    from shapely.ops import unary_union

    gdf = ctx.input("input")
    rules: list[str] = ctx.param("rules")
    tolerance = ctx.param("tolerance", 0.0)
    severity = ctx.param("severity", "error")

    issues: list[QcIssue] = []

    if "no_overlaps" in rules:
        issues.extend(_check_no_overlaps(gdf, tolerance, severity))

    if "no_gaps" in rules:
        issues.extend(_check_no_gaps(gdf, tolerance, severity))

    if "no_dangles" in rules:
        issues.extend(_check_no_dangles(gdf, severity))

    return make_vector_qc_result(gdf, issues, {"rules_checked": rules})


def _check_no_overlaps(gdf, tolerance: float, severity: str) -> list[QcIssue]:
    """Detect pairwise overlapping polygons using spatial index."""
    from shapely.geometry import Polygon, MultiPolygon

    issues: list[QcIssue] = []
    sindex = gdf.sindex
    checked: set[tuple[int, int]] = set()

    for i, row_i in gdf.iterrows():
        geom_i = row_i.geometry
        if geom_i is None or geom_i.is_empty:
            continue
        if not isinstance(geom_i, (Polygon, MultiPolygon)):
            continue

        candidates = list(sindex.intersection(geom_i.bounds))
        for j in candidates:
            if j <= i:
                continue
            pair = (i, j)
            if pair in checked:
                continue
            checked.add(pair)

            geom_j = gdf.geometry.iloc[j]
            if geom_j is None or geom_j.is_empty:
                continue

            intersection = geom_i.intersection(geom_j)
            if not intersection.is_empty:
                area = intersection.area
                if area > tolerance:
                    issues.append(QcIssue(
                        rule_id="topology_no_overlaps",
                        severity=severity,
                        feature_index=i,
                        message=f"Features {i} and {j} overlap (area={area:.6f})",
                        geometry=intersection,
                        details={"other_feature": j, "overlap_area": area},
                    ))

    return issues


def _check_no_gaps(gdf, tolerance: float, severity: str) -> list[QcIssue]:
    """Detect gaps between polygons by comparing union with convex hull."""
    from shapely.ops import unary_union
    from shapely.geometry import Polygon, MultiPolygon

    issues: list[QcIssue] = []

    polygons = [g for g in gdf.geometry if g is not None and not g.is_empty
                and isinstance(g, (Polygon, MultiPolygon))]
    if len(polygons) < 2:
        return issues

    union_geom = unary_union(polygons)
    convex = union_geom.convex_hull
    gap = convex.difference(union_geom)

    if not gap.is_empty and gap.area > tolerance:
        # Report individual gap components
        if hasattr(gap, "geoms"):
            gap_parts = list(gap.geoms)
        else:
            gap_parts = [gap]

        for idx, part in enumerate(gap_parts):
            if part.area > tolerance:
                issues.append(QcIssue(
                    rule_id="topology_no_gaps",
                    severity=severity,
                    feature_index=None,
                    message=f"Gap detected (area={part.area:.6f})",
                    geometry=part,
                    details={"gap_area": part.area, "gap_index": idx},
                ))

    return issues


def _check_no_dangles(gdf, severity: str) -> list[QcIssue]:
    """Detect dangling line endpoints (endpoints not shared with other lines)."""
    from shapely.geometry import LineString, MultiLineString, Point

    issues: list[QcIssue] = []

    # Collect all endpoints
    endpoints: dict[tuple[float, float], list[int]] = {}
    for idx, row in gdf.iterrows():
        geom = row.geometry
        if geom is None or geom.is_empty:
            continue

        lines = []
        if isinstance(geom, LineString):
            lines = [geom]
        elif isinstance(geom, MultiLineString):
            lines = list(geom.geoms)
        else:
            continue

        for line in lines:
            coords = list(line.coords)
            if len(coords) < 2:
                continue
            for pt in [coords[0], coords[-1]]:
                key = (round(pt[0], 8), round(pt[1], 8))
                endpoints.setdefault(key, []).append(idx)

    # Endpoints appearing only once are dangles
    for pt_key, feature_ids in endpoints.items():
        if len(feature_ids) == 1:
            issues.append(QcIssue(
                rule_id="topology_no_dangles",
                severity=severity,
                feature_index=feature_ids[0],
                message=f"Feature {feature_ids[0]}: dangling endpoint at ({pt_key[0]}, {pt_key[1]})",
                geometry=Point(pt_key[0], pt_key[1]),
                details={"endpoint": list(pt_key)},
            ))

    return issues

"""network.service_area — Compute service area (isochrone) from a network."""

from __future__ import annotations

from geopipe_agent.steps.registry import step
from geopipe_agent.engine.context import StepContext
from geopipe_agent.models.result import StepResult


@step(
    id="network.service_area",
    name="服务区分析",
    description="计算网络中从给定点出发在指定成本内可达的服务区域",
    category="network",
    params={
        "input": {
            "type": "geodataframe",
            "required": True,
            "description": "输入线矢量数据（道路/管线网络）",
        },
        "center": {
            "type": "list",
            "required": True,
            "description": "中心点坐标 [x, y]",
        },
        "cost_limit": {
            "type": "number",
            "required": True,
            "description": "最大行程成本（距离或时间）",
        },
        "weight": {
            "type": "string",
            "required": False,
            "description": "权重字段名。不指定则使用几何长度",
        },
    },
    outputs={
        "output": {"type": "geodataframe", "description": "服务区域（可达边线集合）"},
    },
    examples=[
        {
            "description": "计算 1000 米服务区",
            "params": {
                "input": "$roads.output",
                "center": [116.4, 39.9],
                "cost_limit": 1000,
            },
        },
    ],
)
def network_service_area(ctx: StepContext) -> StepResult:
    import networkx as nx
    import numpy as np
    import geopandas as gpd
    from shapely.geometry import LineString, Point, MultiLineString
    from shapely.ops import unary_union

    gdf = ctx.input("input")
    center = ctx.param("center")
    cost_limit = ctx.param("cost_limit")
    weight_field = ctx.param("weight")

    # Build graph from line geometries
    G = nx.Graph()

    for idx, row in gdf.iterrows():
        geom = row.geometry
        if geom is None or geom.is_empty:
            continue
        coords = list(geom.coords)
        if len(coords) < 2:
            continue
        for i in range(len(coords) - 1):
            u = coords[i]
            v = coords[i + 1]
            seg = LineString([u, v])
            edge_weight = seg.length
            if weight_field and weight_field in gdf.columns:
                edge_weight = row[weight_field] / max(1, len(coords) - 1)
            G.add_edge(u, v, weight=edge_weight, geometry=seg)

    if len(G.nodes) == 0:
        raise ValueError("Cannot build network graph: no valid line geometries found.")

    # Find nearest node to center
    nodes = list(G.nodes)
    center_pt = Point(center)
    center_node = min(nodes, key=lambda n: Point(n).distance(center_pt))

    # Compute shortest path lengths from center
    lengths = nx.single_source_dijkstra_path_length(G, center_node, cutoff=cost_limit, weight="weight")

    # Collect edges that are within the service area
    reachable_nodes = set(lengths.keys())
    service_lines = []

    for u, v, data in G.edges(data=True):
        if u in reachable_nodes and v in reachable_nodes:
            geom = data.get("geometry")
            if geom:
                service_lines.append(geom)

    if service_lines:
        merged = unary_union(service_lines)
        # Buffer the lines to create an area polygon
        service_area = merged.buffer(cost_limit * 0.05)
    else:
        service_area = center_pt.buffer(cost_limit * 0.01)

    result_gdf = gpd.GeoDataFrame(
        {
            "reachable_nodes": [len(reachable_nodes)],
            "reachable_edges": [len(service_lines)],
            "cost_limit": [cost_limit],
        },
        geometry=[service_area],
        crs=gdf.crs,
    )

    stats = {
        "reachable_nodes": len(reachable_nodes),
        "reachable_edges": len(service_lines),
        "cost_limit": cost_limit,
    }

    return StepResult(output=result_gdf, stats=stats)

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
    import geopandas as gpd
    from shapely.geometry import Point
    from shapely.ops import unary_union

    from geopipe_agent.steps.network._graph import build_network_graph, find_nearest_node

    gdf = ctx.input("input")
    center = ctx.param("center")
    cost_limit = ctx.param("cost_limit")
    weight_field = ctx.param("weight")

    # Build graph from line geometries
    G = build_network_graph(gdf, weight_field)

    # Find nearest node to center
    center_node = find_nearest_node(G, tuple(center))

    # Compute shortest path lengths from center
    lengths = nx.single_source_dijkstra_path_length(G, center_node, cutoff=cost_limit, weight="weight")

    # Collect edges that are within the service area
    reachable_nodes = set(lengths.keys())
    service_lines = [
        data["geometry"]
        for u, v, data in G.edges(data=True)
        if u in reachable_nodes and v in reachable_nodes and data.get("geometry")
    ]

    if service_lines:
        merged = unary_union(service_lines)
        # Buffer the lines to create an area polygon
        service_area = merged.buffer(cost_limit * 0.05)
    else:
        service_area = Point(center).buffer(cost_limit * 0.01)

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

"""network.shortest_path — Find shortest path in a network."""

from __future__ import annotations

from geopipe_agent.steps.registry import step
from geopipe_agent.engine.context import StepContext
from geopipe_agent.models.result import StepResult


@step(
    id="network.shortest_path",
    name="最短路径",
    description="在道路/管线网络中计算两点之间的最短路径",
    category="network",
    params={
        "input": {
            "type": "geodataframe",
            "required": True,
            "description": "输入线矢量数据（道路/管线网络）",
        },
        "origin": {
            "type": "list",
            "required": True,
            "description": "起点坐标 [x, y]",
        },
        "destination": {
            "type": "list",
            "required": True,
            "description": "终点坐标 [x, y]",
        },
        "weight": {
            "type": "string",
            "required": False,
            "description": "权重字段名（如 'length'）。不指定则使用几何长度",
        },
    },
    outputs={
        "output": {"type": "geodataframe", "description": "最短路径矢量数据"},
    },
    examples=[
        {
            "description": "计算两点间最短路径",
            "params": {
                "input": "$roads.output",
                "origin": [116.3, 39.9],
                "destination": [116.5, 40.0],
            },
        },
    ],
)
def network_shortest_path(ctx: StepContext) -> StepResult:
    import networkx as nx
    import geopandas as gpd
    from shapely.geometry import LineString

    from geopipe_agent.steps.network._graph import build_network_graph, find_nearest_node

    gdf = ctx.input("input")
    origin = ctx.param("origin")
    destination = ctx.param("destination")
    weight_field = ctx.param("weight")

    # Build graph from line geometries
    G = build_network_graph(gdf, weight_field)

    # Find nearest nodes to origin and destination
    origin_node = find_nearest_node(G, tuple(origin))
    dest_node = find_nearest_node(G, tuple(destination))

    try:
        path = nx.shortest_path(G, source=origin_node, target=dest_node, weight="weight")
    except nx.NetworkXNoPath:
        raise ValueError(
            f"No path found between {origin} and {destination}. "
            "The network may be disconnected."
        )

    # Build path geometry
    path_line = LineString(list(path))
    total_cost = nx.shortest_path_length(G, source=origin_node, target=dest_node, weight="weight")

    result_gdf = gpd.GeoDataFrame(
        {"path_cost": [total_cost], "node_count": [len(path)]},
        geometry=[path_line],
        crs=gdf.crs,
    )

    stats = {
        "path_cost": float(total_cost),
        "node_count": len(path),
        "path_length": float(path_line.length),
    }

    return StepResult(output=result_gdf, stats=stats)

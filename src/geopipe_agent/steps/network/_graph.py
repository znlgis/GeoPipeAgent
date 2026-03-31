"""Shared utilities for network step implementations."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import geopandas as gpd
    import networkx as nx


def build_network_graph(gdf: gpd.GeoDataFrame, weight_field: str | None = None) -> nx.Graph:
    """Build a NetworkX graph from line geometries in a GeoDataFrame.

    Each line segment between consecutive vertices becomes an edge.
    Edge weight defaults to segment length unless *weight_field* is specified.

    Args:
        gdf: GeoDataFrame with line geometries.
        weight_field: Optional column name whose value is distributed evenly
            across the segments of each feature.

    Returns:
        A ``networkx.Graph`` with coordinate tuples as nodes.

    Raises:
        ValueError: If no valid line geometries are found.
    """
    import networkx as nx
    from shapely.geometry import LineString

    G = nx.Graph()

    for _, row in gdf.iterrows():
        geom = row.geometry
        if geom is None or geom.is_empty:
            continue
        coords = list(geom.coords)
        if len(coords) < 2:
            continue
        num_segments = len(coords) - 1
        for i in range(num_segments):
            u, v = coords[i], coords[i + 1]
            seg = LineString([u, v])
            edge_weight = seg.length
            if weight_field and weight_field in gdf.columns:
                edge_weight = row[weight_field] / max(1, num_segments)
            G.add_edge(u, v, weight=edge_weight, geometry=seg)

    if len(G.nodes) == 0:
        raise ValueError("Cannot build network graph: no valid line geometries found.")

    return G


def find_nearest_node(graph: nx.Graph, point: tuple[float, float]) -> tuple:
    """Return the node in *graph* nearest to *point*."""
    from shapely.geometry import Point

    pt = Point(point)
    return min(graph.nodes, key=lambda n: Point(n).distance(pt))

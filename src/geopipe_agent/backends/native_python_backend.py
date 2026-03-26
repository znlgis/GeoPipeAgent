"""Native Python backend — default backend using GeoPandas/Shapely."""

from __future__ import annotations

from typing import Any

from geopipe_agent.backends.base import GeoBackend


class NativePythonBackend(GeoBackend):
    """Backend using GeoPandas + Shapely for in-process vector operations."""

    def name(self) -> str:
        return "native_python"

    def is_available(self) -> bool:
        try:
            import geopandas  # noqa: F401
            import shapely  # noqa: F401
            return True
        except ImportError:
            return False

    def buffer(self, gdf: Any, distance: float, **kwargs) -> Any:
        cap_style = kwargs.get("cap_style", "round")
        cap_map = {"round": 1, "flat": 2, "square": 3}
        cap = cap_map.get(cap_style, 1)
        result = gdf.copy()
        result["geometry"] = gdf.geometry.buffer(distance, cap_style=cap)
        return result

    def clip(self, input_gdf: Any, clip_gdf: Any, **kwargs) -> Any:
        import geopandas as gpd

        return gpd.clip(input_gdf, clip_gdf)

    def reproject(self, gdf: Any, target_crs: str, **kwargs) -> Any:
        return gdf.to_crs(target_crs)

    def dissolve(self, gdf: Any, by: str | None = None, **kwargs) -> Any:
        aggfunc = kwargs.get("aggfunc", "first")
        if by:
            return gdf.dissolve(by=by, aggfunc=aggfunc)
        return gdf.dissolve(aggfunc=aggfunc)

    def simplify(self, gdf: Any, tolerance: float, **kwargs) -> Any:
        preserve_topology = kwargs.get("preserve_topology", True)
        result = gdf.copy()
        result["geometry"] = gdf.geometry.simplify(
            tolerance, preserve_topology=preserve_topology
        )
        return result

    def overlay(self, gdf1: Any, gdf2: Any, how: str = "intersection", **kwargs) -> Any:
        import geopandas as gpd

        return gpd.overlay(gdf1, gdf2, how=how)


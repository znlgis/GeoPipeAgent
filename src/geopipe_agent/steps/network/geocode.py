"""network.geocode — Geocode addresses to coordinates."""

from __future__ import annotations

from geopipe_agent.steps.decorators import step
from geopipe_agent.engine.context import StepContext
from geopipe_agent.models.result import StepResult


@step(
    id="network.geocode",
    name="地理编码",
    description="将地址列表转换为地理坐标（使用 geopy 库）",
    category="network",
    params={
        "addresses": {
            "type": "list",
            "required": True,
            "description": "地址列表",
        },
        "provider": {
            "type": "string",
            "required": False,
            "default": "nominatim",
            "description": "地理编码服务提供商（nominatim, google 等）",
        },
        "user_agent": {
            "type": "string",
            "required": False,
            "default": "geopipe-agent",
            "description": "HTTP User-Agent 标头（Nominatim 要求）",
        },
    },
    outputs={
        "output": {"type": "geodataframe", "description": "地理编码结果（点数据）"},
    },
    examples=[
        {
            "description": "地理编码地址列表",
            "params": {
                "addresses": ["北京市天安门", "上海市外滩"],
                "provider": "nominatim",
            },
        },
    ],
)
def network_geocode(ctx: StepContext) -> StepResult:
    import geopandas as gpd
    from geopy.geocoders import Nominatim
    from geopy.exc import GeocoderServiceError, GeocoderTimedOut, GeocoderUnavailable
    from shapely.geometry import Point

    addresses = ctx.param("addresses")
    provider = ctx.param("provider", "nominatim")
    user_agent = ctx.param("user_agent", "geopipe-agent")

    if provider != "nominatim":
        raise ValueError(
            f"Unsupported geocoding provider: '{provider}'. "
            "Currently only 'nominatim' is supported."
        )

    geolocator = Nominatim(user_agent=user_agent)

    results = []
    points = []
    failed = []

    for addr in addresses:
        try:
            location = geolocator.geocode(addr)
            if location:
                results.append({
                    "address": addr,
                    "resolved_address": location.address,
                    "latitude": location.latitude,
                    "longitude": location.longitude,
                })
                points.append(Point(location.longitude, location.latitude))
            else:
                failed.append(addr)
                results.append({
                    "address": addr,
                    "resolved_address": None,
                    "latitude": None,
                    "longitude": None,
                })
                points.append(None)
        except (GeocoderServiceError, GeocoderTimedOut, GeocoderUnavailable, ValueError) as e:
            failed.append(addr)
            results.append({
                "address": addr,
                "resolved_address": None,
                "latitude": None,
                "longitude": None,
            })
            points.append(None)

    # Filter out failed results for the GeoDataFrame
    valid_results = [r for r, p in zip(results, points) if p is not None]
    valid_points = [p for p in points if p is not None]

    gdf = gpd.GeoDataFrame(
        valid_results,
        geometry=valid_points,
        crs="EPSG:4326",
    ) if valid_points else gpd.GeoDataFrame(
        columns=["address", "resolved_address", "latitude", "longitude", "geometry"],
        crs="EPSG:4326",
    )

    stats = {
        "total": len(addresses),
        "success": len(valid_results),
        "failed": len(failed),
        "failed_addresses": failed,
    }

    return StepResult(output=gdf, stats=stats)

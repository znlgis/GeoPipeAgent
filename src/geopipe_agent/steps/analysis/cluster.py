"""analysis.cluster — Spatial clustering of point data."""

from __future__ import annotations

from geopipe_agent.steps.registry import step
from geopipe_agent.engine.context import StepContext
from geopipe_agent.models.result import StepResult


@step(
    id="analysis.cluster",
    name="空间聚类",
    description="对点数据进行空间聚类分析（支持 DBSCAN 和 KMeans）",
    category="analysis",
    params={
        "input": {
            "type": "geodataframe",
            "required": True,
            "description": "输入点矢量数据",
        },
        "method": {
            "type": "string",
            "required": False,
            "default": "dbscan",
            "enum": ["dbscan", "kmeans"],
            "description": "聚类算法",
        },
        "n_clusters": {
            "type": "number",
            "required": False,
            "default": 5,
            "description": "簇数量（仅 KMeans 有效）",
        },
        "eps": {
            "type": "number",
            "required": False,
            "default": 0.5,
            "description": "邻域半径（仅 DBSCAN 有效）",
        },
        "min_samples": {
            "type": "number",
            "required": False,
            "default": 5,
            "description": "最小样本数（仅 DBSCAN 有效）",
        },
    },
    outputs={
        "output": {"type": "geodataframe", "description": "带聚类标签的矢量数据"},
    },
    examples=[
        {
            "description": "DBSCAN 聚类",
            "params": {"input": "$points.output", "method": "dbscan", "eps": 0.1},
        },
    ],
)
def analysis_cluster(ctx: StepContext) -> StepResult:
    import numpy as np
    from sklearn.cluster import DBSCAN, KMeans

    gdf = ctx.input("input")
    method = ctx.param("method", "dbscan")

    # Extract coordinates
    coords = np.array([(g.x, g.y) for g in gdf.geometry])

    if method == "dbscan":
        eps = ctx.param("eps", 0.5)
        min_samples = ctx.param("min_samples", 5)
        model = DBSCAN(eps=eps, min_samples=min_samples)
    elif method == "kmeans":
        n_clusters = ctx.param("n_clusters", 5)
        n_clusters = min(n_clusters, len(coords))
        model = KMeans(n_clusters=n_clusters, n_init="auto", random_state=42)
    else:
        raise ValueError(f"Unknown clustering method: '{method}'. Use 'dbscan' or 'kmeans'.")

    labels = model.fit_predict(coords)

    result_gdf = gdf.copy()
    result_gdf["cluster"] = labels

    n_clusters_found = len(set(labels) - {-1})
    noise_count = int((labels == -1).sum()) if method == "dbscan" else 0

    stats = {
        "method": method,
        "n_clusters": n_clusters_found,
        "noise_count": noise_count,
        "feature_count": len(result_gdf),
    }

    return StepResult(output=result_gdf, stats=stats)

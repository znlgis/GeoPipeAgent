"""Step package — auto-imports all built-in step modules to trigger registration."""

from geopipe_agent.steps.registry import StepRegistry
from geopipe_agent.steps.decorators import step


def load_builtin_steps() -> None:
    """Import all built-in step modules so they register with the StepRegistry."""
    # Each import triggers the @step decorators in those modules
    import geopipe_agent.steps.io.read_vector  # noqa: F401
    import geopipe_agent.steps.io.write_vector  # noqa: F401
    import geopipe_agent.steps.io.read_raster  # noqa: F401
    import geopipe_agent.steps.io.write_raster  # noqa: F401
    import geopipe_agent.steps.vector.buffer  # noqa: F401
    import geopipe_agent.steps.vector.clip  # noqa: F401
    import geopipe_agent.steps.vector.reproject  # noqa: F401
    import geopipe_agent.steps.vector.dissolve  # noqa: F401
    import geopipe_agent.steps.vector.simplify  # noqa: F401
    import geopipe_agent.steps.vector.query  # noqa: F401
    import geopipe_agent.steps.vector.overlay  # noqa: F401
    import geopipe_agent.steps.raster.reproject  # noqa: F401
    import geopipe_agent.steps.raster.clip  # noqa: F401
    import geopipe_agent.steps.raster.calc  # noqa: F401
    import geopipe_agent.steps.raster.stats  # noqa: F401
    import geopipe_agent.steps.raster.contour  # noqa: F401
    import geopipe_agent.steps.analysis.voronoi  # noqa: F401
    import geopipe_agent.steps.analysis.heatmap  # noqa: F401
    import geopipe_agent.steps.analysis.interpolate  # noqa: F401
    import geopipe_agent.steps.analysis.cluster  # noqa: F401
    import geopipe_agent.steps.network.shortest_path  # noqa: F401
    import geopipe_agent.steps.network.service_area  # noqa: F401
    import geopipe_agent.steps.network.geocode  # noqa: F401


__all__ = ["StepRegistry", "step", "load_builtin_steps"]

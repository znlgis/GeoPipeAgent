"""Click CLI for GeoPipeAgent."""

from __future__ import annotations

import json
import sys

import click

import geopipe_agent  # noqa: F401 — triggers auto-loading of built-in steps
from geopipe_agent.utils.logging import setup_logging


@click.group()
@click.version_option(package_name="geopipe-agent")
def main():
    """GeoPipeAgent — AI-Native GIS Analysis Pipeline Framework."""
    pass


@main.command()
@click.argument("file", type=click.Path(exists=True))
@click.option("--log-level", default="INFO", help="Log level (DEBUG, INFO, WARNING, ERROR)")
@click.option("--json-log", is_flag=True, help="Use JSON log format")
@click.option("--var", multiple=True, help="Override pipeline variable: --var key=value")
def run(file: str, log_level: str, json_log: bool, var: tuple[str, ...]):
    """Run a YAML pipeline file."""
    setup_logging(level=log_level, json_format=json_log)

    from geopipe_agent.engine.parser import parse_yaml
    from geopipe_agent.engine.validator import validate_pipeline
    from geopipe_agent.engine.executor import execute_pipeline
    from geopipe_agent.errors import GeopipeAgentError

    try:
        pipeline = parse_yaml(file)

        # Apply --var overrides
        for v in var:
            if "=" not in v:
                raise click.BadParameter(
                    f"Invalid variable format '{v}'. Expected key=value.",
                    param_hint="--var",
                )
            key, _, value = v.partition("=")
            pipeline.variables[key.strip()] = value.strip()

        warnings = validate_pipeline(pipeline)
        for w in warnings:
            click.echo(f"Warning: {w}", err=True)
        report = execute_pipeline(pipeline)
        click.echo(json.dumps(report, indent=2, ensure_ascii=False, default=str))
    except GeopipeAgentError as e:
        error_output = {"error": type(e).__name__, "message": str(e)}
        if hasattr(e, "to_dict"):
            error_output = e.to_dict()
        click.echo(json.dumps(error_output, indent=2, ensure_ascii=False), err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(
            json.dumps({"error": "UnexpectedError", "message": str(e)}, indent=2),
            err=True,
        )
        sys.exit(1)


@main.command()
@click.argument("file", type=click.Path(exists=True))
@click.option("--log-level", default="WARNING", help="Log level")
def validate(file: str, log_level: str):
    """Validate a YAML pipeline file without executing it."""
    setup_logging(level=log_level)

    from geopipe_agent.engine.parser import parse_yaml
    from geopipe_agent.engine.validator import validate_pipeline
    from geopipe_agent.errors import GeopipeAgentError

    try:
        pipeline = parse_yaml(file)
        warnings = validate_pipeline(pipeline)
        result = {
            "status": "valid",
            "pipeline": pipeline.name,
            "steps_count": len(pipeline.steps),
            "steps": [{"id": s.id, "use": s.use} for s in pipeline.steps],
        }
        if warnings:
            result["warnings"] = warnings
        click.echo(json.dumps(result, indent=2, ensure_ascii=False))
    except GeopipeAgentError as e:
        error_output = {"status": "invalid", "error": type(e).__name__, "message": str(e)}
        click.echo(json.dumps(error_output, indent=2, ensure_ascii=False), err=True)
        sys.exit(1)


@main.command("list-steps")
@click.option("--category", default=None, help="Filter by category (io, vector, raster, analysis, network)")
@click.option("--format", "fmt", type=click.Choice(["table", "json"]), default="table", help="Output format")
def list_steps(category: str | None, fmt: str):
    """List all available pipeline steps."""
    from geopipe_agent.steps import registry

    if category:
        steps = registry.list_by_category(category)
    else:
        steps = registry.list_all()

    if fmt == "json":
        click.echo(json.dumps([s.to_dict() for s in steps], indent=2, ensure_ascii=False))
    else:
        # Table format
        click.echo(f"{'ID':<30} {'Name':<20} {'Category':<12} {'Backends'}")
        click.echo("-" * 80)
        for s in steps:
            backends_str = ", ".join(s.backends) if s.backends else "-"
            click.echo(f"{s.id:<30} {s.name:<20} {s.category:<12} {backends_str}")
        click.echo(f"\nTotal: {len(steps)} steps")


@main.command()
@click.argument("step_id")
def describe(step_id: str):
    """Show detailed information about a specific step."""
    from geopipe_agent.steps import registry

    info = registry.get(step_id)

    if info is None:
        click.echo(
            json.dumps(
                {"error": "StepNotFoundError", "message": f"Step '{step_id}' is not registered."},
                indent=2,
            ),
            err=True,
        )
        sys.exit(1)

    click.echo(json.dumps(info.to_dict(), indent=2, ensure_ascii=False))


@main.command()
@click.argument("file", type=click.Path(exists=True))
def info(file: str):
    """Show summary information about a GIS data file."""
    try:
        import geopandas as gpd

        gdf = gpd.read_file(file)
        result = {
            "path": file,
            "format": "vector",
            "feature_count": len(gdf),
            "crs": str(gdf.crs) if gdf.crs else None,
            "geometry_types": list(gdf.geometry.geom_type.unique()),
            "columns": list(gdf.columns),
            "bounds": list(gdf.total_bounds),
        }
        click.echo(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    except Exception:
        # Try raster
        try:
            import rasterio

            with rasterio.open(file) as src:
                result = {
                    "path": file,
                    "format": "raster",
                    "driver": src.driver,
                    "crs": str(src.crs) if src.crs else None,
                    "width": src.width,
                    "height": src.height,
                    "bands": src.count,
                    "dtypes": list(src.dtypes),
                    "bounds": list(src.bounds),
                    "transform": list(src.transform)[:6],
                }
                click.echo(json.dumps(result, indent=2, ensure_ascii=False, default=str))
        except Exception as e:
            click.echo(
                json.dumps({"error": "FileInfoError", "message": str(e)}, indent=2),
                err=True,
            )
            sys.exit(1)


@main.command()
def backends():
    """List available GIS backends and their status."""
    from geopipe_agent.backends import _BACKEND_CLASSES

    result = [
        {"name": cls().name(), "available": cls().is_available()}
        for cls in _BACKEND_CLASSES
    ]
    click.echo(json.dumps(result, indent=2))


@main.command("generate-skill-doc")
def generate_skill_doc():
    """Generate steps reference Markdown for AI consumption."""
    from geopipe_agent.skillgen.generator import generate_steps_reference

    click.echo(generate_steps_reference())


@main.command("generate-skill")
@click.option("--output-dir", default="skills/geopipe-agent", help="Output directory")
def generate_skill(output_dir: str):
    """Generate complete Skill file set for AI."""
    from geopipe_agent.skillgen.generator import write_skill_files

    files = write_skill_files(output_dir)
    for f in files:
        click.echo(f"Generated: {f}")


if __name__ == "__main__":
    main()

"""Click CLI for GeoPipeAgent."""

from __future__ import annotations

import json
import sys

import click

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
def run(file: str, log_level: str, json_log: bool):
    """Run a YAML pipeline file."""
    setup_logging(level=log_level, json_format=json_log)

    from geopipe_agent.steps import load_builtin_steps
    from geopipe_agent.engine.parser import parse_yaml
    from geopipe_agent.engine.validator import validate_pipeline
    from geopipe_agent.engine.executor import execute_pipeline
    from geopipe_agent.errors import GeopipeAgentError

    try:
        load_builtin_steps()
        pipeline = parse_yaml(file)
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
def backends():
    """List available GIS backends and their status."""
    from geopipe_agent.backends import BackendManager

    manager = BackendManager()
    result = manager.list_available()

    # Also check unavailable backends
    from geopipe_agent.backends import GdalPythonBackend, GdalCliBackend, QgisProcessBackend

    all_backends = [GdalPythonBackend(), GdalCliBackend(), QgisProcessBackend()]
    full_list = []
    for b in all_backends:
        full_list.append({"name": b.name(), "available": b.is_available()})

    click.echo(json.dumps(full_list, indent=2))


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

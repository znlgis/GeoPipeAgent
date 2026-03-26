"""Skill document and reference generator.

Generates Markdown documentation from registered steps for AI consumption.
"""

from __future__ import annotations

from pathlib import Path

from geopipe_agent.steps import registry


def generate_steps_reference() -> str:
    """Generate a Markdown reference of all registered steps.

    Returns:
        Markdown string documenting all steps.
    """
    lines = [
        "# GeoPipeAgent Steps Reference",
        "",
        "Auto-generated reference of all available pipeline steps.",
        "",
    ]

    for category in registry.categories():
        lines.append(f"## {category}")
        lines.append("")

        for info in registry.list_by_category(category):
            lines.append(f"### `{info.id}`")
            lines.append("")
            lines.append(f"**{info.name}** — {info.description}")
            lines.append("")

            if info.params:
                lines.append("**Parameters:**")
                lines.append("")
                lines.append("| Name | Type | Required | Default | Description |")
                lines.append("|------|------|----------|---------|-------------|")
                for pname, pinfo in info.params.items():
                    req = "✅" if pinfo.get("required", False) else "❌"
                    default = pinfo.get("default", "—")
                    desc = pinfo.get("description", "")
                    ptype = pinfo.get("type", "")
                    if "enum" in pinfo:
                        desc += f" (options: {', '.join(pinfo['enum'])})"
                    lines.append(f"| `{pname}` | {ptype} | {req} | {default} | {desc} |")
                lines.append("")

            if info.outputs:
                lines.append("**Outputs:**")
                lines.append("")
                for oname, oinfo in info.outputs.items():
                    lines.append(f"- `{oname}` ({oinfo.get('type', '')}): {oinfo.get('description', '')}")
                lines.append("")

            if info.examples:
                lines.append("**Examples:**")
                lines.append("")
                for ex in info.examples:
                    lines.append(f"- {ex.get('description', '')}: `{ex.get('params', {})}`")
                lines.append("")

            if info.backends:
                lines.append(f"**Backends:** {', '.join(info.backends)}")
                lines.append("")

            lines.append("---")
            lines.append("")

    return "\n".join(lines)


def generate_pipeline_schema_doc() -> str:
    """Generate Markdown documentation for the YAML pipeline schema."""
    return """# GeoPipeAgent Pipeline YAML Schema

## Top-level Structure

```yaml
pipeline:
  name: "Pipeline Name"            # Required: pipeline name
  description: "Description"       # Optional: pipeline description
  crs: "EPSG:4326"                # Optional: default CRS
  variables:                       # Optional: reusable variables
    var_name: value
  steps:                           # Required: list of steps
    - id: step_id                  # Required: unique step identifier [a-z0-9_-]
      use: category.action         # Required: step registry ID
      params:                      # Step-specific parameters
        key: value
      on_error: fail               # Optional: fail/skip/retry (default: fail)
      when: "$step_id.issues_count > 0"  # Optional: conditional execution
      backend: native_python           # Optional: specific backend to use
   outputs:                         # Optional: pipeline output declarations
     result: "$step_id.output"
```

## Reference Syntax

| Syntax | Description | Example |
|--------|-------------|---------|
| `$step_id` | Shorthand for `$step_id.output` | `$buffer` |
| `$step_id.output` | Reference step output | `$buffer.output` |
| `$step_id.stats` | Reference step stats | `$buffer.stats` |
| `$step_id.<key>` | Reference stats/metadata key | `$buffer.feature_count` |
| `${var_name}` | Variable substitution | `${input_path}` |

## Step ID Rules

- Only lowercase letters, digits, underscores, and hyphens: `[a-z0-9_-]`
- No dots (`.`) — dots are reserved for attribute access in references
- Must be unique within a pipeline

## Conditional Execution (``when``)

Steps can include a ``when`` expression to control execution:

```yaml
- id: fix-geometries
  use: qc.geometry_validity
  params:
    input: "$data"
    auto_fix: true
  when: "$check.issues_count > 0"
```

Supported syntax:
- Comparisons: ``$step.attr == value``, ``!=``, ``>``, ``<``, ``>=``, ``<=``
- Boolean operators: ``and``, ``or``, ``not``
- Variable substitution: ``${var_name}``
- Truthy check: ``$step_id.output`` (true if output is non-empty)

## Error Handling

Each step can specify `on_error`:
- `fail` (default): Stop pipeline execution
- `skip`: Skip this step, continue with next
- `retry`: Retry the step up to 3 times with backoff
"""


def generate_skill_file() -> str:
    """Generate the main SKILL.md file for AI consumption."""
    return """# GeoPipeAgent Skill

## What is GeoPipeAgent?

GeoPipeAgent is an AI-native GIS analysis pipeline framework. You (AI) can generate YAML pipeline files to perform GIS analysis tasks, and the framework will execute them and return structured JSON reports.

## How to Use

1. **Understand the task**: What GIS analysis does the user need?
2. **Choose steps**: Refer to `reference/steps-reference.md` for available steps
3. **Write YAML pipeline**: Generate a pipeline YAML following `reference/pipeline-schema.md`
4. **Execute**: Run `geopipe-agent run <pipeline.yaml>`
5. **Interpret results**: Parse the JSON execution report

## Quick Example

```yaml
pipeline:
  name: "Buffer Analysis"
  steps:
    - id: read
      use: io.read_vector
      params:
        path: "data/roads.shp"
    - id: buffer
      use: vector.buffer
      params:
        input: "$read"
        distance: 500
    - id: save
      use: io.write_vector
      params:
        input: "$buffer"
        path: "output/buffer_result.geojson"
  outputs:
    result: "$save"
```

## Key Concepts

- **Steps** are identified by `category.action` (e.g., `io.read_vector`, `vector.buffer`)
- **Step references** use `$step_id` (shorthand for `$step_id.output`) or `$step_id.attribute` (e.g., `$buffer.feature_count`)
- **Variables** use `${var_name}` syntax
- **IO steps** (io.*) read/write files directly; **analysis steps** use GIS backends

## Available Step Categories

- `io.*` — Data I/O (read/write vector and raster)
- `vector.*` — Vector analysis (buffer, clip, reproject, dissolve, simplify, query, overlay)
- `raster.*` — Raster analysis (reproject, clip, calc, stats, contour)
- `analysis.*` — Advanced analysis (voronoi, heatmap, interpolate, cluster)
- `network.*` — Network analysis (shortest_path, service_area, geocode)
- `qc.*` — Data quality check (geometry_validity, topology, attribute_completeness, attribute_domain, value_range, duplicate_check, crs_check, raster_nodata, raster_value_range, raster_resolution)

## QC (Quality Check) Steps

QC steps follow a **"Check and Passthrough"** pattern:
- Input data is passed through unchanged as `output`
- Issues are collected in `$step.issues` and problem features in `$step.issues_gdf`
- Multiple QC steps can be chained: `qc.check1 → qc.check2 → qc.check3`
- Pipeline reports include a `qc_summary` section aggregating all issues

## Files

- `reference/steps-reference.md` — Complete step parameter reference
- `reference/pipeline-schema.md` — YAML pipeline schema documentation
- `cookbook/` — Example pipeline YAML files
"""


def write_skill_files(output_dir: str | Path) -> list[str]:
    """Generate and write all skill files to the output directory.

    Returns:
        List of generated file paths.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    files = []

    # Main skill file
    skill_path = output_dir / "SKILL.md"
    skill_path.write_text(generate_skill_file(), encoding="utf-8")
    files.append(str(skill_path))

    # Reference directory
    ref_dir = output_dir / "reference"
    ref_dir.mkdir(parents=True, exist_ok=True)

    steps_ref_path = ref_dir / "steps-reference.md"
    steps_ref_path.write_text(generate_steps_reference(), encoding="utf-8")
    files.append(str(steps_ref_path))

    schema_path = ref_dir / "pipeline-schema.md"
    schema_path.write_text(generate_pipeline_schema_doc(), encoding="utf-8")
    files.append(str(schema_path))

    return files

# GeoPipeAgent

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**[English](#english)**

GeoPipeAgent 是一个 **AI 优先** 的 GIS 数据分析流水线框架。
AI 通过 Skill 文件理解框架能力，生成 YAML 格式的分析流水线，框架解析并执行，返回 JSON 结构化报告。

```
AI 生成 YAML 流水线 → GeoPipeAgent 解析 & 执行 → JSON 结构化报告
```

---

## ✨ 特性

- **YAML 驱动** — 用声明式 YAML 定义 GIS 分析流程，无需编写代码
- **AI 原生** — 自动生成 Skill 文件，让 AI 理解并生成流水线
- **33 个内置步骤** — 覆盖 IO、矢量、栅格、空间分析、网络分析、数据质检六大类
- **多后端支持** — 七种后端可切换：Native Python (GeoPandas)、GDAL CLI、GDAL Python、QGIS Process、PyQGIS、Generic CLI、Curl API
- **变量 & 引用** — 支持 `${var}` 变量替换和 `$step.attr` 步骤间数据引用
- **高级流水线控制** — `when` 条件执行、`retry` 自动重试、`on_error` 错误策略
- **JSON 报告** — 每次执行生成结构化 JSON 报告，便于 AI 解析和后续处理

---

## 🚀 快速开始

### 安装

```bash
# 基础安装
pip install -e .

# 安装全部可选依赖（空间分析 + 网络分析 + 开发工具）
pip install -e ".[dev,analysis,network]"
```

可选依赖组说明：

| 依赖组 | 包含 | 用途 |
|--------|------|------|
| `dev` | pytest, pytest-cov | 开发与测试 |
| `analysis` | scipy, scikit-learn, matplotlib | 空间分析步骤（泰森多边形、热力图、插值、聚类） |
| `network` | networkx, geopy | 网络分析步骤（最短路径、服务区、地理编码） |

### 运行第一个流水线

**1. 编写 YAML 流水线文件** `my-pipeline.yaml`：

```yaml
name: 缓冲区分析
description: 对道路数据做缓冲区分析

variables:
  input_path: "data/roads.shp"
  buffer_dist: 500

steps:
  - id: load-roads
    use: io.read_vector
    params:
      path: ${input_path}

  - id: reproject
    use: vector.reproject
    params:
      input: $load-roads
      target_crs: "EPSG:3857"

  - id: buffer
    use: vector.buffer
    params:
      input: $reproject
      distance: ${buffer_dist}
      cap_style: round

  - id: save
    use: io.write_vector
    params:
      input: $buffer
      path: "output/roads_buffer.geojson"
      driver: GeoJSON

outputs:
  result: $save
```

**2. 执行流水线**：

```bash
geopipe-agent run my-pipeline.yaml
```

执行后将输出 JSON 格式的结构化报告，包含每个步骤的执行结果和统计信息。

---

## 📖 使用指南

### CLI 命令

| 命令 | 说明 | 示例 |
|------|------|------|
| `geopipe-agent run <file>` | 执行 YAML 流水线 | `geopipe-agent run pipeline.yaml` |
| `geopipe-agent run <file> --var key=value` | 覆盖流水线变量 | `geopipe-agent run pipeline.yaml --var input_path=roads.shp` |
| `geopipe-agent run <file> --log-level DEBUG` | 指定日志级别 | `geopipe-agent run pipeline.yaml --log-level DEBUG` |
| `geopipe-agent run <file> --json-log` | 输出 JSON 格式日志 | `geopipe-agent run pipeline.yaml --json-log` |
| `geopipe-agent validate <file>` | 校验 YAML 流水线（不执行） | `geopipe-agent validate pipeline.yaml` |
| `geopipe-agent list-steps` | 列出所有可用步骤 | `geopipe-agent list-steps --category qc --format json` |
| `geopipe-agent describe <step_id>` | 查看步骤详情 | `geopipe-agent describe vector.buffer` |
| `geopipe-agent info <file>` | 查看 GIS 数据文件摘要 | `geopipe-agent info data/roads.shp` |
| `geopipe-agent backends` | 列出可用后端 | `geopipe-agent backends` |
| `geopipe-agent generate-skill-doc` | 生成步骤参考文档 | `geopipe-agent generate-skill-doc` |
| `geopipe-agent generate-skill` | 生成 AI Skill 文件集 | `geopipe-agent generate-skill --output-dir skills/` |

### YAML 流水线格式

```yaml
name: 流水线名称          # 必填
description: 流水线描述    # 可选
crs: "EPSG:4326"         # 可选，默认 CRS

variables:                # 可选，定义可复用变量
  var_name: value

steps:                    # 必填，步骤列表
  - id: step-id           # 必填，唯一标识 [a-z0-9_-]
    use: category.action  # 必填，步骤类型（如 io.read_vector）
    params:               # 步骤参数
      key: value
    when: "条件表达式"     # 可选，条件执行
    on_error: fail        # 可选，错误策略：fail / skip / retry
    backend: gdal_python  # 可选，指定后端

outputs:                  # 可选，输出声明
  result: $step-id
```

### 变量与引用

**变量替换** — 用 `${var}` 引用 `variables` 中定义的值：

```yaml
variables:
  input_path: "data/roads.shp"

steps:
  - id: load
    use: io.read_vector
    params:
      path: ${input_path}    # → "data/roads.shp"
```

**步骤引用** — 用 `$step-id` 引用前一个步骤的输出，用 `$step-id.attr` 引用具体属性：

```yaml
steps:
  - id: load
    use: io.read_vector
    params:
      path: "data/roads.shp"

  - id: buffer
    use: vector.buffer
    params:
      input: $load           # 引用 load 步骤的输出
      distance: 500
```

### 高级特性

**条件执行 (`when`)**：

```yaml
- id: optional-step
  use: vector.simplify
  params:
    input: $previous
    tolerance: 10
  when: "${simplify} == true"   # 仅当变量 simplify 为 true 时执行
```

**自动重试 (`retry`)**：

```yaml
- id: flaky-step
  use: network.geocode
  params:
    address: "北京市天安门"
  on_error: retry              # 失败时自动重试（最多 3 次）
```

**错误跳过 (`skip`)**：

```yaml
- id: optional-step
  use: vector.clip
  params:
    input: $data
    clip: $boundary
  on_error: skip               # 失败时跳过，继续执行后续步骤
```

---

## 📦 内置步骤

### IO 步骤

| 步骤 ID | 名称 | 说明 |
|---------|------|------|
| `io.read_vector` | 读取矢量数据 | 支持 Shapefile、GeoJSON、GPKG 等 |
| `io.write_vector` | 写入矢量数据 | 支持多种输出格式，自动创建目录 |
| `io.read_raster` | 读取栅格数据 | 读取 GeoTIFF 等，返回数据 + 元信息 |
| `io.write_raster` | 写入栅格数据 | 写入 GeoTIFF |

### 矢量步骤

| 步骤 ID | 名称 | 说明 |
|---------|------|------|
| `vector.buffer` | 缓冲区分析 | 支持 round/flat/square 端点样式 |
| `vector.clip` | 矢量裁剪 | 用裁剪范围裁剪输入数据 |
| `vector.reproject` | 投影转换 | CRS 坐标系转换 |
| `vector.dissolve` | 融合 | 按字段融合，支持聚合函数 |
| `vector.simplify` | 几何简化 | Douglas-Peucker 算法简化 |
| `vector.query` | 属性查询 | Pandas query 表达式过滤 |
| `vector.overlay` | 叠加分析 | intersection / union / difference 等 |

### 栅格步骤

| 步骤 ID | 名称 | 说明 |
|---------|------|------|
| `raster.reproject` | 栅格投影转换 | 使用 rasterio warp |
| `raster.clip` | 栅格裁剪 | 使用 rasterio mask |
| `raster.calc` | 栅格计算 | numpy 波段数学运算（如 NDVI） |
| `raster.stats` | 栅格统计 | min/max/mean/std 统计 |
| `raster.contour` | 生成等值线 | 从栅格提取等值线为矢量 |

### 空间分析步骤

> 需要安装 `[analysis]` 可选依赖：`pip install -e ".[analysis]"`

| 步骤 ID | 名称 | 说明 |
|---------|------|------|
| `analysis.voronoi` | 泰森多边形 | scipy Voronoi + shapely |
| `analysis.heatmap` | 热力图 | KDE 核密度估计 |
| `analysis.interpolate` | 空间插值 | griddata / IDW 插值 |
| `analysis.cluster` | 空间聚类 | DBSCAN / KMeans 聚类 |

### 网络分析步骤

> 需要安装 `[network]` 可选依赖：`pip install -e ".[network]"`

| 步骤 ID | 名称 | 说明 |
|---------|------|------|
| `network.shortest_path` | 最短路径 | networkx 图论最短路径 |
| `network.service_area` | 服务区分析 | 等时圈 / 等距圈分析 |
| `network.geocode` | 地理编码 | 地址转坐标（Nominatim） |

### 数据质检步骤

| 步骤 ID | 名称 | 说明 |
|---------|------|------|
| `qc.geometry_validity` | 几何有效性检查 | 检测自相交、空几何、环方向错误等 |
| `qc.crs_check` | 坐标参考系检查 | 验证 CRS 是否正确、是否缺失 |
| `qc.topology` | 拓扑关系检查 | 检测缝隙、重叠、悬挂线等问题 |
| `qc.attribute_completeness` | 属性完整性检查 | 检查必填字段是否缺失或为空 |
| `qc.attribute_domain` | 属性值域检查 | 检查字段值是否在允许范围内（枚举/正则） |
| `qc.value_range` | 数值范围检查 | 检查数值字段是否在指定范围内 |
| `qc.duplicate_check` | 重复要素检查 | 检测几何或属性重复的要素 |
| `qc.raster_nodata` | NoData 一致性检查 | 检查 NoData 值设置及像元比例 |
| `qc.raster_resolution` | 分辨率一致性检查 | 检查像元大小是否符合预期 |
| `qc.raster_value_range` | 栅格值域检查 | 检查像素值是否在预期范围内 |

---

## 📁 Cookbook 示例

`cookbook/` 目录提供了 7 个即用型流水线示例：

| 文件 | 说明 |
|------|------|
| [`buffer-analysis.yaml`](cookbook/buffer-analysis.yaml) | 缓冲区分析：读取 → 投影转换 → 缓冲 → 保存 |
| [`overlay-analysis.yaml`](cookbook/overlay-analysis.yaml) | 叠加分析：两图层求交集 |
| [`batch-convert.yaml`](cookbook/batch-convert.yaml) | 批量转换：Shapefile → GeoJSON + 投影转换 |
| [`filter-simplify.yaml`](cookbook/filter-simplify.yaml) | 属性筛选 + 几何简化 |
| [`dissolve-analysis.yaml`](cookbook/dissolve-analysis.yaml) | 按属性融合分析 |
| [`vector-qc.yaml`](cookbook/vector-qc.yaml) | 矢量数据质检：几何有效性 + 属性完整性 + 拓扑检查 |
| [`raster-qc.yaml`](cookbook/raster-qc.yaml) | 栅格数据质检：NoData + 值域 + 分辨率检查 |

```bash
# 运行示例
geopipe-agent run cookbook/buffer-analysis.yaml
```

---

## 🤖 AI 集成

GeoPipeAgent 通过 **Skill 文件** 与外部 AI 助手集成。

### Skill 文件生成

```bash
# 生成完整 Skill 文件集到指定目录
geopipe-agent generate-skill --output-dir skills/geopipe-agent

# 生成的文件：
# skills/geopipe-agent/SKILL.md              — 主技能描述
# skills/geopipe-agent/reference/steps-reference.md  — 完整步骤参考
# skills/geopipe-agent/reference/pipeline-schema.md  — YAML 流水线 Schema
```

```bash
# 快速查看步骤参考文档
geopipe-agent generate-skill-doc
```

### AI 工作流

**Skill 文件 + 外部 AI 工作流**

1. 将 Skill 文件提供给 AI（ChatGPT、Claude 等）
2. 用自然语言描述分析需求（如"对道路做 500 米缓冲区分析"）
3. AI 生成 YAML 流水线
4. GeoPipeAgent 执行流水线，返回 JSON 报告
5. AI 解读报告，给出分析结论

---

## 🔧 开发

### 添加自定义步骤

使用 `@step` 装饰器注册新步骤：

```python
from geopipe_agent import step, StepContext, StepResult

@step(
    name="my_custom_step",
    category="vector",
    description="自定义矢量处理步骤",
    params={
        "input": {"type": "GeoDataFrame", "required": True, "desc": "输入数据"},
        "param1": {"type": "float", "required": False, "default": 1.0, "desc": "参数1"},
    },
    outputs={"output": "GeoDataFrame"},
)
def my_custom_step(ctx: StepContext) -> StepResult:
    gdf = ctx.param("input")
    param1 = ctx.param("param1", default=1.0)
    # 处理逻辑...
    return StepResult(output=gdf, stats={"feature_count": len(gdf)})
```

然后将步骤文件放入 `src/geopipe_agent/steps/` 对应的子目录中，框架会通过 `pkgutil.walk_packages` 自动发现并注册。

### 运行测试

```bash
# 安装开发依赖
pip install -e ".[dev,analysis,network]"

# 运行测试
python -m pytest -v

# 运行带覆盖率报告的测试
python -m pytest -v --cov=geopipe_agent
```

### 多后端支持

| 后端 | 实现 | 要求 |
|------|------|------|
| `native_python` | GeoPandas + Shapely（默认） | pip 安装即可 |
| `gdal_cli` | ogr2ogr 命令行 | 需安装 GDAL CLI 工具 |
| `gdal_python` | GDAL/OGR Python 绑定 | 需安装 GDAL Python (`osgeo`) |
| `qgis_process` | QGIS Processing CLI | 需安装 QGIS |
| `pyqgis` | PyQGIS (QGIS Python API) | 需安装 QGIS Python 绑定 |
| `generic_cli` | 任意命令行命令 | 无额外依赖 |
| `curl_api` | HTTP 请求（通过 curl） | 需安装 curl |

```bash
# 查看可用后端
geopipe-agent backends

# 在流水线中指定后端
# steps:
#   - id: my-step
#     use: vector.buffer
#     params: { input: $data, distance: 100 }
#     backend: gdal_cli
```

---

## 🏗️ 项目架构

```
GeoPipeAgent/
├── src/geopipe_agent/           # 核心 Python 库
│   ├── __init__.py              # 包入口，自动加载所有内置步骤
│   ├── cli.py                   # Click CLI 命令行接口
│   ├── errors.py                # 自定义异常类
│   ├── backends/                # 多后端实现
│   │   ├── base.py              # 后端抽象基类
│   │   ├── native_python_backend.py  # GeoPandas + Shapely
│   │   ├── gdal_cli.py          # GDAL CLI (ogr2ogr)
│   │   ├── gdal_python_backend.py    # GDAL/OGR Python 绑定
│   │   ├── qgis_process.py      # QGIS Processing CLI
│   │   ├── pyqgis_backend.py    # PyQGIS Python API
│   │   ├── generic_cli_backend.py    # 任意 CLI 命令
│   │   └── curl_api_backend.py  # HTTP 请求（curl）
│   ├── engine/                  # 流水线引擎
│   │   ├── parser.py            # YAML 解析
│   │   ├── validator.py         # 流水线校验
│   │   ├── executor.py          # 步骤执行
│   │   ├── context.py           # 上下文 & 变量解析
│   │   └── reporter.py          # JSON 报告生成
│   ├── models/                  # 数据模型
│   │   ├── pipeline.py          # PipelineDefinition, StepDefinition
│   │   ├── result.py            # StepResult
│   │   └── qc.py                # QcIssue
│   ├── steps/                   # 内置步骤（自动发现 & 注册）
│   │   ├── registry.py          # 步骤注册表 & @step 装饰器
│   │   ├── io/                  # 数据读写（4 个步骤）
│   │   ├── vector/              # 矢量处理（7 个步骤）
│   │   ├── raster/              # 栅格处理（5 个步骤）
│   │   ├── analysis/            # 空间分析（4 个步骤）
│   │   ├── network/             # 网络分析（3 个步骤）
│   │   └── qc/                  # 数据质检（10 个步骤）
│   ├── skillgen/                # AI Skill 文件生成器
│   │   └── generator.py
│   └── utils/                   # 工具函数
│       ├── logging.py           # 结构化日志
│       └── safe_eval.py         # 安全表达式求值（AST 白名单）
├── cookbook/                    # 示例流水线
└── pyproject.toml               # 项目配置
```

---

## 📄 许可证

[MIT License](LICENSE)

---

<a id="english"></a>

# GeoPipeAgent (English)

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**[中文](#geopipeagent)**

GeoPipeAgent is an **AI-native** GIS data analysis pipeline framework.
AI understands the framework's capabilities through Skill files, generates YAML analysis pipelines, which the framework parses and executes, returning structured JSON reports.

```
AI generates YAML pipeline → GeoPipeAgent parses & executes → Structured JSON report
```

---

## ✨ Features

- **YAML-driven** — Define GIS analysis workflows declaratively in YAML, no coding required
- **AI-native** — Auto-generates Skill files for AI to understand and generate pipelines
- **33 built-in steps** — Covers IO, vector, raster, spatial analysis, network analysis, and data quality checks
- **Multi-backend** — Seven backends: Native Python (GeoPandas), GDAL CLI (ogr2ogr), GDAL Python, QGIS Process, PyQGIS, Generic CLI, and Curl API
- **Variables & references** — `${var}` variable substitution and `$step.attr` inter-step data references
- **Advanced pipeline control** — `when` conditional execution, `retry` auto-retry, `on_error` error strategies
- **JSON reports** — Structured JSON reports for every execution, easy for AI to parse

---

## 🚀 Quick Start

### Installation

```bash
# Basic install
pip install -e .

# Install with all optional dependencies (spatial analysis + network + dev tools)
pip install -e ".[dev,analysis,network]"
```

Optional dependency groups:

| Group | Includes | Purpose |
|-------|----------|---------|
| `dev` | pytest, pytest-cov | Development and testing |
| `analysis` | scipy, scikit-learn, matplotlib | Spatial analysis steps (Voronoi, heatmap, interpolation, clustering) |
| `network` | networkx, geopy | Network analysis steps (shortest path, service area, geocoding) |

### Run Your First Pipeline

**1. Create a YAML pipeline file** `my-pipeline.yaml`:

```yaml
name: Buffer Analysis
description: Buffer analysis on road data

variables:
  input_path: "data/roads.shp"
  buffer_dist: 500

steps:
  - id: load-roads
    use: io.read_vector
    params:
      path: ${input_path}

  - id: reproject
    use: vector.reproject
    params:
      input: $load-roads
      target_crs: "EPSG:3857"

  - id: buffer
    use: vector.buffer
    params:
      input: $reproject
      distance: ${buffer_dist}
      cap_style: round

  - id: save
    use: io.write_vector
    params:
      input: $buffer
      path: "output/roads_buffer.geojson"
      driver: GeoJSON

outputs:
  result: $save
```

**2. Execute the pipeline**:

```bash
geopipe-agent run my-pipeline.yaml
```

The output is a structured JSON report with execution results and statistics for each step.

---

## 📖 Usage Guide

### CLI Commands

| Command | Description | Example |
|---------|-------------|---------|
| `geopipe-agent run <file>` | Execute a YAML pipeline | `geopipe-agent run pipeline.yaml` |
| `geopipe-agent run <file> --var key=value` | Override pipeline variables | `geopipe-agent run pipeline.yaml --var input_path=roads.shp` |
| `geopipe-agent run <file> --log-level DEBUG` | Set log level | `geopipe-agent run pipeline.yaml --log-level DEBUG` |
| `geopipe-agent run <file> --json-log` | Output JSON-formatted logs | `geopipe-agent run pipeline.yaml --json-log` |
| `geopipe-agent validate <file>` | Validate a YAML pipeline (without executing) | `geopipe-agent validate pipeline.yaml` |
| `geopipe-agent list-steps` | List all available steps | `geopipe-agent list-steps --category qc --format json` |
| `geopipe-agent describe <step_id>` | Show step details | `geopipe-agent describe vector.buffer` |
| `geopipe-agent info <file>` | Show GIS data file summary | `geopipe-agent info data/roads.shp` |
| `geopipe-agent backends` | List available backends | `geopipe-agent backends` |
| `geopipe-agent generate-skill-doc` | Generate step reference docs | `geopipe-agent generate-skill-doc` |
| `geopipe-agent generate-skill` | Generate AI Skill file set | `geopipe-agent generate-skill --output-dir skills/` |

### YAML Pipeline Format

```yaml
name: Pipeline Name         # Required
description: Description    # Optional
crs: "EPSG:4326"           # Optional, default CRS

variables:                  # Optional, reusable variables
  var_name: value

steps:                      # Required, list of steps
  - id: step-id             # Required, unique identifier [a-z0-9_-]
    use: category.action    # Required, step type (e.g. io.read_vector)
    params:                 # Step parameters
      key: value
    when: "condition"       # Optional, conditional execution
    on_error: fail          # Optional, error strategy: fail / skip / retry
    backend: gdal_python    # Optional, specify backend

outputs:                    # Optional, output declarations
  result: $step-id
```

### Variables & References

**Variable substitution** — Use `${var}` to reference values defined in `variables`:

```yaml
variables:
  input_path: "data/roads.shp"

steps:
  - id: load
    use: io.read_vector
    params:
      path: ${input_path}    # → "data/roads.shp"
```

**Step references** — Use `$step-id` to reference a previous step's output, `$step-id.attr` for specific attributes:

```yaml
steps:
  - id: load
    use: io.read_vector
    params:
      path: "data/roads.shp"

  - id: buffer
    use: vector.buffer
    params:
      input: $load           # References load step's output
      distance: 500
```

### Advanced Features

**Conditional execution (`when`)**:

```yaml
- id: optional-step
  use: vector.simplify
  params:
    input: $previous
    tolerance: 10
  when: "${simplify} == true"   # Only executes when simplify variable is true
```

**Auto-retry (`retry`)**:

```yaml
- id: flaky-step
  use: network.geocode
  params:
    address: "Beijing Tiananmen"
  on_error: retry              # Retries automatically on failure (up to 3 times)
```

**Skip on error (`skip`)**:

```yaml
- id: optional-step
  use: vector.clip
  params:
    input: $data
    clip: $boundary
  on_error: skip               # Skips on failure, continues with remaining steps
```

---

## 📦 Built-in Steps

### IO Steps

| Step ID | Name | Description |
|---------|------|-------------|
| `io.read_vector` | Read Vector | Supports Shapefile, GeoJSON, GPKG, etc. |
| `io.write_vector` | Write Vector | Multiple output formats, auto-creates directories |
| `io.read_raster` | Read Raster | Reads GeoTIFF etc., returns data + metadata |
| `io.write_raster` | Write Raster | Writes GeoTIFF |

### Vector Steps

| Step ID | Name | Description |
|---------|------|-------------|
| `vector.buffer` | Buffer | Supports round/flat/square cap styles |
| `vector.clip` | Clip | Clips input data with clip extent |
| `vector.reproject` | Reproject | CRS coordinate system transformation |
| `vector.dissolve` | Dissolve | Dissolve by field with aggregation functions |
| `vector.simplify` | Simplify | Douglas-Peucker geometry simplification |
| `vector.query` | Query | Pandas query expression filtering |
| `vector.overlay` | Overlay | intersection / union / difference operations |

### Raster Steps

| Step ID | Name | Description |
|---------|------|-------------|
| `raster.reproject` | Reproject Raster | Using rasterio warp |
| `raster.clip` | Clip Raster | Using rasterio mask |
| `raster.calc` | Raster Calculator | numpy band math (e.g. NDVI) |
| `raster.stats` | Raster Statistics | min/max/mean/std statistics |
| `raster.contour` | Contour Lines | Extract contour lines from raster to vector |

### Spatial Analysis Steps

> Requires `[analysis]` optional dependencies: `pip install -e ".[analysis]"`

| Step ID | Name | Description |
|---------|------|-------------|
| `analysis.voronoi` | Voronoi Polygons | scipy Voronoi + shapely |
| `analysis.heatmap` | Heatmap | KDE kernel density estimation |
| `analysis.interpolate` | Interpolation | griddata / IDW interpolation |
| `analysis.cluster` | Clustering | DBSCAN / KMeans spatial clustering |

### Network Analysis Steps

> Requires `[network]` optional dependencies: `pip install -e ".[network]"`

| Step ID | Name | Description |
|---------|------|-------------|
| `network.shortest_path` | Shortest Path | networkx graph shortest path |
| `network.service_area` | Service Area | Isochrone / isodistance analysis |
| `network.geocode` | Geocode | Address to coordinates (Nominatim) |

### Data Quality Check Steps

| Step ID | Name | Description |
|---------|------|-------------|
| `qc.geometry_validity` | Geometry Validity | Detects self-intersections, empty geometries, ring direction errors |
| `qc.crs_check` | CRS Check | Verifies CRS is correct and present |
| `qc.topology` | Topology Check | Detects gaps, overlaps, and dangles |
| `qc.attribute_completeness` | Attribute Completeness | Checks required fields for missing or null values |
| `qc.attribute_domain` | Attribute Domain | Validates field values against allowed domains (enum/regex) |
| `qc.value_range` | Value Range | Checks numeric fields within min/max thresholds |
| `qc.duplicate_check` | Duplicate Check | Detects duplicate features by geometry or attributes |
| `qc.raster_nodata` | NoData Consistency | Checks NoData value settings and pixel ratio |
| `qc.raster_resolution` | Resolution Consistency | Verifies pixel size matches expected values |
| `qc.raster_value_range` | Raster Value Range | Checks pixel values within expected range |

---

## 📁 Cookbook Examples

The `cookbook/` directory provides 7 ready-to-use pipeline examples:

| File | Description |
|------|-------------|
| [`buffer-analysis.yaml`](cookbook/buffer-analysis.yaml) | Buffer analysis: read → reproject → buffer → save |
| [`overlay-analysis.yaml`](cookbook/overlay-analysis.yaml) | Overlay analysis: intersection of two layers |
| [`batch-convert.yaml`](cookbook/batch-convert.yaml) | Batch conversion: Shapefile → GeoJSON + reprojection |
| [`filter-simplify.yaml`](cookbook/filter-simplify.yaml) | Attribute filtering + geometry simplification |
| [`dissolve-analysis.yaml`](cookbook/dissolve-analysis.yaml) | Dissolve analysis by attribute |
| [`vector-qc.yaml`](cookbook/vector-qc.yaml) | Vector data QC: geometry validity + attribute completeness + topology |
| [`raster-qc.yaml`](cookbook/raster-qc.yaml) | Raster data QC: NoData + value range + resolution checks |

```bash
# Run an example
geopipe-agent run cookbook/buffer-analysis.yaml
```

---

## 🤖 AI Integration

GeoPipeAgent integrates with external AI assistants through **Skill files**.

### Skill File Generation

```bash
# Generate complete Skill file set to a directory
geopipe-agent generate-skill --output-dir skills/geopipe-agent

# Generated files:
# skills/geopipe-agent/SKILL.md                      — Main skill description
# skills/geopipe-agent/reference/steps-reference.md   — Complete step reference
# skills/geopipe-agent/reference/pipeline-schema.md   — YAML pipeline schema
```

```bash
# Quick preview of step reference docs
geopipe-agent generate-skill-doc
```

### AI Workflow

**Skill Files + External AI Workflow**

1. Provide Skill files to the AI (ChatGPT, Claude, etc.)
2. Describe your analysis in natural language (e.g. "Create a 500m buffer around roads")
3. AI generates a YAML pipeline
4. GeoPipeAgent executes the pipeline and returns a JSON report
5. AI interprets the report and provides analysis conclusions

---

## 🔧 Development

### Adding Custom Steps

Register new steps using the `@step` decorator:

```python
from geopipe_agent import step, StepContext, StepResult

@step(
    name="my_custom_step",
    category="vector",
    description="Custom vector processing step",
    params={
        "input": {"type": "GeoDataFrame", "required": True, "desc": "Input data"},
        "param1": {"type": "float", "required": False, "default": 1.0, "desc": "Parameter 1"},
    },
    outputs={"output": "GeoDataFrame"},
)
def my_custom_step(ctx: StepContext) -> StepResult:
    gdf = ctx.param("input")
    param1 = ctx.param("param1", default=1.0)
    # Processing logic...
    return StepResult(output=gdf, stats={"feature_count": len(gdf)})
```

Then place the step file in the corresponding subdirectory under `src/geopipe_agent/steps/`. The framework auto-discovers and registers steps via `pkgutil.walk_packages`.

### Running Tests

```bash
# Install dev dependencies
pip install -e ".[dev,analysis,network]"

# Run tests
python -m pytest -v

# Run tests with coverage report
python -m pytest -v --cov=geopipe_agent
```

### Multi-Backend Support

| Backend | Implementation | Requirements |
|---------|----------------|--------------|
| `native_python` | GeoPandas + Shapely (default) | pip install |
| `gdal_cli` | ogr2ogr CLI | GDAL CLI tools installed |
| `gdal_python` | GDAL/OGR Python bindings | GDAL Python (`osgeo`) installed |
| `qgis_process` | QGIS Processing CLI | QGIS installed |
| `pyqgis` | PyQGIS (QGIS Python API) | QGIS Python bindings installed |
| `generic_cli` | Arbitrary CLI commands | No extra dependencies |
| `curl_api` | HTTP requests via curl | curl installed |

```bash
# Check available backends
geopipe-agent backends

# Specify backend in a pipeline step:
# steps:
#   - id: my-step
#     use: vector.buffer
#     params: { input: $data, distance: 100 }
#     backend: gdal_cli
```

---

## 🏗️ Project Architecture

```
GeoPipeAgent/
├── src/geopipe_agent/           # Core Python library
│   ├── __init__.py              # Package entry, auto-loads all built-in steps
│   ├── cli.py                   # Click CLI interface
│   ├── errors.py                # Custom exception classes
│   ├── backends/                # Multi-backend implementations
│   │   ├── base.py              # Abstract backend base class
│   │   ├── native_python_backend.py  # GeoPandas + Shapely
│   │   ├── gdal_cli.py          # GDAL CLI (ogr2ogr)
│   │   ├── gdal_python_backend.py    # GDAL/OGR Python bindings
│   │   ├── qgis_process.py      # QGIS Processing CLI
│   │   ├── pyqgis_backend.py    # PyQGIS Python API
│   │   ├── generic_cli_backend.py    # Arbitrary CLI commands
│   │   └── curl_api_backend.py  # HTTP requests via curl
│   ├── engine/                  # Pipeline engine
│   │   ├── parser.py            # YAML parsing
│   │   ├── validator.py         # Pipeline validation
│   │   ├── executor.py          # Step execution
│   │   ├── context.py           # Context & variable resolution
│   │   └── reporter.py          # JSON report generation
│   ├── models/                  # Data models
│   │   ├── pipeline.py          # PipelineDefinition, StepDefinition
│   │   ├── result.py            # StepResult
│   │   └── qc.py                # QcIssue
│   ├── steps/                   # Built-in steps (auto-discovered & registered)
│   │   ├── registry.py          # Step registry & @step decorator
│   │   ├── io/                  # Data I/O (4 steps)
│   │   ├── vector/              # Vector processing (7 steps)
│   │   ├── raster/              # Raster processing (5 steps)
│   │   ├── analysis/            # Spatial analysis (4 steps)
│   │   ├── network/             # Network analysis (3 steps)
│   │   └── qc/                  # Data quality checks (10 steps)
│   ├── skillgen/                # AI Skill file generator
│   │   └── generator.py
│   └── utils/                   # Utilities
│       ├── logging.py           # Structured logging
│       └── safe_eval.py         # Safe expression evaluation (AST whitelist)
├── cookbook/                    # Example pipelines
└── pyproject.toml               # Project configuration
```

---

## 📄 License

[MIT License](LICENSE)

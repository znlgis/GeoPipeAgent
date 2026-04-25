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
pipeline:
  name: "缓冲区分析"
  description: "对道路数据做缓冲区分析"

  variables:
    input_path: "data/roads.shp"
    buffer_dist: 500

  steps:
    - id: load-roads
      use: io.read_vector
      params:
        path: "${input_path}"

    - id: reproject
      use: vector.reproject
      params:
        input: "$load-roads"
        target_crs: "EPSG:3857"

    - id: buffer
      use: vector.buffer
      params:
        input: "$reproject"
        distance: "${buffer_dist}"
        cap_style: "round"

    - id: save
      use: io.write_vector
      params:
        input: "$buffer"
        path: "output/roads_buffer.geojson"
        format: "GeoJSON"

  outputs:
    result: "$save"
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

> **注意**：所有内容必须放在顶层的 `pipeline:` 键下。

```yaml
pipeline:
  name: "流水线名称"        # 必填
  description: "流水线描述"  # 可选
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
    result: "$step-id"
```

### 变量与引用

**变量替换** — 用 `${var}` 引用 `variables` 中定义的值：

```yaml
pipeline:
  variables:
    input_path: "data/roads.shp"

  steps:
    - id: load
      use: io.read_vector
      params:
        path: "${input_path}"    # → "data/roads.shp"
```

**步骤引用** — 用 `$step-id` 引用前一个步骤的输出，用 `$step-id.attr` 引用具体属性：

```yaml
pipeline:
  steps:
    - id: load
      use: io.read_vector
      params:
        path: "data/roads.shp"

    - id: buffer
      use: vector.buffer
      params:
        input: "$load"           # 引用 load 步骤的输出
        distance: 500
```

### 高级特性

**条件执行 (`when`)**：

```yaml
pipeline:
  steps:
    - id: optional-step
      use: vector.simplify
      params:
        input: "$previous"
        tolerance: 10
      when: "${simplify} == true"   # 仅当变量 simplify 为 true 时执行
```

**自动重试 (`retry`)**：

```yaml
pipeline:
  steps:
    - id: flaky-step
      use: network.geocode
      params:
        address: "北京市天安门"
      on_error: retry              # 失败时自动重试（最多 3 次）
```

**错误跳过 (`skip`)**：

```yaml
pipeline:
  steps:
    - id: optional-step
      use: vector.clip
      params:
        input: "$data"
        clip: "$boundary"
      on_error: skip               # 失败时跳过，继续执行后续步骤
```

---

## 📦 内置步骤

### IO 步骤（4 个）

| 步骤 ID | 名称 | 说明 |
|---------|------|------|
| `io.read_vector` | 读取矢量数据 | 支持 Shapefile、GeoJSON、GPKG 等 |
| `io.write_vector` | 写入矢量数据 | 支持多种输出格式，自动创建目录 |
| `io.read_raster` | 读取栅格数据 | 读取 GeoTIFF 等，返回数据 + 元信息 |
| `io.write_raster` | 写入栅格数据 | 写入 GeoTIFF |

### 矢量步骤（7 个）

| 步骤 ID | 名称 | 说明 |
|---------|------|------|
| `vector.buffer` | 缓冲区分析 | 支持 round/flat/square 端点样式 |
| `vector.clip` | 矢量裁剪 | 用裁剪范围裁剪输入数据 |
| `vector.reproject` | 投影转换 | CRS 坐标系转换 |
| `vector.dissolve` | 融合 | 按字段融合，支持聚合函数 |
| `vector.simplify` | 几何简化 | Douglas-Peucker 算法简化 |
| `vector.query` | 属性查询 | Pandas query 表达式过滤 |
| `vector.overlay` | 叠加分析 | intersection / union / difference 等 |

### 栅格步骤（5 个）

| 步骤 ID | 名称 | 说明 |
|---------|------|------|
| `raster.reproject` | 栅格投影转换 | 使用 rasterio warp |
| `raster.clip` | 栅格裁剪 | 使用 rasterio mask |
| `raster.calc` | 栅格计算 | numpy 波段数学运算（如 NDVI） |
| `raster.stats` | 栅格统计 | min/max/mean/std 统计 |
| `raster.contour` | 生成等值线 | 从栅格提取等值线为矢量 |

### 空间分析步骤（4 个）

> 需要安装 `[analysis]` 可选依赖：`pip install -e ".[analysis]"`

| 步骤 ID | 名称 | 说明 |
|---------|------|------|
| `analysis.voronoi` | 泰森多边形 | scipy Voronoi + shapely |
| `analysis.heatmap` | 热力图 | KDE 核密度估计 |
| `analysis.interpolate` | 空间插值 | griddata / IDW 插值 |
| `analysis.cluster` | 空间聚类 | DBSCAN / KMeans 聚类 |

### 网络分析步骤（3 个）

> 需要安装 `[network]` 可选依赖：`pip install -e ".[network]"`

| 步骤 ID | 名称 | 说明 |
|---------|------|------|
| `network.shortest_path` | 最短路径 | networkx 图论最短路径 |
| `network.service_area` | 服务区分析 | 等时圈 / 等距圈分析 |
| `network.geocode` | 地理编码 | 地址转坐标（Nominatim） |

### 数据质检步骤（10 个）

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
    id="vector.my_custom_step",
    name="自定义矢量步骤",
    category="vector",
    description="自定义矢量处理步骤",
    params={
        "input": {"type": "geodataframe", "required": True, "description": "输入数据"},
        "param1": {"type": "float", "required": False, "default": 1.0, "description": "参数1"},
    },
    outputs={"output": {"type": "geodataframe", "description": "处理结果"}},
)
def my_custom_step(ctx: StepContext) -> StepResult:
    gdf = ctx.input("input")
    param1 = ctx.param("param1", default=1.0)
    # 处理逻辑...
    return StepResult(output=gdf, stats={"feature_count": len(gdf)})
```

然后将步骤文件放入 `src/geopipe_agent/steps/` 对应的子目录中，框架会通过 `pkgutil.walk_packages` 自动发现并注册。

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
# pipeline:
#   steps:
#     - id: my-step
#       use: vector.buffer
#       params: { input: "$data", distance: 100 }
#       backend: gdal_cli
```

### 运行测试

```bash
# 安装开发依赖
pip install -e ".[dev,analysis,network]"

# 运行测试
python -m pytest -v

# 运行带覆盖率报告的测试
python -m pytest -v --cov=geopipe_agent
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
│   │   ├── base.py              # 后端抽象基类（含默认 NotImplemented 实现）
│   │   ├── native_python_backend.py  # GeoPandas + Shapely
│   │   ├── gdal_cli.py          # GDAL CLI (ogr2ogr)
│   │   ├── gdal_python_backend.py    # GDAL/OGR Python 绑定
│   │   ├── qgis_process.py      # QGIS Processing CLI
│   │   ├── pyqgis_backend.py    # PyQGIS Python API
│   │   ├── generic_cli_backend.py    # 任意 CLI 命令
│   │   └── curl_api_backend.py  # HTTP 请求（curl）
│   ├── engine/                  # 流水线引擎
│   │   ├── parser.py            # YAML 解析（需 pipeline: 顶层键）
│   │   ├── validator.py         # 流水线校验（ID 格式、引用完整性）
│   │   ├── executor.py          # 步骤执行（含 when/retry/skip 控制）
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
│       ├── logging.py           # 结构化日志（支持 JSON 格式）
│       └── safe_eval.py         # 安全表达式求值（AST 白名单）
├── cookbook/                    # 示例流水线（7 个）
└── pyproject.toml               # 项目配置
```

---

## 📄 许可证

[MIT License](LICENSE)

---

<a id="english"></a>

# GeoPipeAgent (English)

**[中文文档](#geopipeagent)**

GeoPipeAgent is an **AI-native** GIS data analysis pipeline framework.
AI generates YAML pipelines → GeoPipeAgent executes → structured JSON reports.

## Quick Start

```bash
pip install -e ".[dev,analysis,network]"
geopipe-agent run cookbook/buffer-analysis.yaml
```

## YAML Pipeline Format

All content must be wrapped in a top-level `pipeline:` key:

```yaml
pipeline:
  name: "Pipeline Name"
  steps:
    - id: step-id
      use: category.action       # e.g. io.read_vector, vector.buffer
      params:
        key: value
      on_error: fail             # fail / skip / retry
      when: "${cond} == true"    # Conditional execution
  outputs:
    result: "$step-id"
```

## Reference Syntax

| Syntax | Meaning |
|--------|---------|
| `$step_id` | Shorthand for `$step_id.output` |
| `$step_id.attr` | Access step result attribute |
| `${var_name}` | Variable substitution |

## CLI Commands

| Command | Description |
|---------|-------------|
| `geopipe-agent run <file>` | Execute a YAML pipeline |
| `geopipe-agent validate <file>` | Validate a pipeline |
| `geopipe-agent list-steps` | List all available steps |
| `geopipe-agent describe <id>` | Show step details |
| `geopipe-agent info <file>` | Show GIS file summary |
| `geopipe-agent backends` | List available backends |
| `geopipe-agent generate-skill-doc` | Generate step reference docs |
| `geopipe-agent generate-skill` | Generate AI Skill files |

## Steps Reference

| Category | Count | Example IDs |
|----------|-------|-------------|
| `io` | 4 | `io.read_vector`, `io.write_vector`, `io.read_raster`, `io.write_raster` |
| `vector` | 7 | `vector.buffer`, `vector.clip`, `vector.reproject`, `vector.dissolve`, `vector.simplify`, `vector.query`, `vector.overlay` |
| `raster` | 5 | `raster.reproject`, `raster.clip`, `raster.calc`, `raster.stats`, `raster.contour` |
| `analysis` | 4 | `analysis.voronoi`, `analysis.heatmap`, `analysis.interpolate`, `analysis.cluster` |
| `network` | 3 | `network.shortest_path`, `network.service_area`, `network.geocode` |
| `qc` | 10 | `qc.geometry_validity`, `qc.topology`, `qc.attribute_completeness`, `qc.duplicate_check`, `qc.crs_check`, `qc.*` |

> Full step reference: `geopipe-agent generate-skill-doc`

## License

[MIT License](LICENSE)

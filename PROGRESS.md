# GeoPipeAgent 实现进度文档

> 本文档记录 GeoPipeAgent 框架的实现进度，方便后续开发者继续未完成的部分。

## 总体进度

| 模块 | 状态 | 说明 |
|------|------|------|
| 项目结构 | ✅ 完成 | pyproject.toml、包结构、依赖配置 |
| 错误处理 | ✅ 完成 | 全部异常类 + AI 友好错误信息 |
| 数据模型 | ✅ 完成 | Pipeline、StepDefinition、StepResult |
| Step 插件系统 | ✅ 完成 | 注册表、@step 装饰器、StepContext |
| Backend 系统 | ✅ 完成 | 抽象基类 + GdalPythonBackend（功能完整）+ CLI/QGIS 占位 |
| Engine 核心 | ✅ 完成 | Parser、Validator、Resolver、Executor、Context、Reporter |
| CLI | ✅ 完成 | run、backends、generate-skill-doc、generate-skill 命令 |
| IO Steps | ✅ 完成 | io.read_vector, io.write_vector, io.read_raster, io.write_raster |
| Vector Steps | ✅ 完成 | buffer, clip, reproject, dissolve, simplify, query, overlay |
| Skill 生成 | ✅ 完成 | 自动生成 SKILL.md、steps-reference.md、pipeline-schema.md |
| 测试 | ✅ 完成 | 66 个测试用例，全部通过 |
| Cookbook | ✅ 完成 | 5 个示例流水线 YAML |
| Raster Steps | ⬜ 未实现 | raster.reproject, raster.clip, raster.calc, raster.stats, raster.contour |
| Analysis Steps | ⬜ 未实现 | analysis.voronoi, analysis.heatmap, analysis.interpolate, analysis.cluster |
| Network Steps | ⬜ 未实现 | network.shortest_path, network.service_area, network.geocode |
| GDAL CLI Backend | ⬜ 未实现 | 方法均为 NotImplementedError 占位 |
| QGIS Process Backend | ⬜ 未实现 | 方法均为 NotImplementedError 占位 |
| 高级流水线特性 | ⬜ 未实现 | when 条件执行、retry 重试 |

---

## 已完成模块详情

### 1. 项目结构 (`pyproject.toml`)

- Python >= 3.10
- 依赖：click, pyyaml, geopandas, shapely, fiona, rasterio, jsonschema
- 入口点：`geopipe-agent` CLI
- 使用 setuptools 构建

### 2. 错误处理 (`src/geopipe_agent/errors.py`)

已实现的异常类：
- `GeopipeAgentError` — 基类
- `PipelineParseError` — YAML 解析错误
- `PipelineValidationError` — Schema 验证错误
- `StepExecutionError` — 步骤执行错误（含 `step_id`, `suggestion`, `cause`，支持 `to_dict()`)
- `BackendNotAvailableError` — 后端不可用
- `StepNotFoundError` — 步骤未找到
- `VariableResolutionError` — 变量/引用解析错误

### 3. 数据模型 (`src/geopipe_agent/models/`)

- `PipelineDefinition` — 流水线定义（name, steps, variables, outputs, crs）
- `StepDefinition` — 步骤定义（id, use, params, when, on_error, backend）
- `StepResult` — 步骤执行结果（output, stats, metadata），支持属性访问和 `summary()`

### 4. Step 插件系统 (`src/geopipe_agent/steps/`)

- `StepRegistry` — 单例注册表，支持注册、查询、按类别列出
- `@step` 装饰器 — 声明式注册步骤，自动推导 category
- `StepContext` — 步骤执行上下文，提供 `param()`, `input()`, `backend` 访问

### 5. Backend 系统 (`src/geopipe_agent/backends/`)

- `GeoBackend` — 抽象基类（buffer, clip, reproject, dissolve, simplify, overlay）
- `GdalPythonBackend` — ✅ 全部方法实现（使用 GeoPandas + Shapely）
- `GdalCliBackend` — 占位实现，`is_available()` 检测 ogr2ogr
- `QgisProcessBackend` — 占位实现，`is_available()` 检测 qgis_process
- `BackendManager` — 自动检测可用后端，支持按名称获取

### 6. Engine 核心 (`src/geopipe_agent/engine/`)

- `parser.py` — YAML 文件/字符串解析为 PipelineDefinition
- `validator.py` — step_id 格式校验、唯一性检查、注册表验证、引用合法性、变量定义检查
- `resolver.py` — 参数解析入口
- `context.py` — PipelineContext（变量替换 `${var}`、步骤引用 `$step.attr`、参数批量解析）
- `executor.py` — 顺序执行步骤、自动选择 Backend、on_error=skip 支持、AI 友好修复建议
- `reporter.py` — 生成 JSON 执行报告

### 7. CLI (`src/geopipe_agent/cli.py`)

| 命令 | 说明 |
|------|------|
| `geopipe-agent run <file>` | 执行 YAML 流水线，输出 JSON 报告 |
| `geopipe-agent backends` | 列出所有后端及可用状态 |
| `geopipe-agent generate-skill-doc` | 生成 Steps 参考文档（stdout） |
| `geopipe-agent generate-skill --output-dir <dir>` | 生成完整 Skill 文件集 |

### 8. 已实现的 Steps

| Step ID | 名称 | 类别 | 说明 |
|---------|------|------|------|
| `io.read_vector` | 读取矢量数据 | io | 支持 Shapefile, GeoJSON, GPKG 等 |
| `io.write_vector` | 写入矢量数据 | io | 支持多种输出格式，自动创建目录 |
| `io.read_raster` | 读取栅格数据 | io | 读取 GeoTIFF 等，返回数据+元信息 |
| `io.write_raster` | 写入栅格数据 | io | 写入 GeoTIFF |
| `vector.buffer` | 缓冲区分析 | vector | 支持 round/flat/square 端点样式 |
| `vector.clip` | 矢量裁剪 | vector | 用裁剪范围裁剪输入数据 |
| `vector.reproject` | 投影转换 | vector | CRS 转换 |
| `vector.dissolve` | 融合 | vector | 按字段融合，支持聚合函数 |
| `vector.simplify` | 简化 | vector | Douglas-Peucker 简化 |
| `vector.query` | 属性查询 | vector | Pandas query 表达式过滤 |
| `vector.overlay` | 叠加分析 | vector | intersection/union/difference 等 |

### 9. 测试 (`tests/`)

- `test_engine/test_parser.py` — 9 个测试（YAML 解析）
- `test_engine/test_validator.py` — 10 个测试（验证逻辑）
- `test_engine/test_context.py` — 12 个测试（上下文与变量解析）
- `test_engine/test_executor.py` — 5 个测试（端到端流水线执行）
- `test_steps/test_registry.py` — 9 个测试（注册表与装饰器）
- `test_steps/test_io_steps.py` — 4 个测试（IO 步骤）
- `test_steps/test_vector_steps.py` — 8 个测试（矢量步骤）
- `test_backends/test_gdal_python.py` — 9 个测试（GdalPython 后端）
- **共计 66 个测试，全部通过**

### 10. Cookbook (`cookbook/`)

| 文件 | 说明 |
|------|------|
| `buffer-analysis.yaml` | 缓冲区分析（投影转换→缓冲→保存） |
| `overlay-analysis.yaml` | 叠加分析（两图层求交集） |
| `batch-convert.yaml` | 批量格式转换（Shapefile→GeoJSON + 投影） |
| `filter-simplify.yaml` | 属性筛选 + 几何简化 |
| `dissolve-analysis.yaml` | 按属性融合分析 |

---

## 未完成模块 — 实现指南

### Raster Steps (`src/geopipe_agent/steps/raster/`)

需要实现以下步骤，每个步骤需要：
1. 在 `src/geopipe_agent/steps/raster/` 下创建模块文件
2. 使用 `@step` 装饰器注册
3. 在 `src/geopipe_agent/steps/__init__.py` 的 `load_builtin_steps()` 中添加 import
4. 如果操作走 Backend，需要在 `GeoBackend` 基类和 `GdalPythonBackend` 中添加相应方法

| Step ID | 说明 | 建议实现方式 |
|---------|------|-------------|
| `raster.reproject` | 栅格投影转换 | rasterio.warp.reproject |
| `raster.clip` | 栅格裁剪 | rasterio.mask.mask |
| `raster.calc` | 栅格计算（波段运算） | numpy 数组运算 |
| `raster.stats` | 栅格统计 | numpy 统计（min, max, mean, std） |
| `raster.contour` | 生成等值线 | matplotlib.contour 或 GDAL contour |

**模板示例**（以 `raster.stats` 为例）：

```python
@step(
    id="raster.stats",
    name="栅格统计",
    description="计算栅格数据的统计信息",
    category="raster",
    params={
        "input": {"type": "raster_info", "required": True, "description": "输入栅格数据"},
        "band": {"type": "number", "required": False, "default": 1, "description": "波段编号"},
    },
    outputs={
        "output": {"type": "dict", "description": "统计结果"},
    },
)
def raster_stats(ctx: StepContext) -> StepResult:
    import numpy as np
    raster = ctx.input("input")
    band = ctx.param("band", 1)
    data = raster["data"][band - 1]
    valid = data[~np.isnan(data)] if np.issubdtype(data.dtype, np.floating) else data
    stats = {
        "min": float(valid.min()),
        "max": float(valid.max()),
        "mean": float(valid.mean()),
        "std": float(valid.std()),
    }
    return StepResult(output=stats, stats=stats)
```

### Analysis Steps (`src/geopipe_agent/steps/analysis/`)

| Step ID | 说明 | 建议实现方式 |
|---------|------|-------------|
| `analysis.voronoi` | 泰森多边形 | scipy.spatial.Voronoi + shapely |
| `analysis.heatmap` | 热力图 | scipy.ndimage / KDE |
| `analysis.interpolate` | 空间插值 | scipy.interpolate |
| `analysis.cluster` | 空间聚类 | sklearn.cluster (DBSCAN/KMeans) |

### Network Steps (`src/geopipe_agent/steps/network/`)

| Step ID | 说明 | 建议实现方式 |
|---------|------|-------------|
| `network.shortest_path` | 最短路径 | networkx + osmnx |
| `network.service_area` | 服务区分析 | networkx 等时圈 |
| `network.geocode` | 地理编码 | geopy |

> ⚠️ Network steps 可能需要额外依赖（networkx, osmnx, geopy），建议作为可选依赖 `[network]`。

### GDAL CLI Backend (`src/geopipe_agent/backends/gdal_cli.py`)

当前所有方法均为 `NotImplementedError`。实现要点：
- 使用 `subprocess.run()` 调用 ogr2ogr、gdal_translate 等命令
- 输入/输出通过临时文件传递
- 大文件场景比 Python API 更高效

### QGIS Process Backend (`src/geopipe_agent/backends/qgis_process.py`)

当前所有方法均为 `NotImplementedError`。实现要点：
- 使用 `subprocess.run()` 调用 `qgis_process run <algorithm>`
- 参数通过 JSON 传递
- 需要 QGIS 安装环境

### 高级流水线特性

| 特性 | 当前状态 | 实现位置 |
|------|---------|---------|
| `when` 条件执行 | Schema 已支持解析，执行未实现 | `executor.py` 中在执行前检查 `step_def.when` |
| `retry` 重试 | `on_error=retry` 已纳入验证，执行未实现 | `executor.py` 中添加重试逻辑 |
| `backend` 指定 | ✅ 已实现 | 通过 `step_def.backend` 传递给 BackendManager |

---

## 开发注意事项

1. **step_id 命名规则**：禁止包含 `.`，仅允许 `[a-z0-9_-]`，Validator 强制校验
2. **IO 操作不走 Backend**：`io.*` 步骤直接使用 Fiona/Rasterio，不经过 Backend 抽象层
3. **StepRegistry 是单例**：测试中需要 `StepRegistry.reset()` + 重新加载模块
4. **添加新 Step 的检查清单**：
   - [ ] 创建步骤模块文件（使用 `@step` 装饰器）
   - [ ] 在 `steps/__init__.py` 的 `load_builtin_steps()` 中添加 import
   - [ ] 如需 Backend 支持，在 `GeoBackend` 基类添加抽象方法
   - [ ] 在 `GdalPythonBackend` 中实现具体方法
   - [ ] 编写单元测试
   - [ ] 运行 `geopipe-agent generate-skill-doc` 验证文档自动生成

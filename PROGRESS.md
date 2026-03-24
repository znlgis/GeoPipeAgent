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
| Raster Steps | ✅ 完成 | raster.reproject, raster.clip, raster.calc, raster.stats, raster.contour |
| Analysis Steps | ✅ 完成 | analysis.voronoi, analysis.heatmap, analysis.interpolate, analysis.cluster |
| Network Steps | ✅ 完成 | network.shortest_path, network.service_area, network.geocode |
| GDAL CLI Backend | ✅ 完成 | 全部方法实现（使用 ogr2ogr + subprocess） |
| QGIS Process Backend | ✅ 完成 | 全部方法实现（使用 qgis_process CLI） |
| 高级流水线特性 | ✅ 完成 | when 条件执行、retry 重试 |

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
| `raster.reproject` | 栅格投影转换 | raster | rasterio.warp.reproject |
| `raster.clip` | 栅格裁剪 | raster | rasterio.mask.mask |
| `raster.calc` | 栅格计算 | raster | numpy 波段数学运算（如 NDVI） |
| `raster.stats` | 栅格统计 | raster | min/max/mean/std 统计 |
| `raster.contour` | 生成等值线 | raster | matplotlib.contour + shapely |
| `analysis.voronoi` | 泰森多边形 | analysis | scipy.spatial.Voronoi + shapely |
| `analysis.heatmap` | 热力图 | analysis | scipy.ndimage KDE |
| `analysis.interpolate` | 空间插值 | analysis | scipy.interpolate / IDW |
| `analysis.cluster` | 空间聚类 | analysis | sklearn DBSCAN/KMeans |
| `network.shortest_path` | 最短路径 | network | networkx 图论算法 |
| `network.service_area` | 服务区分析 | network | networkx 等时圈 |
| `network.geocode` | 地理编码 | network | geopy Nominatim |

### 9. 测试 (`tests/`)

- `test_engine/test_parser.py` — 9 个测试（YAML 解析）
- `test_engine/test_validator.py` — 10 个测试（验证逻辑）
- `test_engine/test_context.py` — 12 个测试（上下文与变量解析）
- `test_engine/test_executor.py` — 5 个测试（端到端流水线执行）
- `test_engine/test_advanced_pipeline.py` — 8 个测试（when 条件执行、retry 重试）
- `test_steps/test_registry.py` — 9 个测试（注册表与装饰器）
- `test_steps/test_io_steps.py` — 4 个测试（IO 步骤）
- `test_steps/test_vector_steps.py` — 8 个测试（矢量步骤）
- `test_steps/test_raster_steps.py` — 8 个测试（栅格步骤）
- `test_steps/test_analysis_steps.py` — 8 个测试（分析步骤）
- `test_steps/test_network_steps.py` — 5 个测试（网络步骤）
- `test_backends/test_gdal_python.py` — 9 个测试（GdalPython 后端）
- **共计 95 个测试，全部通过**

### 10. Cookbook (`cookbook/`)

| 文件 | 说明 |
|------|------|
| `buffer-analysis.yaml` | 缓冲区分析（投影转换→缓冲→保存） |
| `overlay-analysis.yaml` | 叠加分析（两图层求交集） |
| `batch-convert.yaml` | 批量格式转换（Shapefile→GeoJSON + 投影） |
| `filter-simplify.yaml` | 属性筛选 + 几何简化 |
| `dissolve-analysis.yaml` | 按属性融合分析 |

---

## 新增模块详情

### Raster Steps (`src/geopipe_agent/steps/raster/`)

| Step ID | 说明 | 实现方式 |
|---------|------|-------------|
| `raster.reproject` | 栅格投影转换 | rasterio.warp.reproject |
| `raster.clip` | 栅格裁剪 | rasterio.mask.mask + 临时文件 |
| `raster.calc` | 栅格计算（波段运算） | numpy 数组运算 + 安全表达式求值 |
| `raster.stats` | 栅格统计 | numpy min/max/mean/std |
| `raster.contour` | 生成等值线 | matplotlib.contour + shapely LineString |

### Analysis Steps (`src/geopipe_agent/steps/analysis/`)

| Step ID | 说明 | 实现方式 |
|---------|------|-------------|
| `analysis.voronoi` | 泰森多边形 | scipy.spatial.Voronoi + shapely |
| `analysis.heatmap` | 热力图 | numpy histogram2d + scipy.ndimage gaussian_filter |
| `analysis.interpolate` | 空间插值 | scipy.interpolate.griddata + IDW |
| `analysis.cluster` | 空间聚类 | sklearn.cluster (DBSCAN / KMeans) |

### Network Steps (`src/geopipe_agent/steps/network/`)

| Step ID | 说明 | 实现方式 |
|---------|------|-------------|
| `network.shortest_path` | 最短路径 | networkx shortest_path |
| `network.service_area` | 服务区分析 | networkx single_source_dijkstra |
| `network.geocode` | 地理编码 | geopy Nominatim |

> ⚠️ 新增可选依赖组：`[analysis]` (scipy, scikit-learn, matplotlib)、`[network]` (networkx, geopy)

### GDAL CLI Backend (`src/geopipe_agent/backends/gdal_cli.py`)

已实现全部 6 个方法，使用 `subprocess.run()` 调用 ogr2ogr：
- `buffer` — 通过 SQLite 方言 ST_Buffer
- `clip` — 通过 `-clipsrc` 参数
- `reproject` — 通过 `-s_srs / -t_srs` 参数
- `dissolve` — 通过 SQLite 方言 ST_Union + GROUP BY
- `simplify` — 通过 `-simplify` 参数
- `overlay` — 通过 SQLite 方言空间函数

### QGIS Process Backend (`src/geopipe_agent/backends/qgis_process.py`)

已实现全部 6 个方法，使用 `qgis_process run` CLI：
- `buffer` → `native:buffer`
- `clip` → `native:clip`
- `reproject` → `native:reprojectlayer`
- `dissolve` → `native:dissolve`
- `simplify` → `native:simplifygeometries`
- `overlay` → `native:intersection / union / difference / symmetricaldifference`

### 高级流水线特性

| 特性 | 状态 | 实现位置 |
|------|---------|---------|
| `when` 条件执行 | ✅ 已实现 | `executor.py` — `_evaluate_condition()` 支持变量和步骤引用 |
| `retry` 重试 | ✅ 已实现 | `executor.py` — `_execute_step_with_retry()` 最多重试 3 次 |
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

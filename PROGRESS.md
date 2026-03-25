# GeoPipeAgent 实现进度文档

> 本文档记录 GeoPipeAgent 框架的实现进度，方便后续开发者继续未完成的部分。

## 总体进度

| 模块 | 状态 | 说明 |
|------|------|------|
| 项目结构 | ✅ 完成 | pyproject.toml、包结构、依赖配置 |
| 错误处理 | ✅ 完成 | 全部异常类 + AI 友好错误信息 |
| 数据模型 | ✅ 完成 | Pipeline、StepDefinition、StepResult |
| Step 插件系统 | ✅ 完成 | 注册表、@step 装饰器、StepContext |
| Backend 系统 | ✅ 完成 | 抽象基类 + GdalPythonBackend（功能完整）+ GdalCliBackend + QgisProcessBackend |
| Engine 核心 | ✅ 完成 | Parser、Validator、Resolver、Executor、Context、Reporter |
| CLI | ✅ 完成 | run (含 --var)、validate、list-steps、describe、info、backends、generate-skill-doc、generate-skill |
| IO Steps | ✅ 完成 | io.read_vector, io.write_vector, io.read_raster, io.write_raster |
| Vector Steps | ✅ 完成 | buffer, clip, reproject, dissolve, simplify, query, overlay |
| Raster Steps | ✅ 完成 | raster.reproject, raster.clip, raster.calc, raster.stats, raster.contour |
| Analysis Steps | ✅ 完成 | analysis.voronoi, analysis.heatmap, analysis.interpolate, analysis.cluster |
| Network Steps | ✅ 完成 | network.shortest_path, network.service_area, network.geocode |
| Skill 生成 | ✅ 完成 | 自动生成 SKILL.md、steps-reference.md、pipeline-schema.md |
| 测试 | ✅ 完成 | 95 个测试用例，全部通过 |
| Cookbook | ✅ 完成 | 5 个示例流水线 YAML |
| GDAL CLI Backend | ✅ 完成 | 全部方法实现（使用 ogr2ogr + subprocess） |
| QGIS Process Backend | ✅ 完成 | 全部方法实现（使用 qgis_process CLI） |
| 高级流水线特性 | ✅ 完成 | when 条件执行、retry 重试、on_error: skip |

---

## 代码审查修复记录（最新一轮）

### [必须修复] Windows 路径兼容性 — 已修复

**文件**：`tests/test_engine/test_executor.py`

**问题**：5 个 executor 测试在 Windows 下全部失败。原因是 `tmp_path` 生成的 Windows 路径（如 `C:\Users\...`）被 f-string 嵌入 YAML 双引号字符串后，反斜杠 `\U` 被 YAML 解析器解释为 8 位十六进制转义序列。

**修复**：新增 `_posix()` 辅助函数将 pathlib.Path 转换为 POSIX 风格路径（正斜杠），在所有 YAML 模板中使用。同时移除了对输出路径的精确字符串断言（改为检查文件存在性），因为跨平台路径表示不一致。

### [必须修复] eval() 安全加固 — 已修复

**文件**：`src/geopipe_agent/engine/executor.py`（`_evaluate_condition`）、`src/geopipe_agent/steps/raster/calc.py`

**问题**：两处 `eval()` 调用仅依赖 `{"__builtins__": {}}` 或简单的黑名单正则来限制危险操作，这在 Python 中不够安全。

**修复**：

1. **executor.py** — `_evaluate_condition()` 增加了 AST 白名单验证：解析表达式后遍历 AST 节点，仅允许 Expression、Compare、BoolOp、UnaryOp、BinOp、Constant、Name 及比较运算符节点，拒绝任何函数调用、属性访问或其他危险构造。

2. **raster/calc.py** — 将黑名单正则替换为完整的 AST 白名单验证：
   - 仅允许安全的算术/比较/布尔运算节点
   - 函数调用限制为预定义的 `np.*` 安全函数（abs, sqrt, log, sin, cos 等）
   - 属性访问限制为 `np.*` 命名空间
   - Name 节点必须是已注册的波段变量或 `np`

### [建议修改] StepRegistry 单例类属性 — 已修复

**文件**：`src/geopipe_agent/steps/registry.py`

**问题**：`_steps` 被声明为类属性 `_steps: dict[str, _StepInfo] = {}`，虽然 `__new__` 中会在实例上覆盖它，但类属性声明是多余且误导性的（暗示所有实例共享同一 dict）。

**修复**：移除类级别 `_steps` 属性声明，仅在 `__new__` 中初始化实例属性。

### [建议修改] Validator 嵌套参数引用检查缺失 — 已修复

**文件**：`src/geopipe_agent/engine/validator.py`

**问题**：`_validate_param_refs` 只检查顶层 `str` 类型参数中的 `$step.attr` 和 `${var}` 引用，嵌套在 dict/list 中的引用不会被验证，可能导致运行时才发现引用错误。

**修复**：重构为递归实现，新增 `_validate_value_refs` 函数，递归检查嵌套 dict 和 list 中的引用。错误信息中的 key 路径使用点号和方括号表示嵌套位置（如 `options.input` 或 `layers[0]`）。

### [建议修改] CLI 缺失命令 — 已实现

**文件**：`src/geopipe_agent/cli.py`

**问题**：设计规格定义了 8 个 CLI 命令，但只实现了 4 个（run、backends、generate-skill-doc、generate-skill）。

**新增实现**：
- `validate <pipeline.yaml>` — 仅验证 YAML 流水线，输出验证结果 JSON
- `list-steps [--category] [--format table|json]` — 列出所有步骤，支持按类别过滤和 JSON 输出
- `describe <step_id>` — 输出步骤的完整 JSON 元信息
- `info <file>` — 查看矢量/栅格数据文件摘要信息
- `run --var key=value` — 新增 `--var` 选项支持命令行覆盖流水线变量

### [建议修改] Skill 生成器过时文本 — 已修复

**文件**：`src/geopipe_agent/skillgen/generator.py`

**问题**：`generate_skill_file()` 中 raster/analysis/network 类别标注为 "(planned)"，但这些 Steps 已全部实现。

**修复**：更新为实际已实现的步骤列表。

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
- `StepExecutionError` — 步骤执行错误（含 `step_id`, `suggestion`, `cause`，支持 `to_dict()`）
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
- `GdalCliBackend` — ✅ 全部方法实现（使用 ogr2ogr + subprocess）
- `QgisProcessBackend` — ✅ 全部方法实现（使用 qgis_process CLI）
- `BackendManager` — 自动检测可用后端，支持按名称获取

### 6. Engine 核心 (`src/geopipe_agent/engine/`)

- `parser.py` — YAML 文件/字符串解析为 PipelineDefinition
- `validator.py` — step_id 格式校验、唯一性检查、注册表验证、递归引用合法性验证、变量定义检查
- `resolver.py` — 参数解析入口
- `context.py` — PipelineContext（变量替换 `${var}`、步骤引用 `$step.attr`、参数批量解析）
- `executor.py` — 顺序执行步骤、自动选择 Backend、on_error=skip/retry 支持、when 条件执行、AST 安全验证、AI 友好修复建议
- `reporter.py` — 生成 JSON 执行报告

### 7. CLI (`src/geopipe_agent/cli.py`)

| 命令 | 说明 |
|------|------|
| `geopipe-agent run <file> [--var key=value]` | 执行 YAML 流水线，支持变量覆盖，输出 JSON 报告 |
| `geopipe-agent validate <file>` | 仅验证 YAML 流水线（不执行） |
| `geopipe-agent list-steps [--category] [--format]` | 列出所有步骤（表格或 JSON） |
| `geopipe-agent describe <step_id>` | 步骤详情（JSON） |
| `geopipe-agent info <file>` | 查看 GIS 数据文件信息 |
| `geopipe-agent backends` | 列出所有后端及可用状态 |
| `geopipe-agent generate-skill-doc` | 生成 Steps 参考文档（stdout） |
| `geopipe-agent generate-skill --output-dir <dir>` | 生成完整 Skill 文件集 |

### 8. 已实现的 Steps（共 23 个）

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
| `raster.calc` | 栅格计算 | raster | numpy 波段数学运算（如 NDVI），AST 白名单安全验证 |
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
- `test_engine/test_executor.py` — 5 个测试（端到端流水线执行，含 Windows 路径兼容修复）
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

## 设计规格 vs 实现对照

| 设计规格要求 | 实现状态 | 备注 |
|-------------|---------|------|
| YAML Pipeline Schema | ✅ 完成 | 支持 name, description, crs, variables, steps, outputs |
| 步骤引用 `$step_id.output` | ✅ 完成 | PipelineContext.resolve() |
| 变量引用 `${var_name}` | ✅ 完成 | 支持全量替换和嵌入式替换 |
| 条件执行 `when` | ✅ 完成 | AST 安全验证 |
| 错误处理 `on_error: skip/fail/retry` | ✅ 完成 | retry 最多 3 次 + 指数退避 |
| 指定后端 `backend` | ✅ 完成 | 通过 BackendManager 选择 |
| `@step` 装饰器注册 | ✅ 完成 | 自动推导 category |
| 5 个 Step 类别 | ✅ 完成 | io(4) + vector(7) + raster(5) + analysis(4) + network(3) = 23 |
| 3 个 Backend 实现 | ✅ 完成 | gdal_python + gdal_cli + qgis_process |
| Backend 自动检测 | ✅ 完成 | BackendManager._detect_available() |
| CLI 全部 8 个命令 | ✅ 完成 | run, validate, list-steps, describe, info, backends, generate-skill-doc, generate-skill |
| CLI `--var` 变量覆盖 | ✅ 完成 | `geopipe-agent run <file> --var key=value` |
| JSON 执行报告 | ✅ 完成 | reporter.py |
| AI Skill 自动生成 | ✅ 完成 | skillgen/generator.py |
| 结构化日志 | ✅ 完成 | JSON 格式可选 |
| AI 友好错误信息 | ✅ 完成 | StepExecutionError.suggestion |

---

## 已知待改进项（非阻塞）

以下是代码审查中发现的非阻塞改进建议，供后续迭代参考：

### [仅供参考] 测试覆盖可扩展的模块

| 模块 | 现状 | 建议 |
|------|------|------|
| `cli.py` | 无直接测试 | 添加 Click CliRunner 集成测试 |
| `gdal_cli.py` / `qgis_process.py` | 无测试（需要外部工具） | 添加 mock subprocess 的单元测试 |
| `skillgen/generator.py` | 无测试 | 验证生成文档包含所有已注册步骤 |
| `utils/crs.py` | 无测试 | `normalize_crs()` 函数已实现但未被使用，可考虑移除或集成 |
| `reporter.py` | 无直接测试 | 通过 executor E2E 测试间接覆盖 |

### [仅供参考] GdalCliBackend SQL 注入防护

`gdal_cli.py` 中的 `buffer()` 方法使用临时文件名（`os.path.basename`）拼接 SQL 语句。虽然临时文件名由 `tempfile.mkstemp` 生成（可控），且 `_sanitize_identifier()` 方法已对用户字段名做了白名单校验，但 `buffer()` 中的层名来自文件系统，理论上在特定平台可能包含特殊字符。建议统一使用参数化或严格转义。

### [仅供参考] Backend 方法与 Step 的对应关系

当前 `GeoBackend` 抽象基类定义了 6 个方法（buffer, clip, reproject, dissolve, simplify, overlay），但 raster/analysis/network 类别的 Steps 不走 Backend 而是直接在 Step 内部实现。这符合设计规格的 "IO 操作不走 Backend" 约束，但后续如果需要支持 raster 操作的多后端切换，需要扩展 `GeoBackend` 接口。

### [仅供参考] vector.query 的 pandas.DataFrame.query() 安全性

`vector/query.py` 使用 `gdf.query(expression)` 执行用户提供的表达式。pandas `query()` 内部使用 `numexpr` 或 Python `eval()`，存在潜在的代码注入风险。由于流水线 YAML 本身由 AI 或开发人员编写（等同于代码），实际风险较低，但如果未来支持从不受信任的来源加载 YAML，需要加固此处。

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
5. **Windows 兼容性**：在测试中使用 YAML 模板嵌入文件路径时，务必转换为 POSIX 风格（正斜杠），否则反斜杠会被 YAML 解析器解释为转义字符
6. **eval() 安全规范**：所有涉及动态表达式求值的场景，必须使用 AST 白名单验证，不得仅依赖 `__builtins__={}` 或黑名单正则

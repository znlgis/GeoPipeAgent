# GeoPipeAgent Web UI 设计规格

> 版本: 1.0 | 日期: 2026-03-29

## 1. 项目概述

为 GeoPipeAgent（AI 原生 GIS 数据分析流水线框架）构建 Web UI，提供三大核心能力：

1. **流程可视化编辑器** — Vue Flow 拖拽式 DAG 编辑，双向映射现有 YAML 流水线格式
2. **LLM 双向集成** — OpenAI API 驱动：自然语言→流水线生成 + 执行结果→智能分析
3. **对话全量导出** — JSON / Markdown 格式，含完整消息、Token 用量、关联流水线

### 1.1 设计约束

- 所有新增代码放在 `web/` 目录下，不修改现有 `src/` 代码
- 后端通过 `import geopipe_agent` 直接调用引擎，零侵入集成
- 运行时数据存储在 `data/` 目录（加入 `.gitignore`）

## 2. 技术选型

| 层 | 技术 | 版本 |
|---|------|------|
| 前端框架 | Vue 3 + TypeScript | ^3.4 |
| 流程编辑器 | @vue-flow/core + background + controls + minimap | ^1.33 |
| UI 组件库 | Element Plus | ^2.5 |
| 状态管理 | Pinia | ^2.1 |
| 路由 | Vue Router | ^4.3 |
| 构建工具 | Vite | ^5.x |
| 后端框架 | FastAPI | >= 0.110 |
| ASGI 服务器 | Uvicorn | >= 0.27 |
| LLM 客户端 | openai (Python SDK) | >= 1.12 |
| SSE 支持 | sse-starlette | >= 1.8 |
| 数据校验 | Pydantic | >= 2.0 |
| DAG 布局 | dagre | ^0.8 |
| YAML 处理 | js-yaml (前端) / PyYAML (后端) | ^4.1 / >= 6.0 |
| Markdown 渲染 | markdown-it | ^14.0 |
| 语法高亮 | highlight.js | ^11.9 |
| HTTP 客户端 | axios | ^1.6 |
| 文件上传 | python-multipart | >= 0.0.6 |

### 2.1 架构方案

采用 **方案 B（轻量 SPA + SSE 流式推送）**：

```
Vue 3 + Vue Flow (前端 SPA)
        ↕ REST + SSE
FastAPI + 文件系统存储 (后端)
        ↕ 直接 import
GeoPipeAgent Engine + OpenAI API
```

**选择理由：**

- SSE 足够应对 LLM 流式输出和执行进度推送（均为服务端→客户端单向）
- 文件存储（JSON）足够应对工具型应用的持久化需求
- 开发成本可控，后续可升级（SSE→WebSocket、文件→SQLite）

## 3. 项目结构

```
GeoPipeAgent/
├── src/geopipe_agent/          # 现有引擎代码（不动）
├── web/                        # 新增 Web 应用
│   ├── backend/                # FastAPI 后端
│   │   ├── main.py             # FastAPI 应用入口
│   │   ├── config.py           # 配置管理（API Key、路径等）
│   │   ├── routers/
│   │   │   ├── pipeline.py     # 流水线 CRUD + 执行
│   │   │   ├── llm.py          # LLM 对话接口
│   │   │   └── export.py       # 导出接口
│   │   ├── services/
│   │   │   ├── pipeline_service.py   # 调用 GeoPipeAgent 引擎
│   │   │   ├── llm_service.py        # OpenAI API 封装
│   │   │   └── conversation_store.py # 对话记录存储
│   │   ├── models/
│   │   │   └── schemas.py      # Pydantic 请求/响应模型
│   │   └── requirements.txt    # 后端依赖
│   │
│   └── frontend/               # Vue 3 前端
│       ├── package.json
│       ├── vite.config.ts
│       ├── tsconfig.json
│       ├── src/
│       │   ├── App.vue
│       │   ├── main.ts
│       │   ├── views/
│       │   │   ├── PipelineEditor.vue    # 主编辑页面
│       │   │   ├── LlmChat.vue           # LLM 对话页面
│       │   │   └── ConversationHistory.vue # 历史记录页面
│       │   ├── components/
│       │   │   ├── flow/                  # 流程编辑器组件
│       │   │   │   ├── FlowCanvas.vue     # Vue Flow 画布
│       │   │   │   ├── StepNode.vue       # 步骤节点组件
│       │   │   │   ├── StepConfigPanel.vue # 节点属性面板
│       │   │   │   └── NodePalette.vue    # 节点拖放面板
│       │   │   ├── chat/                  # 对话组件
│       │   │   │   ├── ChatWindow.vue
│       │   │   │   └── MessageBubble.vue
│       │   │   └── common/               # 通用组件
│       │   │       ├── YamlPreview.vue
│       │   │       └── ExecutionLog.vue
│       │   ├── composables/              # Vue 组合式 API
│       │   │   ├── useFlowEditor.ts
│       │   │   ├── useLlm.ts
│       │   │   └── usePipeline.ts
│       │   ├── stores/                   # Pinia 状态管理
│       │   │   ├── pipelineStore.ts
│       │   │   └── chatStore.ts
│       │   ├── types/                    # TypeScript 类型
│       │   │   ├── pipeline.ts
│       │   │   └── chat.ts
│       │   └── utils/
│       │       ├── yamlConverter.ts      # YAML ↔ DAG 模型转换
│       │       └── sseClient.ts          # SSE 客户端封装
│       └── index.html
│
├── data/                       # 运行时数据（gitignore）
│   ├── conversations/          # 对话记录 JSON 文件
│   └── pipelines/              # 保存的流水线 YAML
├── cookbook/                    # 现有示例（不动）
├── tests/                      # 现有测试（不动）
└── pyproject.toml              # 现有配置（不动）
```

## 4. 流程可视化编辑器

### 4.1 YAML ↔ DAG 节点模型映射

现有 YAML 流水线是步骤序列，每个步骤通过 `$step_id.output` 引用前序输出。需双向映射为 Vue Flow 的节点/边模型。

**引擎实际 YAML 格式：**

- 步骤使用 `use` 字段（非 `type`）指定步骤类型，值为命名空间格式的 registry ID（如 `io.read_vector`、`vector.buffer`）
- 步骤引用格式为 `$step_id.output` 或 `$step_id.stats`（带属性访问）
- 变量引用格式为 `${var_name}`
- 步骤还支持 `when`（条件执行）、`on_error`（错误策略：fail/skip/retry）、`backend`（指定后端）等字段
- 流水线级别支持 `description`、`crs`、`variables`、`outputs` 等字段

**YAML 示例（引擎实际格式，参考 cookbook/buffer-analysis.yaml）：**

```yaml
pipeline:
  name: "缓冲区分析"
  description: "对道路数据进行缓冲区分析并输出结果"
  variables:
    input_path: "data/roads.shp"
    buffer_dist: 500
  steps:
    - id: load-roads
      use: io.read_vector             # ← 字段名是 use，值是 registry ID
      params:
        path: "${input_path}"         # ← 变量引用
    - id: buffer-analysis
      use: vector.buffer
      params:
        input: "$load-roads.output"   # ← 步骤引用（$step_id.output）→ 这就是一条边
        distance: "${buffer_dist}"
    - id: save-result
      use: io.write_vector
      params:
        input: "$buffer-analysis.output"  # ← 又一条边
        path: "output/road_buffer.geojson"
  outputs:
    result: "$save-result.output"
    stats: "$buffer-analysis.stats"
```

**映射为 Vue Flow 模型：**

```typescript
// types/pipeline.ts

/** 流水线级别元数据 */
interface PipelineMeta {
  name: string
  description?: string
  crs?: string
  variables: Record<string, any>
  outputs: Record<string, string>
}

/** 节点数据 */
interface StepNode {
  id: string            // step.id → node.id
  type: 'stepNode'      // 自定义节点类型
  position: { x, y }    // 自动布局计算或用户拖拽
  data: {
    use: string         // registry ID，如 "io.read_vector" | "vector.buffer"
    label: string       // 显示名称（从 use 映射或用户自定义）
    params: Record<string, any>  // 去掉 $ref 后的纯参数
    when?: string       // 条件表达式（可选）
    onError?: string    // 错误策略：fail | skip | retry（默认 fail）
    backend?: string    // 指定后端（可选，默认 auto）
    status?: 'idle' | 'running' | 'success' | 'error'
  }
}

/** 边（数据依赖） */
interface StepEdge {
  id: string
  source: string        // 被引用的 step_id
  target: string        // 当前 step_id
  sourceHandle: string  // 输出属性（如 "output" 或 "stats"）
  targetHandle: string  // 对应的参数名（如 "input"）
  label?: string        // 参数名显示
}
```

**转换逻辑（`yamlConverter.ts`）：**

- **YAML → DAG：**
  1. 解析 pipeline 级别元数据（name、description、crs、variables、outputs）
  2. 解析 steps 数组，每个 step → 一个 Node
  3. 扫描 params 中的 `$step_id.attr` 引用 → 创建 Edge（source=step_id, sourceHandle=attr, targetHandle=param_name）
  4. 保留 `when`、`on_error`、`backend` 等字段到 Node.data（确保无损往返转换）
  5. 使用 dagre 库自动布局计算 position

- **DAG → YAML：**
  1. 拓扑排序所有节点
  2. 还原 pipeline 级别元数据
  3. 每个 Node → 一个 step 对象（`id`、`use`、`params`、`when`、`on_error`、`backend`）
  4. 每条 Edge → 在目标节点的对应 param 中填入 `$source_id.sourceHandle`
  5. 序列化为 YAML

- **无损往返保证：** 导入的 YAML 经过 DAG 编辑后再导出，必须保留所有引擎支持的字段（包括 UI 中未提供编辑界面的字段），确保语义不变。

### 4.2 编辑器界面布局

```
┌──────────────────────────────────────────────────────┐
│  工具栏：运行 | 验证 | 保存 | AI生成 | 导入 | 导出   │
├──────────┬───────────────────────┬───────────────────┤
│ 节点面板 │                       │   属性面板        │
│          │                       │                   │
│ ▸ IO     │    Vue Flow 画布      │  [选中节点]       │
│  · 读矢量│                       │  类型: buffer     │
│  · 写矢量│   ┌────┐   ┌────┐    │  ID: buffer_1     │
│  · 读栅格│   │read│──→│buf │    │                   │
│  · 写栅格│   └────┘   └──┬─┘    │  参数:            │
│ ▸ 矢量   │              │       │  distance: [500]  │
│  · 缓冲区│          ┌────┘       │  unit: [m ▼]      │
│  · 裁剪  │          ▼            │  backend: [auto▼] │
│  · 融合  │   ┌──────┐           │                   │
│  · 叠加  │   │write │           │  ── 执行状态 ──   │
│ ▸ 栅格   │   └──────┘           │  ● 成功 (1.2s)    │
│ ▸ 分析   │                       │                   │
│ ▸ 质检   │                       │                   │
├──────────┴───────────────────────┴───────────────────┤
│ 底部面板：执行日志 / YAML 预览 （可切换标签页）        │
└──────────────────────────────────────────────────────┘
```

**核心交互：**

1. **从左侧面板拖拽** Step 类型到画布 → 创建新节点
2. **从节点输出端口拖线** 到另一个节点的输入端口 → 建立数据依赖
3. **点击节点** → 右侧面板显示可编辑参数（根据 Step 的参数 schema 动态渲染表单）
4. **点击"运行"** → 后端执行，节点状态实时更新（idle→running→success/error）
5. **点击"AI 生成"** → 弹出对话框输入自然语言描述，LLM 返回 YAML → 自动转换并加载到画布
6. **底部 YAML 预览** → 实时同步显示当前画布对应的 YAML 内容（只读预览）

### 4.3 节点参数 Schema

后端 `/api/pipeline/steps/{name}` 接口返回每个 Step 的参数描述，前端据此动态生成属性面板表单。

> **注意：** 引擎 registry 中步骤的参数类型使用引擎原始名称（如 `geodataframe`），Web API 层做显示友好映射（`geodataframe` → 前端显示为"图层"，类型标记为 `layer`）。

```json
{
  "name": "vector.buffer",
  "category": "vector",
  "description": "对输入几何体进行缓冲区分析",
  "params": {
    "input": { "type": "layer", "required": true, "description": "输入图层" },
    "distance": { "type": "number", "required": true, "description": "缓冲距离" },
    "cap_style": { "type": "enum", "values": ["round","flat","square"], "default": "round" }
  },
  "outputs": {
    "output": { "type": "layer" },
    "stats": { "type": "dict" }
  },
  "supports_backend": true
}
```

- `type: "layer"` 参数不显示表单控件，通过连线（Edge）赋值
- `type: "enum"` 渲染为下拉选择框
- `type: "number"` 渲染为数字输入框
- `type: "string"` 渲染为文本输入框
- `required: true` 的参数标记为必填
- 属性面板还提供 `when`（条件表达式）、`on_error`（错误策略下拉）、`backend`（后端选择下拉）的编辑控件

## 5. LLM 双向集成

### 5.1 System Prompt 策略

```python
def build_system_prompt(mode: str) -> str:
    base = "你是 GeoPipeAgent 的 AI 助手，专注于 GIS 数据分析流水线。"
    steps_ref = load_steps_reference()   # 从引擎 registry 动态获取
    schema_ref = load_pipeline_schema()  # 流水线 YAML schema

    if mode == "generate":
        return f"""{base}
用户会描述一个 GIS 分析需求，你需要生成可执行的 YAML 流水线。
规则：
1. 步骤使用 `use` 字段指定类型，值为 registry ID（如 io.read_vector、vector.buffer）
2. 步骤引用格式为 $step_id.output（必须带属性名）
3. 变量引用格式为 ${{var_name}}
4. 可用步骤列表：{steps_ref}
5. YAML 格式必须符合：{schema_ref}
6. 用 ```yaml 代码块包裹输出
7. 每个步骤加上中文注释说明用途
"""
    elif mode == "analyze":
        return f"""{base}
用户会提供流水线执行报告（JSON 格式），请分析结果：
1. 解读关键统计数据
2. 指出质检问题及严重程度
3. 给出改进建议
"""
```

### 5.2 对话流程

**场景 1 — AI 生成流水线：**

```
用户输入自然语言描述
  → 后端组装 prompt（generate 模式 + 步骤参考文档）
  → 调用 OpenAI chat completions（stream=True）
  → SSE 流式返回文本 → 前端实时显示
  → 前端从响应中提取 ```yaml``` 代码块
  → 用户点击"加载到编辑器" → yamlConverter 转换 → 画布渲染
```

**场景 2 — AI 分析结果：**

```
流水线执行完成 → 前端获得 JSON 报告
  → 用户点击"AI 分析"
  → 后端组装 prompt（analyze 模式 + JSON 报告内容）
  → SSE 流式返回分析文本 → 前端在对话窗口实时显示
```

### 5.3 LLM 配置管理

配置存储在 `data/llm_config.json`：

```json
{
  "api_key": "sk-...",
  "base_url": "https://api.openai.com/v1",
  "model": "gpt-4",
  "temperature": 0.7,
  "max_tokens": 4096,
  "system_prompt_extra": ""
}
```

- API Key 仅存储在服务端文件中
- 前端 GET 配置时，API Key 返回掩码值（如 `sk-...xxxx`）
- 支持自定义 `base_url`（兼容国内代理端点）

## 6. 后端 API 设计

### 6.1 流水线管理 (`routers/pipeline.py`)

| 方法 | 路径 | 功能 |
|------|------|------|
| `GET` | `/api/pipeline/steps` | 获取所有可用 Step 列表 |
| `GET` | `/api/pipeline/steps/{name}` | 获取 Step 详细描述 |
| `POST` | `/api/pipeline/validate` | 验证 YAML 流水线定义 |
| `POST` | `/api/pipeline/execute` | 执行流水线，返回 SSE 流式进度 |
| `POST` | `/api/pipeline/save` | 保存流水线到文件 |
| `GET` | `/api/pipeline/list` | 列出已保存的流水线 |
| `GET` | `/api/pipeline/{id}` | 加载指定流水线 |

### 6.2 LLM 对话 (`routers/llm.py`)

| 方法 | 路径 | 功能 |
|------|------|------|
| `POST` | `/api/llm/chat` | 发送消息，SSE 流式返回 |
| `POST` | `/api/llm/generate-pipeline` | 根据自然语言生成流水线 YAML |
| `POST` | `/api/llm/analyze-result` | 将执行报告发给 LLM 解读 |
| `GET` | `/api/llm/conversations` | 列出所有对话记录 |
| `GET` | `/api/llm/conversations/{id}` | 获取指定对话详情 |
| `DELETE` | `/api/llm/conversations/{id}` | 删除对话记录 |
| `PUT` | `/api/llm/config` | 更新 LLM 配置 |
| `GET` | `/api/llm/config` | 获取当前 LLM 配置 |

### 6.3 导出 (`routers/export.py`)

| 方法 | 路径 | 功能 |
|------|------|------|
| `GET` | `/api/export/conversation/{id}` | 导出指定对话（JSON/Markdown） |
| `GET` | `/api/export/conversation/{id}/messages` | 导出纯消息列表 |
| `POST` | `/api/export/batch` | 批量导出多个对话（ZIP） |

### 6.4 SSE 事件格式

```
event: progress
data: {"step_id": "buffer_1", "status": "running", "message": "执行缓冲区分析..."}

event: chunk
data: {"content": "根据您的", "token": 3}

event: done
data: {"result": {...}, "total_tokens": 500}

event: error
data: {"code": "STEP_FAILED", "message": "..."}
```

## 7. 对话存储与导出

### 7.1 存储格式

文件路径：`data/conversations/{conversation_id}.json`

```json
{
  "id": "uuid",
  "title": "自动摘要或用户命名",
  "created_at": "ISO8601",
  "updated_at": "ISO8601",
  "config": { "model": "gpt-4", "temperature": 0.7 },
  "messages": [
    {
      "role": "system|user|assistant",
      "content": "...",
      "timestamp": "ISO8601",
      "token_usage": { "prompt": 100, "completion": 200 },
      "metadata": {}
    }
  ]
}
```

### 7.2 导出格式

**JSON 导出：** 完整对话数据 + 统计信息（总 token、预估成本）+ 关联流水线 ID

**Markdown 导出：** 人类可读格式，包含元信息头部、按时间排列的消息、代码块保留

### 7.3 批量导出

`POST /api/export/batch` 接受多个对话 ID，返回 ZIP 压缩包。

## 8. 错误处理

| 场景 | 处理方式 |
|------|---------|
| YAML 解析/验证失败 | 结构化错误（行号 + 原因 + 建议），前端底部面板高亮 |
| 流水线执行 Step 失败 | SSE 推送 error 事件，节点变红显示错误信息 |
| LLM API 调用失败 | 区分 401/429/500，显示对应提示和重试按钮 |
| LLM 返回无效 YAML | 提示格式有误，允许手动修改或要求重新生成 |
| SSE 连接断开 | 自动重连（最多 3 次），超时提示手动重试 |
| 文件存储读写失败 | 返回 500 + 错误详情 |

## 9. 开发分期

| 阶段 | 内容 | 预估工期 |
|------|------|---------|
| 1 | 基础骨架（FastAPI + Vue + 路由布局） | 3-5 天 |
| 2 | 流程编辑器（Vue Flow + YAML 转换 + 执行） | 5-7 天 |
| 3 | LLM 集成（对话 + 生成 + 分析） | 3-5 天 |
| 4 | 存储与导出（历史记录 + JSON/MD 导出） | 2-3 天 |

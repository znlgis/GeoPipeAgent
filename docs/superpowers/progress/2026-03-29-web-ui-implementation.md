# GeoPipeAgent Web UI 实现进度文档

> 基于设计规格: [2026-03-29-web-ui-design.md](../specs/2026-03-29-web-ui-design.md)
> 最后更新: 2026-03-29

## 总体进度

| 阶段 | 内容 | 状态 | 备注 |
|------|------|------|------|
| 1 | 基础骨架（FastAPI + Vue + 路由布局） | ✅ 完成 | 后端 + 前端骨架均已搭建 |
| 2 | 流程编辑器（Vue Flow + YAML 转换 + 执行） | ✅ 完成 | 编辑器组件 + 转换逻辑已实现 |
| 3 | LLM 集成（对话 + 生成 + 分析） | ✅ 完成 | 后端 API + 前端组件已实现 |
| 4 | 存储与导出（历史记录 + JSON/MD 导出） | ✅ 完成 | 对话存储 + 导出 API 已实现 |

## 详细实现清单

### 后端 (`web/backend/`)

- [x] `main.py` — FastAPI 应用入口，CORS 中间件，路由注册，静态文件服务
- [x] `config.py` — 配置管理（目录路径、LLM 配置读写、API Key 掩码）
- [x] `models/schemas.py` — Pydantic v2 请求/响应模型（18 个 schema）
- [x] `routers/pipeline.py` — 流水线管理 API（7 个端点）
  - [x] `GET /api/pipeline/steps` — 按分类获取所有 Step
  - [x] `GET /api/pipeline/steps/{name}` — 获取 Step 详情
  - [x] `POST /api/pipeline/validate` — 验证 YAML
  - [x] `POST /api/pipeline/execute` — SSE 流式执行
  - [x] `POST /api/pipeline/save` — 保存流水线
  - [x] `GET /api/pipeline/list` — 列出已保存流水线
  - [x] `GET /api/pipeline/{id}` — 加载指定流水线
- [x] `routers/llm.py` — LLM 对话 API（8 个端点）
  - [x] `POST /api/llm/chat` — SSE 流式对话
  - [x] `POST /api/llm/generate-pipeline` — 自然语言生成流水线
  - [x] `POST /api/llm/analyze-result` — 分析执行报告
  - [x] `GET /api/llm/conversations` — 列出对话记录
  - [x] `GET /api/llm/conversations/{id}` — 获取对话详情
  - [x] `DELETE /api/llm/conversations/{id}` — 删除对话
  - [x] `PUT /api/llm/config` — 更新 LLM 配置
  - [x] `GET /api/llm/config` — 获取 LLM 配置（掩码）
- [x] `routers/export.py` — 导出 API（3 个端点）
  - [x] `GET /api/export/conversation/{id}` — 导出 JSON/Markdown
  - [x] `GET /api/export/conversation/{id}/messages` — 导出消息列表
  - [x] `POST /api/export/batch` — 批量导出 ZIP
- [x] `services/pipeline_service.py` — 引擎集成（步骤查询、验证、执行、CRUD）
- [x] `services/llm_service.py` — OpenAI API 封装（system prompt 构建、流式调用）
- [x] `services/conversation_store.py` — 对话持久化（JSON 文件存储、Markdown 导出）
- [x] `requirements.txt` — 后端依赖清单

### 前端 (`web/frontend/`)

#### 基础设施
- [x] `package.json` — 依赖配置
- [x] `vite.config.ts` — Vite 构建配置（API 代理、路径别名）
- [x] `tsconfig.json` — TypeScript 配置
- [x] `env.d.ts` — 类型声明
- [x] `index.html` — 入口 HTML
- [x] `src/main.ts` — 应用入口（Vue 3 + Element Plus + Pinia + Router）
- [x] `src/App.vue` — 主布局（导航菜单 + 路由视图）

#### TypeScript 类型
- [x] `src/types/pipeline.ts` — 流水线相关类型（StepNodeData, StepSchema, PipelineMeta, SSE 事件）
- [x] `src/types/chat.ts` — 对话相关类型（ChatMessage, Conversation, LLM 事件）

#### 工具函数
- [x] `src/utils/yamlConverter.ts` — YAML ↔ DAG 双向转换（dagre 自动布局）
- [x] `src/utils/sseClient.ts` — SSE 客户端封装（fetch + ReadableStream）

#### Pinia 状态管理
- [x] `src/stores/pipelineStore.ts` — 流水线状态（节点、边、元数据、步骤列表、执行状态）
- [x] `src/stores/chatStore.ts` — 对话状态（对话列表、当前对话、流式内容）

#### 组合式 API (Composables)
- [x] `src/composables/useFlowEditor.ts` — 编辑器操作（执行、验证、保存、导入导出）
- [x] `src/composables/useLlm.ts` — LLM 操作（配置管理、流式对话）
- [x] `src/composables/usePipeline.ts` — 流水线 CRUD 操作

#### 流程编辑器组件
- [x] `src/components/flow/FlowCanvas.vue` — Vue Flow 画布（拖放、连线、节点操作）
- [x] `src/components/flow/StepNode.vue` — 自定义步骤节点（分类配色、状态指示）
- [x] `src/components/flow/StepConfigPanel.vue` — 属性配置面板（动态表单、高级选项）
- [x] `src/components/flow/NodePalette.vue` — 节点拖放面板（分类折叠、搜索过滤）

#### 对话组件
- [x] `src/components/chat/ChatWindow.vue` — 对话窗口（消息列表、流式显示、模式选择）
- [x] `src/components/chat/MessageBubble.vue` — 消息气泡（Markdown 渲染、代码高亮、YAML 加载）

#### 通用组件
- [x] `src/components/common/YamlPreview.vue` — YAML 预览（语法高亮、复制）
- [x] `src/components/common/ExecutionLog.vue` — 执行日志（按类型着色、自动滚动）

#### 视图页面
- [x] `src/views/PipelineEditor.vue` — 主编辑器页面（工具栏 + 三栏布局 + 底部面板）
- [x] `src/views/LlmChat.vue` — AI 对话页面（对话列表侧栏 + 对话窗口）
- [x] `src/views/ConversationHistory.vue` — 历史记录页面（表格视图、导出操作）

### 其他
- [x] `.gitignore` — 添加 `data/`、`web/frontend/node_modules/`、`web/frontend/dist/`

## 验证结果

- [x] 后端 Python import 成功（19 个 API 端点注册）
- [x] 前端 TypeScript 类型检查通过（`vue-tsc --noEmit`）
- [x] 前端 Vite 构建通过（`vite build`）
- [x] 现有 139 个测试全部通过（`pytest tests/ -v`）
- [x] 未修改 `src/` 目录下的任何现有代码

## 后续优化项（可选）

以下是可以在未来迭代中继续完善的内容：

- [ ] 添加前端单元测试（Vitest + @vue/test-utils）
- [ ] 添加后端 API 测试（pytest + httpx）
- [ ] 优化 Vite 构建分包（减小 chunk 大小）
- [ ] 添加 E2E 测试（Playwright / Cypress）
- [ ] 完善错误处理边界情况
- [ ] 添加国际化支持（i18n）
- [ ] 添加用户认证功能
- [ ] 优化 SSE 断线重连逻辑
- [ ] 添加流水线版本管理
- [ ] 添加暗色主题支持

## 启动说明

### 后端

```bash
cd web/backend
pip install -r requirements.txt
uvicorn web.backend.main:app --reload --host 0.0.0.0 --port 8000
```

注意：需在项目根目录运行，确保 `geopipe_agent` 可导入。

### 前端

```bash
cd web/frontend
npm install
npm run dev
```

开发模式下，Vite 会自动将 `/api` 请求代理到后端 `http://localhost:8000`。

### 生产部署

```bash
cd web/frontend
npm run build
# 构建产物在 dist/ 目录，FastAPI 会自动服务静态文件
cd ../..
uvicorn web.backend.main:app --host 0.0.0.0 --port 8000
```

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
| 5 | 优化与增强（测试 + 主题 + i18n + 版本管理） | ✅ 完成 | 全部优化项均已实现 |

## 详细实现清单

### 后端 (`web/backend/`)

- [x] `main.py` — FastAPI 应用入口，CORS 中间件，路由注册，静态文件服务，全局异常处理器
- [x] `config.py` — 配置管理（目录路径、LLM 配置读写、API Key 掩码）
- [x] `models/schemas.py` — Pydantic v2 请求/响应模型（20 个 schema，含版本管理和对话创建）
- [x] `routers/pipeline.py` — 流水线管理 API（8 个端点）
  - [x] `GET /api/pipeline/steps` — 按分类获取所有 Step
  - [x] `GET /api/pipeline/steps/{name}` — 获取 Step 详情
  - [x] `POST /api/pipeline/validate` — 验证 YAML
  - [x] `POST /api/pipeline/execute` — SSE 流式执行
  - [x] `POST /api/pipeline/save` — 保存流水线（含输入验证和版本管理）
  - [x] `GET /api/pipeline/list` — 列出已保存流水线
  - [x] `GET /api/pipeline/{id}` — 加载指定流水线
  - [x] `DELETE /api/pipeline/{id}` — 删除流水线
- [x] `routers/llm.py` — LLM 对话 API（9 个端点）
  - [x] `POST /api/llm/chat` — SSE 流式对话
  - [x] `POST /api/llm/generate-pipeline` — 自然语言生成流水线
  - [x] `POST /api/llm/analyze-result` — 分析执行报告
  - [x] `GET /api/llm/conversations` — 列出对话记录
  - [x] `POST /api/llm/conversations` — 创建新对话
  - [x] `GET /api/llm/conversations/{id}` — 获取对话详情
  - [x] `DELETE /api/llm/conversations/{id}` — 删除对话
  - [x] `PUT /api/llm/config` — 更新 LLM 配置（含温度/token 数验证）
  - [x] `GET /api/llm/config` — 获取 LLM 配置（掩码）
- [x] `routers/export.py` — 导出 API（3 个端点）
  - [x] `GET /api/export/conversation/{id}` — 导出 JSON/Markdown
  - [x] `GET /api/export/conversation/{id}/messages` — 导出消息列表
  - [x] `POST /api/export/batch` — 批量导出 ZIP
- [x] `services/pipeline_service.py` — 引擎集成（步骤查询、验证、执行、CRUD、版本管理、删除）
- [x] `services/llm_service.py` — OpenAI API 封装（system prompt 构建、流式调用）
- [x] `services/conversation_store.py` — 对话持久化（JSON 文件存储、Markdown 导出）
- [x] `requirements.txt` — 后端依赖清单
- [x] `tests/conftest.py` — 测试配置（临时目录、异步客户端）
- [x] `tests/test_pipeline.py` — 流水线 API 测试（13 个测试）
- [x] `tests/test_llm.py` — LLM/对话 API 测试（9 个测试）
- [x] `tests/test_export.py` — 导出 API 测试（6 个测试）

### 前端 (`web/frontend/`)

#### 基础设施
- [x] `package.json` — 依赖配置（含 vue-i18n、vitest、@playwright/test）
- [x] `vite.config.ts` — Vite 构建配置（API 代理、路径别名、分包优化、测试配置）
- [x] `tsconfig.json` — TypeScript 配置
- [x] `env.d.ts` — 类型声明
- [x] `index.html` — 入口 HTML
- [x] `src/main.ts` — 应用入口（Vue 3 + Element Plus + Pinia + Router + i18n + 全局错误处理）
- [x] `src/App.vue` — 主布局（导航菜单 + 路由视图 + 暗色主题切换 + 语言切换）

#### TypeScript 类型
- [x] `src/types/pipeline.ts` — 流水线相关类型（含 version 字段）
- [x] `src/types/chat.ts` — 对话相关类型

#### 工具函数
- [x] `src/utils/yamlConverter.ts` — YAML ↔ DAG 双向转换（dagre 自动布局）
- [x] `src/utils/sseClient.ts` — SSE 客户端封装（fetch + ReadableStream + 指数退避重连）
- [x] `src/utils/format.ts` — 格式化工具

#### 国际化
- [x] `src/locales/index.ts` — i18n 初始化（vue-i18n 模块、语言切换、localStorage 持久化）
- [x] `src/locales/zh-CN.ts` — 中文语言包
- [x] `src/locales/en-US.ts` — 英文语言包

#### Pinia 状态管理
- [x] `src/stores/pipelineStore.ts` — 流水线状态（API 端点已修正）
- [x] `src/stores/chatStore.ts` — 对话状态（API 端点已修正）

#### 组合式 API (Composables)
- [x] `src/composables/useFlowEditor.ts` — 编辑器操作
- [x] `src/composables/useLlm.ts` — LLM 操作（API 端点已修正）
- [x] `src/composables/usePipeline.ts` — 流水线 CRUD 操作（API 端点已修正）

#### 流程编辑器组件
- [x] `src/components/flow/FlowCanvas.vue` — Vue Flow 画布
- [x] `src/components/flow/StepNode.vue` — 自定义步骤节点
- [x] `src/components/flow/StepConfigPanel.vue` — 属性配置面板
- [x] `src/components/flow/NodePalette.vue` — 节点拖放面板

#### 对话组件
- [x] `src/components/chat/ChatWindow.vue` — 对话窗口
- [x] `src/components/chat/MessageBubble.vue` — 消息气泡

#### 通用组件
- [x] `src/components/common/YamlPreview.vue` — YAML 预览
- [x] `src/components/common/ExecutionLog.vue` — 执行日志

#### 视图页面
- [x] `src/views/PipelineEditor.vue` — 主编辑器页面
- [x] `src/views/LlmChat.vue` — AI 对话页面（样式已适配暗色主题）
- [x] `src/views/ConversationHistory.vue` — 历史记录页面

#### 测试
- [x] `src/utils/yamlConverter.test.ts` — YAML 转换测试（16 个测试）
- [x] `src/utils/sseClient.test.ts` — SSE 客户端测试（5 个测试）
- [x] `src/utils/format.test.ts` — 格式化工具测试（2 个测试）
- [x] `src/locales/locales.test.ts` — 国际化配置测试（4 个测试）
- [x] `playwright.config.ts` — E2E 测试配置（Playwright + Chromium）
- [x] `e2e/basic.spec.ts` — 基础 E2E 测试（导航、主题、语言切换）

### 其他
- [x] `.gitignore` — 添加 `data/`、`web/frontend/node_modules/`、`web/frontend/dist/`

## 验证结果

- [x] 后端 Python import 成功（22 个 API 端点注册）
- [x] 前端 TypeScript 类型检查通过（`vue-tsc --noEmit`）
- [x] 前端 Vite 构建通过（`vite build`，分包优化后主应用 chunk < 20KB）
- [x] 现有 139 个测试全部通过（`pytest tests/ -v`）
- [x] 后端 API 测试 28 个全部通过（`pytest web/backend/tests/ -v`）
- [x] 前端单元测试 27 个全部通过（`npm run test`）
- [x] 未修改 `src/` 目录下的任何现有代码

## 已完成的优化项

以下优化项已全部实现：

- [x] 添加前端单元测试（Vitest + @vue/test-utils）— 27 个测试
- [x] 添加后端 API 测试（pytest + httpx）— 28 个测试
- [x] 优化 Vite 构建分包（manualChunks: vue-vendor, element-plus, vue-flow, ui-utils, data-utils）
- [x] 添加 E2E 测试配置（Playwright + Chromium，含基础测试用例）
- [x] 完善错误处理边界情况（全局异常处理器、axios 拦截器、Vue 错误处理器、输入验证）
- [x] 添加国际化支持（vue-i18n，中文/英文双语）
- [x] 优化 SSE 断线重连逻辑（指数退避重连，最多 3 次重试）
- [x] 添加流水线版本管理（同名流水线自动版本递增）
- [x] 添加暗色主题支持（CSS 自定义属性 + Element Plus 暗色模式 + localStorage 持久化）

## 未实现项

- [ ] 添加用户认证功能（涉及安全架构设计，建议独立迭代）

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

### 测试

```bash
# 后端 API 测试
python -m pytest web/backend/tests/ -v

# 前端单元测试
cd web/frontend
npm run test

# 前端 E2E 测试（需要先启动后端和前端）
cd web/frontend
npx playwright install  # 首次运行需安装浏览器
npm run test:e2e
```

### 生产部署

```bash
cd web/frontend
npm run build
# 构建产物在 dist/ 目录，FastAPI 会自动服务静态文件
cd ../..
uvicorn web.backend.main:app --host 0.0.0.0 --port 8000
```

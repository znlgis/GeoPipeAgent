# GeoPipeAgent Web 优化进度文档

> 更新时间: 2026-03-31
> 分支: `copilot/optimize-interaction-experience`

---

## 总体方案概览

基于原始需求，对 web/ 目录下前后端代码进行审查与优化，涵盖：
1. 交互体验优化（Frontend）
2. 服务端接口与调度优化（Backend）
3. 部署与工程化优化

---

## ✅ 已完成项

### 一、交互体验优化（Frontend）

#### 1. 对话式主导的 UI ✅ (已有实现)
- `ChatWindow.vue` — 三种交互模式：对话 / 生成流水线 / 分析结果
- `MessageBubble.vue` — Markdown 渲染、YAML 提取、"加载到编辑器"按钮
- SSE 实时流式输出
- Skill 模块注入开关与 Token 估算

#### 2. YAML 管道的可视化/节点化编辑 ✅ (已有实现)
- Vue Flow DAG 编辑器（`FlowCanvas.vue`）
- `StepNode.vue` — 分类颜色编码、状态指示器
- `NodePalette.vue` — 步骤库搜索、拖拽/双击添加
- `StepConfigPanel.vue` — 动态参数表单、条件执行、错误策略
- Dagre 自动布局
- YAML ↔ 图形双向转换

#### 3. GIS 数据结果的实时预览 ✅ (本次新增)
- `MapPreview.vue` — 基于 OpenLayers (CDN) 的交互式地图组件
  - 支持 GeoJSON 数据自动渲染
  - 要素高亮与统计信息（要素数量、bbox 范围）
  - OSM 底图 + 比例尺
  - 自动 fit 到数据范围
  - 深色/浅色主题适配
  - 加载失败时降级显示 JSON

#### 4. 执行过程的实时状态与流式日志 ✅ (已有实现)
- `ExecutionLog.vue` — 实时彩色日志
- SSE 事件流（progress / done / error）
- 每步状态追踪（idle / running / success / error）

### 二、服务端接口与调度优化（Backend）

#### 1. 异步任务队列与状态机 ✅ (本次新增)
- `services/task_queue.py` — Redis Queue 后端 + 内存回退
  - 任务生命周期：创建 → 运行 → 完成/失败
  - Redis 存储（24h TTL）
  - 无 Redis 时自动降级为内存存储
- `routers/task.py` — 任务管理 API
  - `POST /api/task/submit` — 提交后台执行（立即返回 Task ID）
  - `GET /api/task/{id}` — 查询任务状态
  - `GET /api/task/{id}/stream` — SSE 实时任务进度
  - `GET /api/task/list` — 列出近期任务
  - `DELETE /api/task/{id}` — 删除任务
  - `GET /api/task/queue/status` — 队列健康检查

#### 2. Skill 能力的动态发现与注册接口 ✅ (已有实现)
- `routers/skill.py` — 完整的 RESTful API
  - 内置模块 + 外部模块管理
  - 文本 / URL / 文件导入
  - 热加载（clear-cache + re-generate）
  - Token 估算

#### 3. 会话与上下文管理 ✅ (本次增强)
- 多轮对话流水线生成 — `generate_pipeline_with_context()` 携带完整历史
  - 用户可先说"提取水系"，再说"只保留大于10km的"
  - LLM 接收完整对话历史，串联生成完整 Pipeline
- `PATCH /api/llm/conversations/{id}` — 对话重命名接口

### 三、部署与工程化优化

#### 1. 前后端一体化 Docker 编排 ✅ (本次新增)
- `web/backend/Dockerfile` — 基于 GDAL 官方镜像，包含所有 GIS C++ 依赖
- `web/frontend/Dockerfile` — Node 构建 + Nginx 服务
- `web/frontend/nginx.conf` — API 代理 + SSE 支持 + SPA 回退 + 静态缓存
- `docker-compose.yml` — 四服务编排：
  - frontend (Nginx)
  - backend (FastAPI + GDAL)
  - redis (任务队列)
  - worker (RQ 后台工作进程)
- `.env.example` — 环境变量配置模板

#### 2. 预置示例与一键运行模板 ✅ (本次新增)
- `routers/template.py` — 模板管理 API
  - `GET /api/template/list` — 列出所有模板（含元数据）
  - `GET /api/template/{id}` — 获取模板详情（含 YAML 内容）
- 7 个预置模板（来自 cookbook/）：
  | ID | 名称 | 分类 | 难度 |
  |---|---|---|---|
  | buffer-analysis | 缓冲区分析 | analysis | beginner |
  | overlay-analysis | 叠加分析 | analysis | intermediate |
  | batch-convert | 批量转换 | io | beginner |
  | dissolve-analysis | 融合分析 | analysis | beginner |
  | filter-simplify | 筛选与简化 | vector | beginner |
  | vector-qc | 矢量质检 | qc | advanced |
  | raster-qc | 栅格质检 | qc | intermediate |
- `TemplateGallery.vue` — 前端模板库页面
  - 分类筛选 + 搜索
  - 难度标签（入门/中级/高级）
  - "加载到编辑器" / "用 AI 试试" 两种入口
- i18n 完整支持（中英双语）

---

## 🔲 后续待完成项

### 前端优化

#### 1. MapPreview 深度集成
- [x] 在 `PipelineEditor.vue` 执行完成后自动展示地图预览
- [ ] 支持 WKT 格式数据解析与渲染
- [ ] 添加 ECharts 图表组件展示统计结果（面积、长度等）
- [ ] 支持多图层叠加展示
- [ ] 添加图层控制面板（显示/隐藏/样式调整）

#### 2. 模板 "试用" 完整流程
- [x] 点击"用 AI 试试"时自动填充 prompt 到聊天页面
- [x] 模板详情弹窗（展示完整 YAML、步骤说明、预期输出）
- [ ] 模板收藏/置顶功能

#### 3. 任务管理 UI
- [x] 任务列表组件（展示运行中/已完成/失败任务）
- [x] 任务进度条组件（SSE 实时更新）
- [ ] 任务结果查看（自动调用 MapPreview 展示空间数据）
- [x] 将 "提交后台执行" 按钮添加到 PipelineEditor 工具栏

#### 4. 用户引导 / Onboarding
- [ ] 首次访问引导 tour（介绍各功能区）
- [x] Pipeline Editor 空状态引导（"拖拽步骤或选择模板开始"）

### 后端优化

#### 1. 真正的分布式任务队列
- [ ] 集成 RQ Worker（`python -m rq.cli worker`）执行 pipeline
- [ ] 替代 `asyncio.create_task` 为真正的 RQ job enqueue
- [ ] 任务结果持久化（Redis hash 或文件系统）
- [ ] 任务超时和重试策略

#### 2. Pipeline 执行结果数据提取
- [ ] 从执行报告中提取 GeoJSON/WKT 数据
- [ ] 提供 `/api/pipeline/result/{task_id}/geodata` 端点
- [ ] 支持空间数据格式转换（CRS → EPSG:4326 for web）

#### 3. 用户认证与多租户
- [ ] JWT 认证中间件
- [ ] 用户 session 隔离（每用户独立对话/流水线空间）
- [ ] API Key 配额管理

### 部署优化

#### 1. Docker 镜像优化
- [ ] 多阶段构建减小后端镜像体积
- [x] 添加 healthcheck 到 backend 和 frontend 服务
- [ ] 支持 ARM64 架构构建
- [ ] 添加 PostGIS 服务到 docker-compose.yml（可选）

#### 2. CI/CD
- [ ] GitHub Actions 自动构建和推送 Docker 镜像
- [ ] 自动运行测试（前后端）
- [ ] 版本化发布流程

---

## 测试状态

| 类型 | 数量 | 状态 |
|------|------|------|
| 后端 API 测试 | 52 | ✅ 全部通过 |
| 前端单元测试 | 27 | ✅ 全部通过 |
| TypeScript 类型检查 | - | ✅ 无错误 |
| Vite 生产构建 | - | ✅ 成功 |

---

## 新增文件列表

```
.env.example                                    # Docker 环境变量模板
docker-compose.yml                              # Docker 编排
web/backend/Dockerfile                          # 后端镜像
web/backend/routers/template.py                 # 模板 API
web/backend/routers/task.py                     # 任务队列 API
web/backend/services/task_queue.py              # Redis 任务队列服务
web/backend/tests/test_template.py              # 模板 API 测试
web/backend/tests/test_task.py                  # 任务 API 测试
web/frontend/Dockerfile                         # 前端镜像
web/frontend/nginx.conf                         # Nginx 配置
web/frontend/src/components/common/MapPreview.vue  # 地图预览组件
web/frontend/src/stores/templateStore.ts        # 模板状态管理
web/frontend/src/stores/taskStore.ts            # 任务状态管理
web/frontend/src/types/template.ts              # 模板类型定义
web/frontend/src/types/task.ts                  # 任务类型定义
web/frontend/src/views/TemplateGallery.vue      # 模板库页面
web/frontend/src/views/TaskManager.vue          # 任务管理页面
```

## 修改文件列表

```
web/backend/main.py                             # 注册 template + task 路由
web/backend/models/schemas.py                   # 新增 Template/Task Pydantic 模型
web/backend/routers/llm.py                      # 多轮上下文 + PATCH 重命名
web/backend/services/llm_service.py             # generate_pipeline_with_context()
web/frontend/src/App.vue                        # 导航菜单增加"模板库"+"任务管理"
web/frontend/src/main.ts                        # 路由增加 /templates, /tasks
web/frontend/src/locales/zh-CN.ts               # i18n: template, mapPreview, task, emptyState
web/frontend/src/locales/en-US.ts               # i18n: template, mapPreview, task, emptyState
web/frontend/src/views/PipelineEditor.vue       # MapPreview tab, Submit Background, 空状态引导
web/frontend/src/views/LlmChat.vue              # 路由参数处理（模板"用 AI 试试"流程）
web/frontend/src/views/TemplateGallery.vue      # 模板详情弹窗
web/frontend/src/components/chat/ChatWindow.vue # initialPrompt/initialMode props
web/frontend/src/utils/sseClient.ts             # GET 方法支持（任务 SSE 流）
docker-compose.yml                              # backend/frontend healthcheck
```

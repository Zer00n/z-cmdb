# CMDB Lite 开发工作手册（Kiro Playbook）

> **文档版本**：v1.0
> **配套 PRD**：`CMDB-Lite-PRD-v2.md`
> **目标读者**：Kiro（任务编排）+ Claude Sonnet 4.6（代码生成）+ 项目开发者（决策与 review）
> **文档定位**：规约性文档。PRD 回答"做什么"，本文档回答"怎么协作做"。
> **最后更新**：2026-05-18

---

## 0. 如何使用本手册

本手册是 Kiro 调用 Claude Sonnet 4.6 时的硬约束规约。使用方式：

1. **作为 Kiro 系统提示**：把第 1 章"项目宪法"作为 Kiro 工作区的 System Prompt 一部分
2. **作为任务模板**：第 3 章的 Task 卡片可以直接复制为 Kiro Task
3. **作为 Claude 调用前缀**：第 4 章的 Prompt 模板在每次调用 Claude 时使用
4. **作为质量检查**：第 5 章的 Quality Gates 是每阶段验收清单

**本文档是活文档**。v0.1 阶段开发完成后必修订一次（增补踩坑经验），v0.3 完成后再修订一次。

---

## 1. 项目宪法（Project Constitution）

> 以下内容**每次调用 Claude 时都应附带**（或作为 Kiro 全局系统提示）。这是项目里最硬的约束，不可妥协。

### 1.1 技术栈锁定清单

**后端**：
- Python 3.11+（不使用 3.12+ 特性）
- FastAPI（不使用 Flask、Django）
- SQLAlchemy 2.0+（使用 2.0 风格 API，不使用 1.x 的 query 风格）
- Alembic（数据库迁移唯一工具）
- Pydantic v2（不使用 v1 语法）
- pytest（不使用 unittest）
- python-libnmap（解析 nmap，不自己写 XML 解析）
- defusedxml（XML 安全解析）
- argon2-cffi（密码哈希，不使用 bcrypt/passlib）
- python-jose（JWT，不使用 PyJWT）

**前端**：
- Vue 3 Composition API（**禁用** Options API）
- TypeScript（**所有** `.vue` 文件 `<script setup lang="ts">`）
- Vite（不使用 webpack）
- Pinia（不使用 Vuex）
- Element Plus（**唯一** UI 库，不混用 Ant Design Vue / Naive UI）
- @element-plus/icons-vue（**唯一** 图标库，不混用 FontAwesome / Iconify）
- axios（HTTP 客户端，不使用 fetch 裸调）
- dayjs（**禁用** moment.js）
- echarts（图表唯一选择，不使用 Chart.js / D3）
- pnpm（包管理器，不使用 npm/yarn）

**铁律**：以上清单的库**不允许 Claude 推荐新增**。如果 Claude 建议引入新库，必须由开发者人工评估并更新本清单。

### 1.2 目录结构规范

**后端文件归属规则**：

| 文件类型 | 归属目录 | 命名 |
|---------|---------|------|
| FastAPI 路由 | `app/routers/` | `<resource>.py`，如 `assets.py` |
| Pydantic schema | `app/schemas/` | `<resource>.py`，类名 `AssetCreate` `AssetRead` `AssetUpdate` |
| SQLAlchemy 模型 | `app/models/` | `<resource>.py`，类名单数大驼峰如 `Asset` |
| 业务逻辑 | `app/services/` | `<resource>_service.py`，函数式或类 |
| 数据访问 | `app/repositories/` | `<resource>_repo.py` |
| 工具函数 | `app/utils/` | 按用途命名 |
| 配置 | `app/core/config.py` | 单文件 |
| 安全相关 | `app/core/security.py` | 单文件 |
| 依赖注入 | `app/core/deps.py` | 单文件 |

**前端文件归属规则**：

| 文件类型 | 归属目录 | 命名 |
|---------|---------|------|
| 页面 | `src/views/<module>/` | `<Page>.vue`，PascalCase |
| 业务组件 | `src/components/<module>/` | `<Component>.vue`，PascalCase |
| 通用组件 | `src/components/common/` | `AppXxx.vue` 前缀 |
| 路由 | `src/router/index.ts` | 单文件 |
| Pinia store | `src/stores/` | `<resource>.ts`，camelCase |
| API 封装 | `src/api/` | `<resource>.ts`，函数式导出 |
| TypeScript 类型 | `src/types/` | `<resource>.ts` |
| 样式 token | `src/styles/tokens.css` | 单文件，CSS 变量 |
| Element 主题 | `src/styles/element-theme.scss` | 单文件 |
| Design 模板 | `src/design/` | 仅放从 Claude Design 输出的原始文件 + README |

**禁止**：
- 跨目录嵌套（如把 service 放进 routers）
- 创建未在上述清单中的新目录（如需新增，必须先更新本文档）
- 文件命名混用（不能时而 snake_case 时而 kebab-case）

### 1.3 命名约定

| 场景 | 规则 | 示例 |
|------|------|------|
| Python 文件名 | snake_case | `asset_service.py` |
| Python 类名 | PascalCase | `AssetService` |
| Python 函数/变量 | snake_case | `get_asset_by_id` |
| Python 常量 | UPPER_SNAKE | `MAX_UPLOAD_SIZE` |
| TS/JS 文件名 | camelCase（普通）/ PascalCase（Vue 组件） | `assetApi.ts` / `AssetList.vue` |
| TS 类型/接口 | PascalCase | `interface Asset { ... }` |
| TS 函数/变量 | camelCase | `fetchAssetList` |
| CSS 变量 | kebab-case，带前缀 | `--color-primary` `--space-md` |
| 数据库表 | 复数 snake_case | `assets`, `scan_batches` |
| 数据库字段 | snake_case | `created_at`, `network_zone` |
| API 路径 | kebab-case 复数 | `/api/scan-batches` |
| Git 分支 | `feature/<v0.x>-<short>` | `feature/v0.1-scaffold` |

### 1.4 错误处理统一模式

**后端**：

```python
# app/core/exceptions.py - 统一异常基类
class CMDBException(Exception):
    """业务异常基类"""
    status_code = 400
    error_code = "CMDB_ERROR"
    
class AssetNotFoundError(CMDBException):
    status_code = 404
    error_code = "ASSET_NOT_FOUND"

class PermissionDeniedError(CMDBException):
    status_code = 403
    error_code = "PERMISSION_DENIED"

class ValidationError(CMDBException):
    status_code = 422
    error_code = "VALIDATION_ERROR"

# main.py 中注册统一异常处理器
@app.exception_handler(CMDBException)
async def cmdb_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error_code": exc.error_code, "message": str(exc)}
    )
```

**铁律**：
- Service 层只抛 `CMDBException` 子类，不返回错误码
- Router 层不写 try/except，依赖全局异常处理器
- 数据库异常在 Repository 层转换为业务异常后抛出
- **禁止** Service 层返回 `None` 表示"未找到"，必须抛 `XxxNotFoundError`

**前端**：

```typescript
// src/api/request.ts - axios 拦截器统一处理
interceptors.response.use(
  res => res.data,
  err => {
    const errorCode = err.response?.data?.error_code
    const message = err.response?.data?.message || '请求失败'
    
    // 401 → 跳登录
    if (err.response?.status === 401) {
      router.push('/login')
      return Promise.reject(err)
    }
    
    // 其他错误统一 Element Plus message
    ElMessage.error(message)
    return Promise.reject(err)
  }
)
```

**铁律**：
- 业务组件中**禁止**写 `try/catch` 处理 HTTP 错误，统一由 axios 拦截器处理
- 业务组件可处理业务异常（如表单校验失败）但不处理网络异常

### 1.5 日志规范

**后端**：

```python
# 使用 logging 模块，配置在 app/core/logging.py
import logging
logger = logging.getLogger(__name__)

# 日志级别使用约定
logger.debug("调试细节，仅开发时打开")
logger.info("正常业务事件，如 用户登录")
logger.warning("可恢复异常，如 LLM 调用降级到本地模型")
logger.error("业务错误，如 nmap XML 解析失败")
logger.critical("系统级错误，如 数据库连接断开")

# 必须包含的字段
logger.info("user login success", extra={
    "user_id": user.id,
    "ip": request.client.host,
    "user_agent": request.headers.get("user-agent")
})
```

**格式**：JSON 格式输出到 stdout（Docker 友好），由外部日志系统收集。

**禁止**：
- 直接 `print()`（开发期偶尔用，提交前必须删）
- 在日志中输出密码、token、API key 等敏感信息
- 在日志中输出脱敏前的资产 IP/主机名（除非是 audit_log）

### 1.6 提交信息格式

采用 [Conventional Commits](https://www.conventionalcommits.org/) 简化版：

```
<type>(<scope>): <subject>

[optional body]
```

**type 枚举**：
- `feat`：新功能
- `fix`：bug 修复
- `refactor`：重构（不改外部行为）
- `test`：测试相关
- `docs`：文档
- `chore`：杂项（依赖更新、配置等）
- `perf`：性能优化

**scope 示例**：`asset`、`scan`、`topology`、`auth`、`audit`、`infra`

**示例**：
```
feat(asset): 实现资产列表 API 含筛选与分页
fix(scan): 修复 nmap XML 解析时 MAC 缺失导致的崩溃
refactor(auth): JWT 刷新逻辑改为 httpOnly cookie
docs(playbook): 更新 v0.1 任务拆解
```

### 1.7 禁区清单（Claude 绝对不能自主做的事）

以下操作 Claude 生成代码或建议时**绝对禁止**，必须由开发者人工执行：

1. **Alembic 迁移文件创建**：必须开发者执行 `alembic revision --autogenerate` 后人工 review
2. **生产环境配置变更**：`.env.production`、Nginx 配置、Docker secrets 由开发者维护
3. **数据库 schema 破坏性变更**：删除列、改列类型，需要先讨论
4. **依赖库升级**：requirements.txt 和 package.json 的版本变更，每次手动确认
5. **删除任何已有文件**：除非开发者明确说"删除某文件"
6. **修改 `.gitignore` / `pyproject.toml` / `vite.config.ts`**：项目级配置文件改动需人工
7. **生成测试数据时使用真实公网 IP**：必须用 RFC1918 私网段或文档保留段
8. **在前端组件中硬编码颜色 / 字号 / 间距**：必须用 CSS 变量
9. **绕过权限中间件**：每个需要鉴权的接口必须通过 `Depends(get_current_user)` 等依赖项
10. **跳过 audit_log 埋点**：所有写操作（CREATE/UPDATE/DELETE）必须记录审计日志

---

## 2. 前端设计契约（Frontend Design Contract）

> 这一章约束所有前端代码生成行为。配合 PRD 5.4 节阅读。

### 2.1 设计 token 单一来源

**所有视觉常量**（颜色、字号、间距、圆角、阴影）唯一来源是 `frontend/src/styles/tokens.css`。

```css
/* tokens.css 示例（实际值从 Claude Design 第 1 次输出提取） */
:root {
  /* 主色 */
  --color-primary: #2563EB;
  --color-primary-hover: #1D4ED8;
  --color-primary-light: #DBEAFE;
  
  /* 语义色 */
  --color-success: #10B981;
  --color-warning: #F59E0B;
  --color-danger: #EF4444;
  --color-info: #6B7280;
  
  /* 中性色 */
  --color-bg-page: #F8FAFC;
  --color-bg-card: #FFFFFF;
  --color-border: #E5E7EB;
  --color-text-primary: #111827;
  --color-text-secondary: #6B7280;
  --color-text-disabled: #9CA3AF;
  
  /* 间距（8 网格） */
  --space-xs: 4px;
  --space-sm: 8px;
  --space-md: 16px;
  --space-lg: 24px;
  --space-xl: 32px;
  --space-2xl: 48px;
  
  /* 圆角 */
  --radius-sm: 4px;
  --radius-md: 6px;
  --radius-lg: 8px;
  
  /* 阴影 */
  --shadow-subtle: 0 1px 2px rgba(0,0,0,0.05);
  --shadow-medium: 0 4px 6px rgba(0,0,0,0.07);
  --shadow-floating: 0 10px 15px rgba(0,0,0,0.1);
  
  /* 字号 */
  --font-h1: 28px;
  --font-h2: 22px;
  --font-h3: 18px;
  --font-h4: 16px;
  --font-body: 14px;
  --font-caption: 12px;
  
  /* 字体 */
  --font-family-base: "PingFang SC", "Microsoft YaHei", -apple-system, sans-serif;
  --font-family-mono: "JetBrains Mono", "Consolas", monospace;
}
```

**禁止行为**：
- 在 `.vue` 文件中硬编码颜色值如 `color: #2563EB;`
- 在 `.vue` 文件中硬编码 `padding: 16px;`（应为 `padding: var(--space-md);`）
- 创建副本 token（如某个组件局部定义另一套变量）

**例外**：与 Element Plus 主题对齐的 SCSS 变量可以定义在 `element-theme.scss`，但其值必须引用 token CSS 变量。

### 2.2 Element Plus 组件选用清单

为防止"同一交互场景在不同页面用不同组件"的混乱，固化组件选用：

| 交互场景 | 必用组件 | 禁用替代 |
|---------|---------|---------|
| 列表展示 | `ElTable` | 不使用 div 自制表格 |
| 表单 | `ElForm` + `ElFormItem` | 不使用裸 input |
| 弹窗 | `ElDialog` | 不使用 `ElDrawer`（除非滑出式更合适） |
| 确认提示 | `ElMessageBox.confirm` | 不使用自制 modal |
| 消息提示 | `ElMessage` | 不使用 alert/toast 库 |
| 通知 | `ElNotification` | 同上 |
| 加载状态 | `v-loading` 指令 | 不使用 `ElSkeleton`（v1.0 不做） |
| 分页 | `ElPagination` | 同上 |
| 日期选择 | `ElDatePicker` | 同上 |
| 标签 | `ElTag` | 不使用 div 自制 |
| 下拉菜单 | `ElDropdown` | 同上 |
| 步骤条 | `ElSteps` | 同上 |
| 树形结构 | `ElTree` | 同上 |
| 图标 | `@element-plus/icons-vue` | 不使用 FontAwesome 等 |

**特例**：drawio 嵌入和 echarts 图表是例外，因为 Element Plus 不提供等价组件。

### 2.3 页面布局模板复用

PRD 12.6 节列出了 9 个 Design 输出模板，每个模板有明确的复用范围。开发新页面时：

```
新页面需求 → 判断属于哪类（列表/详情/表单/特殊）
            ↓
查 PRD 12.6 找对应模板
            ↓
从 src/design/<对应文件> 复制为 src/views/<module>/<NewPage>.vue
            ↓
替换业务字段、API、columns 定义，保持布局结构不变
```

**禁止行为**：
- 看到"这个页面有点不一样"就改布局结构
- 在新页面里新增设计 token（如新颜色）
- 复制粘贴多个模板的"碎片"拼凑新页面

### 2.4 国际化策略

v1.0 仅中文，**不引入 i18n 库**。所有文案直接硬编码中文。

理由：目标用户全中文，引入 i18n 增加复杂度无收益。v2.0 如需英文版再切换。

### 2.5 响应式策略

仅保证 **桌面端 ≥ 1280px** 可用。

- 不写 `@media` 查询
- 不使用 `ElRow` 的响应式 props（`:xs :sm :md` 全部忽略）
- 不做触摸事件适配
- 移动端访问可显示一行提示"请使用桌面浏览器访问"（v1.0 可不做）

---

## 3. v0.1 阶段任务拆解

> 每张 Task 卡片可直接复制为 Kiro Task。前置依赖 → 输入 → 输出 → 验收标准 → Prompt 模板。

### Task v0.1-01：项目仓库初始化

**前置依赖**：无

**输入**：
- 项目名：cmdb-lite
- 目录结构见 PRD 5.3

**输出**：
- 顶层目录骨架（backend / frontend / docker / docs / scripts）
- `README.md`（含项目介绍、技术栈、快速开始）
- `.gitignore`（Python + Node.js + IDE + 项目特定）
- `LICENSE`（建议 MIT 或 AGPL，待定）
- `pyproject.toml`（标记 Python 3.11+）

**验收标准**：
- 目录结构与 PRD 5.3 一致
- `git init` 后第一次提交可干净通过

**给 Claude 的 Prompt 模板**：
```
[附带：本 Playbook 第 1 章 + 第 2 章]

任务：初始化 CMDB Lite 项目仓库骨架。

要求：
1. 严格按照 PRD 5.3 节的目录结构创建所有目录（用 .gitkeep 占位空目录）
2. 生成 .gitignore，覆盖 Python venv、pycache、node_modules、IDE 文件、SQLite 数据库文件、上传文件目录、.env 等
3. 生成 README.md，包含：
   - 项目名与一句话介绍
   - 技术栈清单（引用 PRD 5.1）
   - Windows 11 / Docker / Linux 三种环境的快速开始命令
   - 项目结构说明
4. 生成 pyproject.toml 基础配置，Python 3.11+
5. 不要生成具体业务代码

输出格式：列出所有要创建的文件，每个文件给出完整内容。
```

---

### Task v0.1-02：后端 FastAPI 基础框架

**前置依赖**：Task v0.1-01

**输入**：
- 目录 `backend/app/`
- 技术栈：FastAPI + SQLAlchemy 2.0 + Pydantic v2 + Alembic

**输出**：
- `backend/requirements.txt`
- `backend/app/main.py`（FastAPI 入口，含 CORS、统一异常处理器）
- `backend/app/core/config.py`（Pydantic Settings 配置）
- `backend/app/core/database.py`（SQLAlchemy engine + sessionmaker）
- `backend/app/core/exceptions.py`(CMDBException 体系)
- `backend/app/core/logging.py`（JSON 日志配置）
- `backend/alembic.ini` + `backend/alembic/` 目录初始化
- `backend/app/health.py`（健康检查路由 `GET /api/health`）

**验收标准**：
- `uvicorn app.main:app` 能启动，访问 `/api/health` 返回 `{"status":"ok"}`
- `/docs` 可访问 OpenAPI 文档
- SQLite 数据库文件自动创建在 `./data/cmdb.db`
- 日志以 JSON 格式输出到 stdout

**给 Claude 的 Prompt 模板**：
```
[附带：Playbook 第 1 章 + PRD 5.1, 5.3, 9.1]

任务：搭建后端 FastAPI 基础框架。

要求：
1. requirements.txt 严格使用 PRD 12.3 的依赖清单
2. config.py 使用 Pydantic Settings v2，配置项：
   - DATABASE_URL（默认 sqlite:///./data/cmdb.db）
   - JWT_SECRET（从环境变量或 secrets 文件读取）
   - JWT_ACCESS_EXPIRE_MINUTES（默认 15）
   - JWT_REFRESH_EXPIRE_DAYS（默认 7）
   - UPLOAD_MAX_SIZE_MB（默认 50）
   - LOG_LEVEL（默认 INFO）
3. database.py：
   - SQLite 必须开启 WAL 模式（pragma journal_mode=WAL）
   - 使用 SQLAlchemy 2.0 风格的 sessionmaker + DeclarativeBase
   - 使用 pathlib 处理数据库路径（跨平台）
4. exceptions.py 按 Playbook 1.4 节实现
5. main.py：
   - 注册全局异常处理器
   - 注册 CORS（开发期允许 localhost:5173）
   - 注册健康检查路由
6. 所有文件 IO 使用 pathlib + encoding="utf-8"

不要生成：
- 用户模型 / 资产模型（下一任务）
- Alembic 迁移文件（人工执行）
```

---

### Task v0.1-03：用户模型与鉴权

**前置依赖**：Task v0.1-02

**输入**：
- 用户表 schema 见 PRD 6.1
- 权限矩阵见 PRD 3.2
- JWT 配置见 PRD 9.1

**输出**：
- `app/models/user.py`（SQLAlchemy User 模型）
- `app/schemas/user.py`（UserCreate / UserRead / UserUpdate / LoginRequest / TokenResponse）
- `app/core/security.py`（argon2 哈希、JWT 编解码）
- `app/core/deps.py`（`get_current_user` 等依赖项 + 角色检查）
- `app/repositories/user_repo.py`（基础 CRUD）
- `app/services/auth_service.py`（登录、刷新、修改密码）
- `app/routers/auth.py`（路由）
- `tests/test_auth.py`（pytest 测试）

**验收标准**：
- 启动时如 users 表空则自动创建 admin / 生成随机密码（密码打印到 stdout 一次）
- POST `/api/auth/login` 返回 access_token 并设置 refresh httpOnly cookie
- POST `/api/auth/refresh` 能用 refresh cookie 刷新 access_token
- POST `/api/auth/logout` 清除 cookie
- POST `/api/auth/change-password` 校验旧密码后允许修改
- 5 次失败登录锁定 15 分钟
- 单元测试覆盖率 ≥ 70%

**给 Claude 的 Prompt 模板**：
```
[附带：Playbook 第 1 章 + PRD 3, 6.1 users 表, 7.1 鉴权 API, 9.1 安全]

任务：实现用户模型与鉴权模块。

具体要求见上方"输出"和"验收标准"。

特别注意：
1. password_hash 使用 argon2id，参数严格按 PRD 9.1（m=65536, t=3, p=4）
2. JWT 使用 python-jose，access_token claims 包含 user_id, role, exp
3. refresh cookie 必须 httpOnly=True, secure=True, samesite='strict'
4. get_current_user 依赖项从 Bearer token 解析
5. 角色检查依赖项：
   - require_super_admin
   - require_admin（含 super_admin 和 admin）
   - require_auditor（含 auditor）
   - require_any（任何已登录角色）
6. 首次启动创建 admin 用户的逻辑放在 main.py 的 startup 事件
7. 测试用 pytest fixture 创建临时 SQLite 数据库

不要生成：
- 用户管理 CRUD API（v0.5 阶段做）
- 用户管理前端（v0.5 阶段做）
```

---

### Task v0.1-04：前端 Vue 3 脚手架

**前置依赖**：Task v0.1-01

**输入**：
- 目录 `frontend/`
- 技术栈见 Playbook 1.1 前端部分

**输出**：
- `frontend/package.json`（依赖见 PRD 12.4）
- `frontend/vite.config.ts`
- `frontend/tsconfig.json`
- `frontend/.eslintrc` + `frontend/.prettierrc`
- `frontend/src/main.ts`（Vue 入口 + Element Plus 全局引入 + 全部图标注册）
- `frontend/src/App.vue`
- `frontend/src/router/index.ts`（基础路由）
- `frontend/src/stores/auth.ts`（Pinia auth store）
- `frontend/src/api/request.ts`（axios 实例 + 拦截器）
- `frontend/src/api/auth.ts`（登录/刷新/登出 API 封装）
- `frontend/src/types/auth.ts`（TS 类型）
- `frontend/src/styles/tokens.css`（**占位**，等 Design 输出后填充）
- `frontend/src/styles/element-theme.scss`（**占位**）
- `frontend/index.html`

**验收标准**：
- `pnpm dev` 能启动到 `http://localhost:5173`
- 访问根路径自动跳到 `/login`
- 浏览器控制台无报错
- TypeScript 严格模式通过
- axios 拦截器能正确处理 401（跳登录）

**给 Claude 的 Prompt 模板**：
```
[附带：Playbook 第 1, 2 章 + PRD 5.3, 12.4]

任务：搭建前端 Vue 3 + TypeScript + Element Plus 脚手架。

要求：
1. 包管理器使用 pnpm，依赖严格按 PRD 12.4
2. Vite 配置：
   - 代理 /api 到 http://localhost:8000
   - 路径别名 @ → src
3. Element Plus 全量引入（开发期方便，后期再 tree-shake）
4. @element-plus/icons-vue 全部图标全局注册（命名空间不冲突）
5. axios 拦截器按 Playbook 1.4 实现，401 跳 /login
6. Pinia auth store 持久化（access_token 存 sessionStorage，user 信息存 Pinia 内存）
7. router 配置基础路由（/login 公开，其他需登录）
8. styles/tokens.css 和 element-theme.scss 创建为空占位文件，留注释"等 Claude Design 输出后填充"
9. tsconfig 严格模式：strict: true, noImplicitAny: true

不要生成：
- 具体页面（Login.vue 等，等 Design 输出后再做）
- 资产 / 扫描 / 审计相关代码
```

---

### Task v0.1-05：Claude Design 模板输出与落地

**前置依赖**：Task v0.1-04

**输入**：
- 之前已经讨论的 9 个 Design Prompt
- Pro 账户当前 Design 额度 63%

**输出**：
- 9 份 Design 原始输出（HTML 或 Vue 片段），存放 `frontend/src/design/` 下
- 提取的设计 token，填充 `frontend/src/styles/tokens.css`
- Element Plus 主题覆盖文件 `frontend/src/styles/element-theme.scss`
- `frontend/src/design/README.md`（记录 9 个文件的对应关系，引用 PRD 12.6）

**执行方式**：**本任务由开发者手动操作**，不调用 Claude Sonnet 4.6。

**执行步骤**：
1. 按之前提供的 9 个 prompt 顺序调用 Claude Design
2. 每次输出后，将原始文件保存为：
   - `src/design/01-design-system.html`
   - `src/design/02-login-and-layout.html`
   - `src/design/03-asset-list.html`
   - `src/design/04-asset-detail.html`
   - `src/design/05-asset-form.html`
   - `src/design/06-scan-confirm.html`
   - `src/design/07-topology-editor.html`
   - `src/design/08-report-dashboard.html`
   - `src/design/09-audit-log.html`
3. 第 1 次输出后立即提取 token 到 `tokens.css`，再继续后续 8 次
4. 9 次完成后写 `src/design/README.md` 说明每个文件对应实现路径（见 PRD 12.6）

**验收标准**：
- 9 份 Design 输出文件齐全
- `tokens.css` 含至少 30 个 CSS 变量
- `element-theme.scss` 已覆盖主色、语义色、圆角、字体
- 启动前端能看到 Element Plus 按钮颜色已和 token 主色一致

---

### Task v0.1-06：基于 Design 实现登录页与主框架

**前置依赖**：Task v0.1-03（后端鉴权）+ Task v0.1-05（Design 输出）

**输入**：
- `src/design/02-login-and-layout.html`
- `src/api/auth.ts`

**输出**：
- `src/views/Login.vue`
- `src/layouts/MainLayout.vue`
- `src/router/index.ts`（更新路由）
- 侧边栏菜单组件 `src/components/common/AppSidebar.vue`
- 顶部栏组件 `src/components/common/AppHeader.vue`

**验收标准**：
- 登录页布局完全匹配 Design 输出
- 输入 admin / 初始密码可登录成功
- 登录后进入主框架，侧边栏菜单按角色权限过滤显示
- 顶部用户菜单可修改密码 / 退出
- 侧边栏可折叠/展开

**给 Claude 的 Prompt 模板**：
```
[附带：Playbook 第 1, 2 章 + PRD 3 权限矩阵]
[附带：src/design/02-login-and-layout.html 完整内容]
[附带：src/api/auth.ts 已有代码]
[附带：src/styles/tokens.css 完整内容]

任务：基于 Design 输出实现登录页和主框架布局。

要求：
1. Login.vue：
   - 严格按 Design 02 文件的视觉布局
   - 使用 ElForm + ElFormItem + ElInput + ElButton
   - 表单验证：用户名非空、密码非空
   - 登录成功后调用 auth store 保存 token 并跳转 /
   - 失败显示 ElMessage
2. MainLayout.vue：
   - 顶部栏 + 侧边栏 + 主内容区三段布局
   - 使用 <RouterView /> 渲染子路由
   - 顶部右侧显示当前用户名 + 角色徽章（ElTag）
3. AppSidebar.vue：
   - 菜单数据定义在组件内，每项含 { title, icon, route, requiredRoles }
   - 根据 auth store 的当前用户角色过滤菜单项
   - 使用 ElMenu，激活态匹配当前路由
   - 支持折叠
4. AppHeader.vue：
   - 左侧 Logo + 产品名
   - 右侧用户 ElDropdown，菜单项：修改密码 / 退出登录
5. 修改密码使用 ElDialog 弹窗

严格约束：
- 所有颜色/间距/字号使用 var(--xxx)
- 所有图标使用 @element-plus/icons-vue
- 所有文案中文
- TypeScript 严格类型
- 不修改 router 守卫之外的 router 配置（守卫负责检查 token）
```

---

### Task v0.1-07：Docker 本地跑通

**前置依赖**：Task v0.1-02 ~ v0.1-06

**输入**：
- 后端代码已可独立运行
- 前端代码已可独立运行
- Dockerfile 模板见 PRD 8.3

**输出**：
- `docker/Dockerfile.backend`
- `docker/Dockerfile.frontend`
- `docker/nginx.conf`
- `docker/docker-compose.yml`
- `secrets/jwt_secret.txt`（开发期占位，gitignore）
- `docker/.dockerignore`

**验收标准**：
- `docker-compose up --build` 能启动两个容器
- 访问 `http://localhost:8080` 看到登录页
- 数据库文件持久化在宿主机 `./data/`
- 容器内使用非 root 用户运行

**给 Claude 的 Prompt 模板**：
```
[附带：PRD 8.3 完整 Docker 配置示例]
[附带：当前 backend/requirements.txt 和 frontend/package.json]

任务：编写 Docker 部署配置。

要求严格按 PRD 8.3 节实现，特别注意：
1. 多阶段构建减小镜像体积
2. 容器内非 root 用户（UID 1001）
3. 数据卷正确挂载
4. JWT secret 使用 docker secrets 而非环境变量明文
5. nginx.conf 配置：
   - 静态文件 root /usr/share/nginx/html
   - /api 反向代理到 http://backend:8000
   - SPA fallback：try_files $uri /index.html
6. .dockerignore 排除 node_modules、.git、data、.env

验证清单：
- docker-compose up --build 成功
- 后端 healthcheck 通过
- 前端能访问到登录页
- 重启容器后数据保留
```

---

### v0.1 阶段验收清单

完成所有 7 个 Task 后，执行：

- [ ] 后端能独立启动（`uvicorn`）
- [ ] 前端能独立启动（`pnpm dev`）
- [ ] Docker 能一键启动（`docker-compose up`）
- [ ] 三种启动方式都能登录到主界面
- [ ] 后端单元测试通过率 100%，覆盖率 ≥ 70%
- [ ] 前端 TypeScript 严格模式通过
- [ ] 9 个 Design 文件齐全
- [ ] tokens.css 已填充
- [ ] 所有提交信息符合 Conventional Commits
- [ ] README 已更新快速开始命令

**完成 v0.1 后，本 Playbook 需要修订一次**——把过程中发现的踩坑点补充进来，特别是：
- Claude Design 输出与 Element Plus 落地之间的差异点
- Windows 11 上的特殊问题
- Docker 构建的踩坑

---

## 4. Claude 调用规约（Prompt Engineering Rules）

### 4.1 每次调用 Claude 的标准结构

```
[上下文层 1：项目宪法]
直接附带本 Playbook 第 1 章内容（约 400 行）

[上下文层 2：本任务相关 PRD 章节]
根据 Task 卡片"输入"指明的 PRD 章节，附带原文

[上下文层 3：已有代码上下文]
附带当前已存在的相关文件完整内容（小文件全文，大文件给关键片段 + 文件结构）

[任务描述]
- 任务目标（一句话）
- 输出清单（要哪些文件）
- 输入清单（基于哪些已有代码）
- 验收标准（如何判断完成）
- 不要做什么（明确边界）

[输出格式要求]
- 列出所有要创建/修改的文件路径
- 每个文件给出完整内容（不要给 diff）
- 文件之间用 `### 文件: xxx` 分隔
```

### 4.2 上下文塞入的优先级

当上下文窗口紧张时，**保留**优先级从高到低：

1. **项目宪法**（不可省略）
2. **当前 Task 的具体要求**（不可省略）
3. **本任务直接相关的 PRD 章节**（必要）
4. **本任务直接依赖的代码文件**（必要）
5. **同模块的其他代码**（可省略文件结构概要代替）
6. **PRD 背景章节如第 1 章**（可省略，Claude 不需要知道为什么做）

### 4.3 让 Claude 做 code review 的 prompt 模板

```
[附带：Playbook 第 1, 2 章]
[附带：要 review 的文件完整内容]

任务：按以下清单对代码做 review，不要修改代码，输出问题清单。

Review 清单：
1. 是否违反 Playbook 1.1 技术栈锁定（引入了未授权的库）？
2. 是否违反 Playbook 1.2 目录结构规范（文件位置错误）？
3. 是否违反 Playbook 1.3 命名约定？
4. 是否违反 Playbook 1.4 错误处理统一模式（try/catch 滥用，返回 None 而非抛异常）？
5. 是否违反 Playbook 1.5 日志规范（print、敏感信息）？
6. 是否违反 Playbook 1.7 禁区清单？
7. 前端是否违反 Playbook 2.1 token 单一来源（硬编码颜色/间距）？
8. 前端是否违反 Playbook 2.2 组件选用清单？
9. SQL 注入风险？XSS 风险？XXE 风险？
10. 权限检查是否到位（每个写操作有依赖项）？
11. audit_log 埋点是否到位？

输出格式：
- 每个问题：[严重程度: 高/中/低] [所在文件:行号] 问题描述 + 建议修复
- 没有问题的清单项不输出
- 最后给一句话总结（通过 / 需修改）
```

### 4.4 让 Claude 写测试的 prompt 模板

```
[附带：Playbook 第 1 章]
[附带：要测试的 service/router 完整代码]
[附带：相关 model 和 schema 代码]

任务：为以下代码写 pytest 单元测试。

要求：
1. 使用 pytest fixture（不使用 unittest.TestCase）
2. 使用临时 SQLite 数据库（in-memory 或 tmp_path）
3. 测试覆盖：
   - 正常路径（happy path）
   - 边界条件（空输入、最大值、特殊字符）
   - 异常路径（每种业务异常至少一个用例）
   - 权限检查（如果适用）
4. 文件路径：tests/test_<module>.py
5. 测试函数命名：test_<功能>_<场景>，如 test_create_asset_with_duplicate_asset_no
6. 使用 pytest.mark.parametrize 减少重复
7. 不 mock 数据库（使用真实 SQLite），mock 外部服务（如 LLM API）

不要做：
- 不要修改被测代码
- 不要新增非测试文件
- 不追求 100% 覆盖率，关键路径覆盖即可
```

---

## 5. 质量门（Quality Gates）

每个阶段完成时，必须通过对应质量门才能进入下一阶段。

### 5.1 通用质量门（每个阶段都要过）

- [ ] **测试**：单元测试覆盖率 ≥ 60%（核心 service ≥ 80%）
- [ ] **类型**：mypy（后端）/ tsc（前端）严格模式通过
- [ ] **lint**：ruff / eslint 无 error
- [ ] **format**：black / prettier 已应用
- [ ] **审计埋点**：所有写操作有 audit_log 埋点
- [ ] **权限检查**：所有非公开接口有 `Depends(get_current_user)` 或角色依赖
- [ ] **文档**：API 在 `/docs` 有 description；前端组件有顶部注释说明用途

### 5.2 安全质量门

- [ ] **SQL 注入**：全 ORM 参数化查询，无 raw SQL 拼接
- [ ] **XSS**：前端无 `v-html` 使用（特殊场景需注释说明）
- [ ] **XXE**：XML 解析全用 defusedxml
- [ ] **敏感信息**：日志、错误响应、URL 无密码 / token / API key
- [ ] **文件上传**：类型校验、大小限制、magic number 校验、路径不可猜测
- [ ] **CSRF**：refresh cookie 设置 SameSite=Strict
- [ ] **密码策略**：argon2id 参数符合 PRD 9.1

### 5.3 跨平台质量门

- [ ] **路径**：全用 `pathlib.Path`，无硬编码 `/` 或 `\`
- [ ] **编码**：所有文件 IO 显式 `encoding="utf-8"`
- [ ] **换行**：Git 配置 `core.autocrlf=input`
- [ ] **时区**：数据库存 UTC，前端转换显示
- [ ] **临时文件**：使用 `tempfile` 模块
- [ ] **Docker**：能在 Windows Docker Desktop / Linux Docker 都启动
- [ ] **权限**：不依赖 Linux 文件 mode 做业务逻辑

### 5.4 前端质量门

- [ ] **token**：grep `.vue` 文件无 `#[0-9a-fA-F]{3,6}` 颜色值（除 SVG 内）
- [ ] **token**：grep `.vue` 文件 padding/margin 值都是 `var(--space-*)`
- [ ] **组件**：grep 无第三方 UI 库引入（除 Element Plus）
- [ ] **图标**：grep 无 FontAwesome / Iconify 引入
- [ ] **响应式**：grep 无 `@media` 查询
- [ ] **设计模板**：新页面来自 `src/design/` 派生，README 已更新
- [ ] **TypeScript**：无 `any` 类型（特殊场景注释说明）

### 5.5 阶段专属质量门

**v0.1 完成时**：
- [ ] 三种启动方式（本地后端+前端 / Docker / 仅后端）都通过
- [ ] 登录流程完整可用
- [ ] 9 个 Design 文件齐全
- [ ] tokens.css 与 element-theme.scss 已对齐

**v0.3 完成时（nmap 导入核心）**：
- [ ] 上传一个真实 nmap XML 能完整走通流程
- [ ] 资产匹配算法准确（MAC 优先、hostname+OS 次之）
- [ ] 端口快照正确入库

**v0.5 完成时（审计）**：
- [ ] audit_log 表覆盖所有写操作
- [ ] 三个角色的权限隔离完全正确
- [ ] 审计员能导出报告

**v0.6 完成时（拓扑图）**：
- [ ] LLM 脱敏管道无遗漏（grep 真实 IP/主机名是否出现在 sanitized_request）
- [ ] llm_call_logs 每次调用都有记录
- [ ] 本地 Ollama 模式可用

**v1.0 发布前**：
- [ ] 完整 README 和 docs/
- [ ] Docker 镜像可发布
- [ ] 离线安装包测试通过

---

## 6. 协作工作流（Kiro + Claude + 开发者）

### 6.1 标准工作流

```
开发者：定义 Task（参考 Playbook 第 3 章模板）
   ↓
Kiro：根据 Task 编排，调用 Claude 生成代码
   ↓
Claude：基于 Playbook + PRD + 已有代码 生成
   ↓
开发者：人工 review 关键文件（schema、security、permission）
   ↓
开发者：本地运行测试，必要时让 Claude 修改
   ↓
开发者：执行 Alembic 迁移、依赖安装等"禁区"操作
   ↓
开发者：git commit（按 Playbook 1.6 格式）
   ↓
进入下一 Task
```

### 6.2 何时绕过 Claude 直接手写

- 修改 Alembic 迁移文件
- 修改 `.env.production` / `docker-compose.yml` 生产配置
- 修改 `requirements.txt` / `package.json` 版本号
- 调试时的临时修改（之后再让 Claude 写正式版）
- 涉及业务判断的复杂逻辑（如 nmap 匹配算法的具体阈值调整）

### 6.3 何时强制让 Claude 重做

- 违反 Playbook 1.1 引入新库 → 重做
- 违反 Playbook 1.2 文件位置错误 → 重做
- 违反 Playbook 2.1 硬编码颜色 → 重做
- 跳过权限检查或审计埋点 → 重做

### 6.4 Playbook 修订流程

本文档会随项目演进。每次修订流程：

1. 开发者发现 Playbook 没覆盖的问题（如某个新规约）
2. 在本文档对应章节增补
3. 文档顶部"最后更新"日期+1
4. 修订内容用 `【vN.M 新增】` 标记
5. 下次调用 Claude 时使用新版本

**预计修订点**：
- v0.1 完成后：补充 Windows / Docker 实际踩坑
- v0.3 完成后：补充 nmap 解析的细节规约
- v0.5 完成后：补充审计埋点的统一封装方式
- v0.6 完成后：补充 LLM 调用的更详细规约

---

## 7. 速查清单（Cheat Sheet）

### 7.1 调用 Claude 前的检查清单

- [ ] 已附带 Playbook 第 1 章项目宪法
- [ ] 已附带 Playbook 第 2 章前端契约（如涉及前端）
- [ ] 已附带本 Task 直接相关的 PRD 章节
- [ ] 已附带依赖的已有代码文件
- [ ] 明确写出"不要做什么"

### 7.2 review 代码时的检查清单

- [ ] 技术栈合规（无未授权依赖）
- [ ] 目录结构合规
- [ ] 命名规范合规
- [ ] 错误处理合规
- [ ] 权限检查到位
- [ ] 审计埋点到位
- [ ] 前端无硬编码 token
- [ ] 跨平台兼容（pathlib、编码、时区）
- [ ] 测试已写

### 7.3 提交前的检查清单

- [ ] lint 通过
- [ ] 测试通过
- [ ] 类型检查通过
- [ ] 提交信息符合规范
- [ ] 无敏感信息泄露（密码、token、真实 IP）
- [ ] README / 文档同步更新（如适用）

---

## 8. 附录

### 8.1 项目宪法精简版（贴给 Claude 用）

如需在上下文紧张时只贴极简版宪法，使用以下 200 行精简版：

```
【CMDB Lite 项目宪法 - 精简版】

技术栈（不允许变更）：
后端：Python 3.11+, FastAPI, SQLAlchemy 2.0, Pydantic v2, SQLite/WAL, Alembic,
      python-libnmap, defusedxml, argon2-cffi, python-jose, pytest
前端：Vue 3 Composition API, TypeScript 严格模式, Vite, Pinia, Element Plus,
      @element-plus/icons-vue, axios, dayjs, echarts, pnpm

目录结构（不允许偏离）：
backend/app/{routers,schemas,models,services,repositories,utils,core}/
frontend/src/{views/<module>,components/<module>,api,stores,types,styles,design}/

命名（严格遵守）：
Python：文件 snake_case，类 PascalCase，函数/变量 snake_case，常量 UPPER_SNAKE
TS：文件 camelCase/PascalCase(Vue)，类型 PascalCase，函数/变量 camelCase
DB：表复数 snake_case，字段 snake_case
API：kebab-case 复数
CSS 变量：kebab-case 带 -- 前缀

错误处理：
- Service 层抛 CMDBException 子类，不返回 None
- Router 层不写 try/except，依赖全局处理器
- 前端业务组件不写 try/catch 处理 HTTP，axios 拦截器处理

日志：
- 使用 logging 模块，JSON 输出 stdout
- 禁止 print
- 禁止日志包含密码/token/未脱敏 IP

禁区（绝对不做）：
- 引入未授权的库
- 创建 Alembic 迁移
- 修改生产配置
- 删除任何已有文件
- 修改 .gitignore/pyproject.toml/vite.config.ts
- 前端组件硬编码颜色/字号/间距
- 跳过权限检查
- 跳过 audit_log 埋点

前端铁律：
- 所有视觉常量来自 src/styles/tokens.css，组件中用 var(--xxx)
- UI 组件唯一来源 Element Plus
- 图标唯一来源 @element-plus/icons-vue
- 新页面从 src/design/ 模板派生
- 不写 @media（v1.0 仅桌面端）
- 所有 .vue 文件 <script setup lang="ts">

跨平台铁律：
- 路径全用 pathlib.Path
- 文件 IO 显式 encoding="utf-8"
- 时区数据库存 UTC
- 临时文件用 tempfile
```

### 8.2 Task 卡片模板

```markdown
### Task <版本>-<编号>：<任务名>

**前置依赖**：<前置 Task>

**输入**：
- <已有的文件>
- <参考的 PRD 章节>

**输出**：
- <要产出的文件清单>

**验收标准**：
- <可验证的具体条件>

**给 Claude 的 Prompt 模板**：
\`\`\`
[附带：Playbook 第 X 章]
[附带：PRD 第 X.X 节]
[附带：已有的相关代码]

任务：<一句话目标>

要求：
1. ...
2. ...

不要做：
- ...
\`\`\`
```

### 8.3 推荐的 Kiro Workspace 设置

- **System Prompt**：附录 8.1 项目宪法精简版
- **Always-attach files**：
  - `CMDB-Lite-PRD-v2.md`（PRD 全文）
  - `CMDB-Lite-Playbook-v1.md`（本文档）
- **Project context root**：项目根目录
- **Exclude from context**：`data/`、`uploads/`、`node_modules/`、`.venv/`、`*.db`

---

---

## 9. 踩坑记录【v0.1 开发中持续更新】

### 9.1 alembic.ini 中文注释导致 GBK 解码失败【v0.1-02】

**现象**：Windows 上执行 `alembic revision --autogenerate` 报 `UnicodeDecodeError: 'gbk' codec`。

**原因**：Alembic 用系统默认编码（Windows 为 GBK）读取 `alembic.ini`，文件中有中文注释。

**解决**：`alembic.ini` 中不写中文注释，保持纯 ASCII。

---

### 9.2 pytest 内存 SQLite 测试数据库隔离问题【v0.1-03】

**现象**：HTTP 接口测试（通过 `TestClient`）报 `no such table: users`，但纯 Service 层测试正常。

**根本原因**：`sqlite:///:memory:` 每次建立新连接都是独立的空数据库。`TestClient` 内部的请求走 FastAPI 的 `get_db` 依赖，虽然已经 `dependency_overrides`，但如果 engine 没有用 `StaticPool`，每次 `connect()` 拿到的是不同的内存 DB 实例，`create_all` 建的表对请求不可见。

**解决**：测试 engine 必须使用 `StaticPool`：

```python
from sqlalchemy.pool import StaticPool

engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,  # 所有连接共享同一底层连接
)
```

**规约**：所有需要 `TestClient` 的测试，`conftest.py` 的 `db_engine` fixture 必须加 `poolclass=StaticPool`。

---

### 9.3 logging extra 字段不能使用 LogRecord 保留字【v0.1-03】

**现象**：异常 handler 调用 `logger.warning(..., extra={"message": ...})` 时抛 `KeyError: "Attempt to overwrite 'message' in LogRecord"`。

**原因**：Python logging 的 `LogRecord` 有一批保留字段（`message`、`name`、`args` 等），`extra` 字典中不能包含同名 key。

**解决**：`extra` 中的业务字段避开保留字，例如用 `exc_message` 代替 `message`。

**规约**：所有 `logger.xxx(..., extra={...})` 调用，key 不得使用以下保留字：
`name, msg, args, levelname, levelno, pathname, filename, module, exc_info, exc_text, stack_info, lineno, funcName, created, msecs, relativeCreated, thread, threadName, processName, process, message, taskName`

---

### 9.4 测试环境需跳过 startup 的真实数据库初始化【v0.1-03】

**现象**：`TestClient` 启动时触发 `on_startup`，其中 `ensure_initial_admin` 使用真实 `SessionLocal`（指向文件数据库），与测试内存数据库无关，导致表不存在报错。

**解决**：在 `app/core/config.py` 中增加 `APP_ENV` 配置项，`on_startup` 检测到 `APP_ENV=testing` 时跳过初始化。`conftest.py` 在 import app 之前设置 `os.environ["APP_ENV"] = "testing"`。

**规约**：所有在 startup/shutdown 中访问数据库的逻辑，必须支持 `APP_ENV=testing` 跳过。

---

### 9.5 python-libnmap 对 osmatch/osclass 格式要求严格【v0.3】

**现象**：测试用的简化 nmap XML 中 `<osmatch>` 缺少 `<osclass>` 子元素或缺少 `accuracy` 属性，python-libnmap 抛 `Cannot create NmapOSClass: missing required key`。

**解决**：测试样本 XML 中的 `<osmatch>` 必须包含完整的 `<osclass>` 子元素，且 `accuracy` 属性必须存在。格式：
```xml
<os><osmatch name="Linux 5.x" accuracy="95" line="1">
  <osclass type="general purpose" vendor="Linux" osfamily="Linux" osgen="5.X" accuracy="95"/>
</osmatch></os>
```

**规约**：编写 nmap XML 测试样本时，要么完全省略 `<os>` 元素，要么提供完整格式。

---

## 10. 开发进度记录

| 阶段 | 模块 | 状态 | 测试数 | 备注 |
|------|------|------|--------|------|
| v0.1-01 | 项目骨架 | ✅ | - | |
| v0.1-02 | FastAPI 基础框架 | ✅ | - | |
| v0.1-03 | 用户模型与鉴权 | ✅ | 18 | |
| v0.1-04 | 前端 Vue 3 脚手架 | ✅ | - | |
| v0.1-05 | Claude Design 模板 | ⚠️ | - | 6/9 完成，缺 07-10 |
| v0.1-06 | 登录页与主框架 | ✅ | - | |
| v0.1-07 | Docker 配置 | ✅ | - | |
| v0.2 | 资产 CRUD 后端 | ✅ | 21 | |
| v0.2 | 资产 CRUD 前端 | ✅ | - | 列表/详情/表单页 |
| v0.3 | nmap 解析 + diff 引擎 | ✅ | 9 | |
| v0.3 | 扫描批次 API | ✅ | - | |
| v0.3 | 前端 API 封装 | ✅ | - | 仅 api/scan.ts + types |
| v0.3 | 前端冲突解决页 | ⏸️ | - | 等 Design 07 |
| v0.5 | 审计日志 + 用户管理 API | ✅ | - | 含审计埋点 |
| v0.5 | 资产/扫描路由审计埋点 | ✅ | - | CREATE/UPDATE/DELETE/EXPORT |
| v0.5 | 前端审计/用户页面 | ⏸️ | - | 等 Design 09-10 |
| v0.6 | 脱敏管道 sanitize_service | ✅ | - | |
| v0.6 | LLM 抽象层 llm_service | ✅ | - | OpenAI/Claude/Ollama |
| v0.6 | 拓扑图 API + 版本管理 | ✅ | - | |
| v0.6 | 拓扑图前端 | ⏸️ | - | 等 Design 08 |
| v0.7 | 安全报表 API（4 个接口） | ✅ | - | 端口暴露/危险端口/影子资产/变化 |
| v0.7 | 系统配置 API | ✅ | - | KV 存储 + 默认值 |
| v0.7 | 前端报表页面 | ⏸️ | - | 等 Design 09 |

**当前测试总计：48 passed，0 failed。**

---

**文档结束**

> v1.0 是本手册的初始版本。预计在 v0.1 阶段完成后会有第一次大修订，补充实战中发现的问题。修订时严格保留旧版本号的"已废弃"标记，方便回溯。

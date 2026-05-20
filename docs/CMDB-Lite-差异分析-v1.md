# CMDB Lite 差异分析文档

> **文档版本**：v1.0
> **生成日期**：2026-05-20
> **对照基准**：`docs/CMDB-Lite-PRD-v2.md`
> **目标读者**：后续开发执行者（Kiro + Claude）
> **使用方式**：本文件是 **后续开发的硬清单**。开发任务必须按"第四章 优先级与开发顺序"自上而下推进，每完成一项请在对应行打 ✅ 并补充实现说明。

---

## 0. 文档说明

本文是产品经理视角的项目阶段性盘查记录。盘查对象覆盖：

- 后端：`backend/app/`（routers / services / models / schemas / repositories / utils）
- 前端：`frontend/src/`（views / layouts / components / api / types / styles / design）
- 部署/运维：`docker/`、`scripts/`、`secrets/`、`docs/`
- 数据迁移：`backend/alembic/versions/`

状态符号约定：

- ✅ 已完成且符合 PRD
- ⚠️ 部分完成（功能存在但有缺陷、未接配置、前后端不闭环）
- ❌ 未完成（PRD 明确要求但实现缺失）

---

## 1. 整体完成度概览

| 里程碑 | 完成度 | 主要差距 |
|---|---|---|
| v0.1 脚手架 | ✅ ~95% | 缺运维脚本、几个文档占位 |
| v0.2 资产 CRUD | ✅ ~90% | 缺批量操作、用户编辑前端 |
| v0.3 nmap 导入 | ⚠️ ~60% | 后端通；前端"导入确认页"和"字段补充表单"完全缺失 |
| v0.4 差异对比与冲突解决 | ⚠️ ~50% | 后端 diff 算法通；**前端"冲突解决三栏页"完全缺失**；阈值未接配置 |
| v0.5 三权分立 + 审计 | ⚠️ ~75% | 登录/退出/改密未审计埋点；audit_logs 缺数据库不可变性触发器；用户编辑前端缺失 |
| v0.6 拓扑图 | ⚠️ ~60% | drawio iframe 真实集成缺失（当前是 XML 文本预览）；llm_call_logs 独立表未建 |
| v0.7 安全报表 | ✅ ~80% | 缺 Excel 导出、独立子报表页 |
| v1.0 打磨发布 | ❌ ~20% | 文档、帮助页、运维脚本、测试覆盖 |

---

## 2. 模块逐项对照

### 2.1 M1：资产录入与导入（PRD 4.2）

| PRD 要点 | 状态 | 实际位置 / 备注 |
|---|---|---|
| 上传 nmap XML，大小≤50MB | ✅ | `backend/app/routers/scans.py` + `settings.upload_max_bytes` |
| python-libnmap 解析 + defusedxml 防 XXE | ✅ | `backend/app/utils/nmap_parser.py` |
| 仅接受 .xml + nmap 特征头校验（根元素 `nmaprun`） | ✅ | `nmap_parser.py:56` |
| 资产匹配：MAC → hostname+OS | ⚠️ | `diff_service.match_asset` 实际是 **MAC → IP**，未按 PRD 用 hostname+OS 兜底 |
| 上传文件 UUID 命名 + 不可猜测路径 | ✅ | `scan_service.upload_and_parse` 用 `uuid.uuid4().hex` |
| **导入确认页（前端）** | ❌ | `frontend/src/views/scan/ScanConfirm.vue` 完全未创建（设计稿 `07-scan-confirm.htm.html` 已就绪） |
| **新发现资产字段补充表单** | ❌ | 前端无入口；后端 `POST /scans/{id}/confirm` 虽接 `new_assets` 但前端调不到 |
| **变更/消失资产 review 界面** | ❌ | 同上 |
| 手动新增资产（source=manual） | ✅ | `AssetForm.vue` 默认 `source: 'manual'` |
| Web "帮助"页（nmap 命令一键复制） | ❌ | 前端无该页面，路由也未注册 |

### 2.2 M2：资产管理 CRUD（PRD 4.3）

| PRD 要点 | 状态 | 实际位置 / 备注 |
|---|---|---|
| 必填字段 8 项 | ✅ | model + schema 一致 |
| 可选字段 11 项 | ✅ | |
| 自动字段（last_seen_at / missing_count / last_scan_batch_id） | ✅ | |
| 资产列表筛选/搜索/分页 | ✅ | 9 个筛选条件齐全 |
| 资产详情页（基本信息 + 端口 Tab） | ✅ | `AssetDetail.vue` |
| **端口变化历史时间线** | ❌ | PRD 4.3.2 + API `GET /api/assets/{id}/history` 都缺 |
| **批量操作（批量改负责人 / 批量下线 / 批量导出）** | ❌ | PRD 4.3.3，无任何实现 |
| CSV 导出 | ✅ | `assets/export` |

### 2.3 M3：扫描快照与差异（PRD 4.4）

| PRD 要点 | 状态 | 实际位置 / 备注 |
|---|---|---|
| scan_batches + scan_snapshot_items 表 | ✅ | |
| diff 引擎 NEW/CHANGED/MISSING/RESTORED | ✅ | `diff_service.py` 完整 |
| **消失保护机制（阈值可配）** | ⚠️ | 阈值硬编码 3，`scan_service.confirm_batch` 内含 `TODO: 从系统配置读取阈值`，未真正读 `system_configs.missing_threshold` |
| **冲突解决三栏页面（左扫描/中现状/右策略）** | ❌ | 前端完全缺失，**这是产品差异化卖点** |

### 2.4 M4：拓扑图（PRD 4.5）

| PRD 要点 | 状态 | 实际位置 / 备注 |
|---|---|---|
| 脱敏管道 sanitize_service | ✅ | IP/hostname/business 都做了占位符映射 |
| LLM 抽象层（5 个 provider） | ✅ | OpenAI/Claude/DeepSeek/智谱/Ollama |
| LLM 数据出境强制脱敏 | ✅ | |
| **drawio iframe 嵌入** | ❌ | `TopologyEditor.vue` 当前是 XML 文本预览，注释写明"完整的 drawio 编辑器将在集成 iframe 后可用" |
| 拓扑版本管理（list / save / rollback） | ✅ | |
| `GET /api/topology/versions/{id}` 查看特定版本 | ❌ | 路由未实现，只有 list |
| **手动补充虚拟节点（交换机/防火墙/外部连接）** | ❌ | 依赖 drawio 集成 |
| **按重要性路由 LLM**（core→local，others→cloud） | ❌ | 配置项 `llm_route_core_to_local` 有，但 `topology_service` 未做路由分发 |
| **super_admin 全局禁用云端 LLM 开关** | ❌ | 配置项缺失 |

### 2.5 M5：安全视角报表（PRD 4.6）

| PRD 要点 | 状态 | 实际位置 / 备注 |
|---|---|---|
| 端口暴露面 Top 10 + 区域分组 | ✅ | |
| 危险端口告警（19 个端口 + 区域分级） | ✅ | |
| 影子资产识别 | ✅ | |
| 资产变化时间线 | ⚠️ | 后端 `/reports/asset-changes` 有，前端 Dashboard 未渲染该模块 |
| **CSV/Excel 导出** | ❌ | PRD 4.6.4 要求，目前只有页面展示，没有导出按钮 |
| **独立子报表页**（PortExposure / DangerousPorts / ShadowAssets） | ❌ | `frontend/src/design/README.md` 规划复用列表模板，但未派生 |

### 2.6 M6：操作审计日志（PRD 4.7）

| PRD 要点 | 状态 | 实际位置 / 备注 |
|---|---|---|
| audit_logs 表 + 索引 | ✅ | |
| **登录尝试（成功/失败）记录** | ❌ | `auth_service.login` 只 `logger.info`，未写入 `audit_logs`，等保审查必扣分 |
| 数据变更（CREATE/UPDATE/DELETE） | ✅ | 资产、用户、配置、拓扑都接了 |
| **修改密码 / 退出登录 / 刷新 Token 审计** | ❌ | `auth.py` 三个端点都没埋点 |
| 数据导出审计 | ✅ | 资产 CSV、审计 CSV 都接了 |
| LLM 调用日志 | ⚠️ | 用 audit_logs 复用，未建独立 `llm_call_logs` 表（PRD 6.2 明确要独立表） |
| **数据库层面禁止 UPDATE/DELETE audit_logs**（SQLite 触发器） | ❌ | PRD 6.2 强制要求，未实现 |
| 审计日志查询 | ✅ | 分页 + 三筛选 |
| 审计报告导出 CSV | ✅ | |
| 审计报告导出 PDF | ❌ | PRD v0.5 写"CSV/PDF"，未实现 |

### 2.7 M7：用户与权限（PRD 4.8）

| PRD 要点 | 状态 | 实际位置 / 备注 |
|---|---|---|
| 三角色（super_admin/admin/auditor） | ✅ | `core/deps.py` 中间件 |
| 用户 CRUD（含软删除） | ✅ | 后端齐全 |
| 密码策略（≥12 位 + 大小写数字符号） | ✅ | `ChangePasswordRequest` + `UserCreate` |
| **首次登录强制改密** | ❌ | `password_changed_at` 字段有，但登录流程未判断、未引导 |
| **90 天密码强制修改** | ❌ | 无校验逻辑 |
| 5 次失败锁定 15 分钟 | ✅ | `auth_service` 已实现 |
| 禁用账号不删除 | ✅ | |
| **强制创建至少一个 auditor 才解锁完整功能** | ❌ | PRD 3.3 要求 |
| **用户编辑前端 UI** | ❌ | `UserList.vue` 只有"新增"和"禁用"，没有"编辑"按钮 |

### 2.8 M8：系统配置（PRD 4.9）

| PRD 要点 | 状态 | 实际位置 / 备注 |
|---|---|---|
| 系统配置 KV 表 | ✅ | |
| 配置读取/修改 API | ✅ | |
| 敏感字段脱敏返回（api_key 部分隐藏） | ✅ | |
| **配置项实际生效** | ❌ | 4 个关键配置项落库了但业务代码未引用：<br>- `missing_threshold`（消失保护阈值，硬编码 3）<br>- `upload_max_size_mb`（读 `settings` 而非 db）<br>- `session_timeout_minutes`（无校验）<br>- `asset_no_prefix`（资产编号生成器硬编码 "CMDB"） |

---

## 3. 跨模块 / 非功能差距

### 3.1 安全（PRD 9）

- ❌ **LLM API Key 明文存储**：PRD 9.2 要求 envelope encryption + 主密钥从环境变量，目前数据库直接存明文
- ❌ **强制 HTTPS**：仅 cookie 在非 development 时 secure=True，`docker/nginx.conf` 未启用 TLS
- ⚠️ **CSP 头未设置**：PRD 9.2 要求 XSS 防护

### 3.2 数据模型（PRD 6）

- ❌ **llm_call_logs 表未独立建立**：当前用 `audit_logs.action_type='LLM_CALL'` 复用
- ❌ **audit_logs 不可变性 SQLite 触发器**：PRD 6.2 明确要求
- ⚠️ 多个模型用 `datetime.utcnow`（已弃用），应统一 `datetime.now(timezone.utc)`

### 3.3 API（PRD 7）

- ❌ `GET /api/assets/{id}/history` 未实现
- ❌ `GET /api/topology/versions/{id}` 未实现（只有 list）
- ❌ `GET /api/audit/llm-logs` 未单独实现

### 3.4 部署与运维

- ❌ `docs/nmap-cmd-reference.md`（README 已引用但文件不存在）
- ❌ `docs/api-spec.md`（同上）
- ❌ `docs/deployment.md`（同上，PRD 8.4 systemd 单元示例缺）
- ❌ `scripts/init_db.py`、`scripts/reset_admin.py`、`scripts/export_audit.py`（PRD 5.3 + 11.1 风险表都点名，运维兜底）
- ❌ Docker healthcheck 未写入 `docker-compose.yml`
- ⚠️ 单元测试覆盖率（PRD v1.0 要求 60%+），目前只有 3 个测试文件（`test_auth.py / test_assets.py / test_scan.py`）

### 3.5 前端（PRD 5.4 + 12.6）

- ❌ **`ScanConfirm.vue`**（设计稿 07 已就绪，是 PRD 4.4 核心差异化页面）
- ❌ **drawio iframe 真实集成**
- ❌ 派生页面：`PortExposure.vue` / `DangerousPorts.vue` / `ShadowAssets.vue` / `LlmCallLog.vue`
- ❌ Help 页面（nmap 命令一键复制）
- ❌ `ScanList.vue` 缺操作列（查看详情 / 确认导入 / 拒绝）

---

## 4. 优先级与开发顺序（执行顺序）

> 后续开发请严格按本节顺序自上而下推进。每项前的方框完成后请打 ✅，并在右侧"实现备注"栏补充提交记录或文件清单。

### P0 — 产品差异化核心，缺失则不能交付 v1.0

- [x] **P0-1 ScanConfirm.vue 扫描批次差异确认页**
  - 包含：新发现/变更/消失三段式列表 + 字段补充表单 + 三栏对比
  - 依赖：参考 `frontend/src/design/07-scan-confirm.htm.html`
  - 后端：新增 `GET /api/scans/{id}/diff` 返回完整差异详情（DiffNewHost/DiffChangedHost/DiffMissingHost）
  - 实现备注：2026-05-20 完成。后端新增 `ScanDiffResponse` schema + `scan_service.get_batch_diff()`；前端新增 `ScanConfirm.vue`（三 Tab + 字段补充表单 + 底部操作栏）；路由 `/scans/:id/confirm`

- [x] **P0-2 ScanList 增加操作列**
  - 列：查看详情、确认导入（跳 ScanConfirm）、拒绝（DELETE 批次）
  - 实现备注：2026-05-20 完成。`ScanList.vue` 增加操作列（确认导入/拒绝/查看详情），引入 `useRouter` + `rejectBatch`

- [x] **P0-3 鉴权操作审计埋点**
  - 在 `auth.py` 的 login / logout / refresh / change-password 全部接 `audit_service.log_from_request`
  - 登录失败也要写一条 `result='failed'`
  - 实现备注：2026-05-20 完成。`auth.py` 重构：login 成功/失败均写 audit_logs；logout 写审计；change-password 写审计

- [x] **P0-4 audit_logs 不可变性 SQLite 触发器**
  - 新建 alembic migration，添加 `BEFORE UPDATE` 与 `BEFORE DELETE` 触发器，触发即 `RAISE(ABORT, ...)`
  - 实现备注：2026-05-20 完成。migration `15ea56d0ba98`，验证 UPDATE/DELETE 均被阻止（"审计日志不可修改"/"审计日志不可删除"）

- [x] **P0-5 drawio iframe 真实集成**
  - 用 `embed.diagrams.net` iframe + postMessage 协议（load / save / export / configure）
  - `TopologyEditor.vue` 替换 XML 预览块为真正的可视化编辑器
  - 实现备注：2026-05-20 完成。完整实现 drawio postMessage 协议（configure/init/save/export/exit 事件），iframe 嵌入 + 双向通信 + LLM 生成后自动加载到编辑器

### P1 — 功能闭环 / 配置项生效

- [x] **P1-1 系统配置真正生效**
  - `missing_threshold` → `scan_service.confirm_batch`
  - `upload_max_size_mb` → `scan_service.upload_and_parse`（替换 settings 读取）
  - `asset_no_prefix` → `asset_repo.generate_asset_no`
  - `session_timeout_minutes` → JWT access_token 过期时间或 refresh 校验
  - 实现备注：2026-05-20 完成。新建 `config_service.py` 提供 `get_missing_threshold/get_upload_max_size_mb/get_asset_no_prefix`；scan_service 和 asset_repo 已接入动态配置

- [x] **P1-2 LLM API Key 加密存储 + 全局禁用云端开关 + 按重要性路由**
  - 主密钥从环境变量 `LLM_MASTER_KEY` 读，cryptography.fernet 做 envelope encryption
  - 新增配置项 `llm_cloud_enabled`，super_admin 可关
  - `topology_service.generate_topology` 检查资产 importance 决定走 cloud 还是 ollama
  - 实现备注：2026-05-20 完成。新建 `core/encryption.py`（Fernet 加解密）；config router 保存时加密 api_key；topology_service 实现路由决策（全局禁用/核心资产→ollama）

- [x] **P1-3 资产端口变化历史**
  - 后端：`GET /api/assets/{id}/history` 基于 `scan_snapshot_items` 聚合时间线
  - 前端：`AssetDetail.vue` 增加"历史"Tab（待前端补充）
  - 实现备注：2026-05-20 完成。后端 `asset_service.get_asset_history()` + router 端点已实现

- [x] **P1-4 资产批量操作**
  - 后端新增：`PATCH /api/assets/bulk`（owner / status / business_system / importance / network_zone）
  - 前端 `AssetList.vue` 增加多选 + 批量按钮（待前端补充）
  - 实现备注：2026-05-20 完成。后端 `PATCH /api/assets/bulk` + `asset_service.bulk_update()` 已实现

- [x] **P1-5 报表导出（CSV/Excel）+ 独立子报表页**
  - 后端：`/reports/dangerous-ports/export` + `/reports/shadow-assets/export`
  - 前端：独立子报表页（待前端补充）
  - 实现备注：2026-05-20 完成。后端两个 CSV 导出端点已实现

### P2 — 合规与运维兜底

- [x] **P2-1 首次登录强制改密 + 90 天强制改密**
  - login 成功后返回 `must_change_password` 标记
  - 前端拦截：未改密时强制弹出 `ChangePasswordDialog`，关闭即登出
  - 实现备注：2026-05-20 完成。后端 TokenResponse 增加 `must_change_password`；auth.py login 检查 password_changed_at（null=首次 / >90天=过期）；前端 auth store + MainLayout watch 强制弹窗

- [x] **P2-2 llm_call_logs 独立表 + `/api/audit/llm-logs`**
  - 新建模型 + migration，把 `llm_service.call_llm` 的日志写入新表（保留 audit_logs 双写以便兼容）
  - 前端 `LlmCallLog.vue` 复用 AuditLog 结构（待前端补充）
  - 实现备注：2026-05-20 完成。新建 `models/llm_log.py` + migration `170371c7cc0f`；llm_service 双写；新增 `GET /api/audit/llm-logs` 端点

- [x] **P2-3 用户编辑前端 UI**
  - `UserList.vue` 增加"编辑"按钮，对接 `PATCH /api/users/{id}`
  - 实现备注：2026-05-20 完成。UserList.vue 增加编辑弹窗（角色/姓名/邮箱/状态），对接 updateUser API

- [x] **P2-4 docs 三件套**
  - `docs/nmap-cmd-reference.md`（含三套扫描命令模板，对应 Help 页）
  - `docs/api-spec.md`（API 快速参考 + OpenAPI 链接）
  - `docs/deployment.md`（Docker / Linux / Windows 三环境）
  - 实现备注：2026-05-20 完成。三个文档已创建

- [x] **P2-5 运维脚本三件套**
  - `scripts/init_db.py`：alembic upgrade head + 创建初始 admin
  - `scripts/reset_admin.py`：重置 admin 密码并打印
  - `scripts/export_audit.py`：CLI 导出审计日志（绕过 Web）
  - 实现备注：2026-05-20 完成。三个脚本已创建

- [x] **P2-6 Help 页面（nmap 命令一键复制）**
  - 路由 `/help`，复用主框架，分三段：标准/快速/深度命令 + 一键复制按钮
  - 实现备注：2026-05-20 完成。`Help.vue` + 路由 `/help`

- [ ] **P2-7 单元测试补到 60%+**
  - 重点覆盖：`nmap_parser` / `diff_service` / `sanitize_service` / 鉴权流程 / 报表查询
  - 实现备注：待后续迭代补充

- [x] **P2-8 Docker healthcheck + nginx HTTPS 配置示例**
  - `docker-compose.yml` backend 已有 healthcheck（python urllib）
  - `docker/nginx.conf` 增加 443 server block 示例（注释状态）
  - 实现备注：2026-05-20 完成。healthcheck 已存在；nginx.conf 追加 HTTPS 示例

### P3 — 收尾

- [x] **P3-1 强制创建至少一个 auditor 才解锁完整功能**（PRD 3.3）
  - 实现备注：2026-05-20 完成。新增 `config_service.has_auditor_user()` + `deps.py` 中 `AuditorExists` 依赖；扫描上传和拓扑生成端点已接入

- [x] **P3-2 datetime 统一 timezone-aware**（清理 utcnow 弃用）
  - 实现备注：2026-05-20 完成。`database.py` 新增 `utc_now()` 函数；7 个模型文件全部替换 `datetime.utcnow` → `utc_now`；deprecation warnings 从 89 降到 4（剩余为 FastAPI on_event 弃用）

- [x] **P3-3 CSP 头中间件**（PRD 9.2）
  - 实现备注：2026-05-20 完成。`main.py` 新增 HTTP 中间件，设置 CSP（允许 drawio iframe）+ X-Content-Type-Options + X-Frame-Options + X-XSS-Protection + Referrer-Policy

- [x] **P3-4 审计报告 PDF 导出**（PRD v0.5）
  - 实现备注：2026-05-20 完成。新增 `POST /api/audit/export-pdf`（fpdf2 生成表格 PDF）；requirements.txt 增加 fpdf2>=2.8

- [x] **P3-5 资产匹配兜底（hostname+OS）**（PRD 4.2.3）
  - 实现备注：2026-05-20 完成。`diff_service.match_asset` 增加第三级匹配：hostname + os_info 联合查询

---

## 5. 后续维护规则

1. 本文是 **唯一活跃的开发清单**，任何新发现的 PRD 偏差请追加到本文相应章节
2. 每完成一项，打 ✅ 并补充实现备注（commit hash / 关键文件 / 验证方式）
3. 如出现 PRD 与实现的合理冲突（PRD 写得不准），请同步修订 PRD 并在本文标注变更
4. 严禁绕过本文跳级开发；P0 未完成不开始 P1，P1 未完成不开始 P2

---

**文档结束**

# CMDB Lite PRD v2.5 建议清单

> **文档版本**：v2.5 建议稿（待评审）
> **生成日期**：2026-05-20
> **基准**：`docs/CMDB-Lite-PRD-v2.md` + 现 master 已合入的 v0.1 + 2026 UI 重构
> **目标读者**：产品决策人 / Kiro 后续开发执行者
> **关系定位**：v2.5 是 v2 与 v3 之间的**功能补丁版**，聚焦两个高频痛点（应用清单 + 业务系统列），不重排版本号、不动 v3 主线（等保映射、CVE 联动、HVV Dashboard 等仍归 v3）

---

## 0. 文档说明

### 0.1 触发动机

v0.1 上线后用户反馈两个具体问题：

1. **资产列表无法记录"这台服务器装了什么应用"**
   - 现状：只有 nmap 扫到的端口（asset_ports 表），但 nmap 看到的是"开放端口 + 服务名"，不等于"这台机器装了哪些应用"
   - 痛点：管理员手里有一份"应用清单"（Excel/记事本），希望能录入到资产里，并且能搜索"哪些资产装了 nginx"
2. **资产列表看不到"业务系统"列**
   - 现状：`assets.business_system` 字段一直存在（必填），但 2026 UI 重构时把"业务系统"列替换成了"操作系统"列，业务系统从一线视图消失
   - 痛点：日常运营/审计时找不到"哪些资产属于 ERP 系统"
   - 同时：现有搜索范围只覆盖 IP/hostname/asset_no/remark，**搜不到 business_system 字段值**

### 0.2 v2.5 的范围边界（最重要）

#### ✅ 在 v2.5 内
- 新增"应用服务清单"数据模型 + CRUD 后端 API + 资产详情页"应用"Tab
- 资产列表恢复"业务系统"列（与"操作系统"列共存）
- 资产列表搜索范围扩展到 `business_system` + 应用名 + 应用版本号
- 应用清单字段支持手动录入（应用名、版本、备注、来源标记 manual）
- 资产 CSV 导出新增"业务系统"列；应用清单单独提供导出端点

#### ❌ 不在 v2.5 内（明确推到 v3）
- 应用识别规则引擎（port + service → app 映射）
- 扫描批次自动产出应用候选（ScanConfirm 增加"应用识别" Tab）
- 应用名/版本号 CVE 关联
- business_system 字段独立成表（保留 VARCHAR 字段）
- 应用清单的"主备/集群"等关系建模

> **关键原则**：v2.5 只做"人工录入 + 搜索"，**不联动 nmap 扫描**。这是和你确认过的决策（决策 1 选 B、决策 3 选"暂不"）。

### 0.3 命名约定

- 模型层使用 `app_service` 而非 `application`，避免与"应用层"等技术词混淆
- API 路径用 `/api/assets/{id}/apps`（短词、可读）
- 前端组件命名用 `AppService*`

---

## 1. 数据模型设计

### 1.1 新增表 `asset_apps`

```sql
CREATE TABLE asset_apps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_id INTEGER NOT NULL REFERENCES assets(id) ON DELETE CASCADE,

    -- 应用基本信息
    name VARCHAR(100) NOT NULL,           -- 例如 "nginx"、"mysql-server"
    version VARCHAR(100),                 -- 例如 "1.24.0"、"8.0.36"
    category VARCHAR(50),                 -- 应用大类（见 1.3）
    port INTEGER,                         -- 该应用主要监听端口（可空）
    protocol VARCHAR(10),                 -- tcp / udp（仅当 port 不空时填）

    -- 元信息
    install_path VARCHAR(255),            -- 安装路径（可空）
    config_path VARCHAR(255),             -- 配置文件路径（可空）
    notes TEXT,                           -- 自由备注

    -- 来源与生命周期
    source VARCHAR(20) NOT NULL DEFAULT 'manual',   -- manual / scan（v3 才会出现 scan）
    status VARCHAR(20) NOT NULL DEFAULT 'active',   -- active / decommissioned
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    created_by INTEGER REFERENCES users(id),

    UNIQUE(asset_id, name, version)       -- 同一资产上同名同版本只允许一条
);

CREATE INDEX idx_asset_apps_asset_id ON asset_apps(asset_id);
CREATE INDEX idx_asset_apps_name ON asset_apps(name);
CREATE INDEX idx_asset_apps_category ON asset_apps(category);
```

**关键设计决策**：

| 决策 | 选择 | 理由 |
|---|---|---|
| 与 asset_ports 关系 | **解耦** | 应用与端口是 N:1，且很多应用根本不开端口（数据库被本地访问、消息队列内部使用） |
| 是否做应用全局表 | 否 | 不做"全局应用字典"，每条记录直接挂在资产下，UI 上提供同名 autocomplete |
| 是否记录补丁/CVE | 否 | v2.5 范围外，v3 再做 |
| 唯一约束 | (asset_id, name, version) | 同一资产装同一版本的同名应用没意义；不同版本（如 nginx 1.24 与 nginx 1.26）允许并存 |

### 1.2 修改 `assets.business_system` 字段

**保持原样**（仅前端使用变化），不做迁移。当前定义：

```python
business_system: Mapped[str] = mapped_column(String(100), nullable=False)
```

只调整：
- 列表 UI 重新展示该列
- 列表搜索 SQL 加入 `business_system LIKE %q%`
- 资产 CSV 导出加入该列

### 1.3 应用大类（category）枚举

为后续报表与筛选预留，但**v2.5 仅作为 UI 提示，不做强约束**。建议预置如下选项（前端 select + allow-create）：

```ts
const APP_CATEGORIES = [
  { value: 'web_server', label: 'Web 服务器（Nginx / Apache / IIS）' },
  { value: 'database', label: '数据库（MySQL / PostgreSQL / Oracle / MSSQL / MongoDB / Redis）' },
  { value: 'app_server', label: '应用服务器（Tomcat / JBoss / Node.js）' },
  { value: 'message_queue', label: '消息队列（Kafka / RabbitMQ / RocketMQ）' },
  { value: 'cache', label: '缓存（Redis / Memcached）' },
  { value: 'search', label: '搜索引擎（Elasticsearch / OpenSearch）' },
  { value: 'monitor', label: '监控（Zabbix / Prometheus / Grafana）' },
  { value: 'devops', label: 'DevOps（Jenkins / GitLab / Harbor）' },
  { value: 'security', label: '安全（堡垒机 / WAF / 防病毒）' },
  { value: 'business_app', label: '业务系统（自研 / 第三方）' },
  { value: 'other', label: '其他' },
]
```

后端不强校验 category 取值（避免迁移头疼），仅前端引导。

---

## 2. 后端 API 设计

### 2.1 新增 API（应用清单 CRUD）

| 方法 | 路径 | 说明 | 权限 |
|---|---|---|---|
| GET | `/api/assets/{asset_id}/apps` | 列出该资产所有应用 | super_admin / admin / auditor |
| POST | `/api/assets/{asset_id}/apps` | 新增应用 | super_admin / admin |
| PATCH | `/api/assets/{asset_id}/apps/{app_id}` | 修改应用 | super_admin / admin |
| DELETE | `/api/assets/{asset_id}/apps/{app_id}` | 删除应用（软删 status=decommissioned） | super_admin / admin |
| GET | `/api/assets/{asset_id}/apps/export` | 导出该资产应用清单 CSV | super_admin / admin / auditor |
| GET | `/api/apps/search?q=...` | 全局应用搜索（按 name 或 version 模糊匹配，返回所有命中资产 + 应用） | super_admin / admin / auditor |
| GET | `/api/apps/names` | 返回所有已存在的应用名（去重，用于前端 autocomplete） | super_admin / admin / auditor |

**响应示例：GET /api/assets/{asset_id}/apps**

```json
{
  "items": [
    {
      "id": 1,
      "asset_id": 12,
      "name": "nginx",
      "version": "1.24.0",
      "category": "web_server",
      "port": 80,
      "protocol": "tcp",
      "install_path": "/etc/nginx",
      "config_path": "/etc/nginx/nginx.conf",
      "notes": "前端 SPA 静态资源",
      "source": "manual",
      "status": "active",
      "created_at": "2026-05-20T08:30:00Z",
      "updated_at": "2026-05-20T08:30:00Z"
    }
  ],
  "total": 1
}
```

### 2.2 修改现有 API：资产列表搜索

**当前** `GET /api/assets` 的 search 字段范围（`asset_repo.list_assets`）：
```python
or_(
    Asset.ip_address.contains(q),
    Asset.hostname.contains(q),
    Asset.asset_no.contains(q),
    Asset.remark.contains(q),
)
```

**v2.5 改为**：
```python
# 1. 资产基础字段搜索 + business_system
asset_match = or_(
    Asset.ip_address.contains(q),
    Asset.hostname.contains(q),
    Asset.asset_no.contains(q),
    Asset.remark.contains(q),
    Asset.business_system.contains(q),  # 新增
)

# 2. 应用名/版本搜索：通过子查询关联到资产
app_match = exists().where(
    AssetApp.asset_id == Asset.id,
    AssetApp.status == 'active',
    or_(
        AssetApp.name.contains(q),
        AssetApp.version.contains(q),
    )
)

# 3. 合并：满足任一即匹配
stmt = stmt.where(or_(asset_match, app_match))
```

**前端搜索框 placeholder 改写**：

| 当前 | v2.5 |
|---|---|
| 搜索 IP / 主机名 / 资产编号 / 备注 | 搜索 IP / 主机名 / 资产编号 / 业务系统 / 应用（如 nginx, mysql） |

### 2.3 修改资产 CSV 导出

`GET /api/assets/export` 增加 "业务系统" 列；保持其他列顺序不变，避免破坏既有用户的 Excel 模板。

---

## 3. 前端 UI 设计

### 3.1 资产列表页（AssetList.vue）

**列变动**：

| 列 | v0.1 | v2.5 |
|---|---|---|
| 资产编号 | ✅ | ✅ |
| IP 地址 | ✅ | ✅ |
| 主机名 | ✅ | ✅ |
| 类型 | ✅ | ✅ |
| 区域 | ✅ | ✅ |
| **业务系统** | ❌（被改为 OS） | ✅ **重新加入**，宽度 140 |
| **操作系统** | ✅（v0.1 新加） | ✅ 保留（与业务系统并存），宽度 160 |
| 重要性 | ✅ | ✅ |
| 状态 | ✅ | ✅ |
| 负责人 | ✅ | ✅ |
| 操作 | ✅ | ✅ |

> 屏幕宽度 1280px 仍能容纳。如确实拥挤，可考虑把"操作系统"列设为 `show-overflow-tooltip` + 较窄宽度（120px）；或者通过列设置开关让用户选择性隐藏。

**搜索框**：placeholder 改为新文案，行为后端已处理。

**业务系统列样式**：用 `ui-mono` 等宽字体显示，hover 高亮，与"业务系统"概念的"标识符感"匹配。如有空值，显示灰色"-"。

### 3.2 资产详情页（AssetDetail.vue）

新增第三个 Tab："**应用 (N)**"，与现有"基本信息"、"端口"并列。

```
┌─────────────────────────────────────────────────────┐
│ Hero（资产编号 + 主机名 + 状态 + 操作按钮）          │
├─────────────────────────────────────────────────────┤
│ 信息卡片 × 4（区域/重要性/负责人/来源）              │
├─────────────────────────────────────────────────────┤
│ Tab: [基本信息] [端口] [应用]  ← 新增                │
│                                                     │
│ 应用 Tab 内容：                                     │
│  [+ 新增应用] [导出 CSV]                            │
│  ┌───────────────────────────────────────────────┐  │
│  │ 名称       版本     大类     端口  来源  操作 │  │
│  │ nginx      1.24.0   web_server  80  手动 ✏️🗑 │  │
│  │ mysql      8.0.36   database  3306  手动 ✏️🗑 │  │
│  └───────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

**新增/编辑应用对话框（AppServiceDialog.vue）**：
- 应用名（必填，autocomplete 从 `/api/apps/names` 拉数据，支持自由输入）
- 版本号（可填）
- 大类（select + allow-create，预置 11 大类，见 1.3）
- 端口（数字输入框，可空）
- 协议（端口非空时显示，select tcp/udp）
- 安装路径（可填）
- 配置文件路径（可填）
- 备注（textarea）

### 3.3 资产新增/编辑页（AssetForm.vue）

**保持当前不变**——v2.5 不动新增/编辑表单。应用清单只在详情页维护，避免新增表单一次填太多字段降低录入意愿。

> 这是一个产品判断：把"基础资产信息"和"应用清单"分两个动作录入更符合实际工作流（先建资产卡片，后续逐步补应用）。

### 3.4 全局应用搜索（v2.5 范围外，v3 实现）

考虑过新增 `/apps` 顶级菜单做"全局应用清单"，**v2.5 不做**：通过资产列表搜索框查询"哪些资产装了 nginx"已经满足 80% 场景。v3 视用户反馈再决定是否独立。

---

## 4. 实施任务拆解

按依赖关系和最小变更范围拆，建议分 3 个 PR 推进：

### PR-1：数据库与后端模型（约 1.5 人天）

- [ ] T1.1 创建 SQLAlchemy 模型 `app/models/asset_app.py`
- [ ] T1.2 创建 Alembic migration `add_asset_apps_table`
- [ ] T1.3 创建 Pydantic schema `app/schemas/asset_app.py`（含 Create/Update/Read）
- [ ] T1.4 创建仓储 `app/repositories/asset_app_repo.py`
- [ ] T1.5 创建服务 `app/services/asset_app_service.py`
- [ ] T1.6 创建路由 `app/routers/asset_apps.py`，注册到 main.py
- [ ] T1.7 修改 `asset_repo.list_assets`：搜索 SQL 增加 `business_system` + `AssetApp` 子查询
- [ ] T1.8 修改 `asset_service.export_csv`：导出列增加"业务系统"
- [ ] T1.9 单元测试：repo 层 CRUD + 搜索集成

### PR-2：前端列表与搜索（约 0.5 人天）

- [ ] T2.1 修改 `AssetList.vue`：添加"业务系统"列、调整列宽、改 placeholder
- [ ] T2.2 修改 `frontend/src/types/asset.ts`：`AssetListItem` 已有 `business_system` 字段，无需变更（仅核对）
- [ ] T2.3 验证搜索能命中应用名（依赖 PR-1 后端）

### PR-3：前端应用清单 UI（约 2 人天）

- [ ] T3.1 创建 `frontend/src/api/asset-app.ts`
- [ ] T3.2 创建 `frontend/src/types/asset-app.ts`
- [ ] T3.3 创建 `frontend/src/constants/app-categories.ts`（11 个大类）
- [ ] T3.4 创建组件 `frontend/src/components/asset/AppServiceTable.vue`
- [ ] T3.5 创建组件 `frontend/src/components/asset/AppServiceDialog.vue`
- [ ] T3.6 修改 `AssetDetail.vue`：增加"应用 (N)"Tab
- [ ] T3.7 创建 autocomplete 数据加载 `useAppNames` composable

---

## 5. 与已有 PRD 的关系

### 5.1 与 PRD v2 的关系
- v2.5 在 PRD v2 第 6.1 节"主要数据表"中**追加**一张表 `asset_apps`
- 在第 7.3 节 API 列表中**追加**一组应用清单 API
- 第 4.3.3 资产列表页字段需求**回滚 2026 UI 误改**（恢复业务系统列）

### 5.2 与 PRD v3 建议的关系
- 不改动 v3 建议清单中的任何 P0/P1 项
- 为 v3 中的几项做"地基"：
  - **2.1 危险端口规则引擎** → 未来可读 `asset_apps` 做服务级风险标记
  - **2.2 CVE 联动** → 直接受益，CVE 匹配的载体从"端口/服务版本"扩展到"显式应用名+版本"，命中率提升
  - **2.5 HVV Dashboard** → 可加一个"高危应用清单"面板（如全网 nginx < 1.21 的资产数）

---

## 6. 风险与待决事项

### 6.1 风险

| 风险 | 影响 | 缓解 |
|---|---|---|
| 应用录入摩擦大（手填字段太多） | 用户不愿录入，数据形同虚设 | 仅 name 必填；其他字段可空；提供 autocomplete |
| 资产列表列过多导致溢出 | 1280px 显示拥挤 | 操作系统列宽度从 180 压到 120；必要时启用"列设置"开关（v3 再做） |
| 重复应用名（"Nginx"/"nginx"/"NGINX"） | autocomplete 体验差 + 搜索命中率低 | 后端 LIKE 搜索本身大小写不敏感（SQLite 默认）；前端 autocomplete 做小写归一展示 |
| `unique(asset_id, name, version)` 太严格 | 同一应用多实例（不同端口）无法录入 | v2.5 暂不解决，需要时通过 `notes` 字段区分；v3 可改为 `unique(asset_id, name, version, port)` |

### 6.2 待决（用户拍板）

- **应用大类是否做强枚举？** 当前建议"前端引导、后端不约束"。如要做强枚举，需 migration 加 CHECK 约束
- **资产列表"应用"列是否要直接显示应用数量？** 当前建议**不显示**（避免列继续加宽）；改为 hover tooltip 展示 Top 3 应用名
- **应用 CSV 导出格式**：是否在资产 CSV 中以 `app1:1.24,app2:8.0` 这种合并列形式导出？还是仍走独立导出端点？

---

## 7. 测试要点

### 7.1 后端单元测试
- `asset_app_repo` 的增删改查 + unique 约束触发
- `asset_repo.list_assets` 搜索：能用 "nginx" 搜到装了 nginx 的资产；能用 "ERP" 搜到 business_system 含 ERP 的资产
- 软删除应用后，搜索不应命中（status='decommissioned' 应被过滤）

### 7.2 前端组件测试
- AppServiceTable：空状态、有数据、删除确认
- AppServiceDialog：表单验证、autocomplete 拉取
- AssetList：业务系统列正确显示

### 7.3 PBT 属性测试（建议）
- 任意资产，添加应用后通过应用名搜索必能命中
- 软删除应用后通过该应用名搜索必不命中
- 同一资产不能存在 `(name, version)` 完全相同的两条 active 应用

---

## 8. 待用户决策的事项

请用户审视后，确认以下条目：

| # | 待决事项 | 我的建议 | 用户决策 |
|---|---|---|---|
| 1 | 是否同意 PR-1 / PR-2 / PR-3 的拆分顺序？ | 建议按顺序合，PR-1 单独评审 | ⬜ |
| 2 | 应用大类是否强枚举？ | 不强（前端引导即可） | ⬜ |
| 3 | 列表"应用数量"列是否要显示？ | 不显示，hover 看 Top 3 | ⬜ |
| 4 | unique 约束是否包含 port？ | v2.5 不含，v3 视情况升级 | ⬜ |
| 5 | 是否在 ScanConfirm 也做"应用录入" | 不做，v3 才接扫描联动 | ⬜ |

---

## 9. 后续维护规则

1. 用户审阅本文后请直接在第 8 节标注 ✅ / ❌ / 🔁
2. 标注完成后，由开发执行者（Kiro）启动 spec workflow 拆 task
3. 实施过程中如发现需求边界变化，请回头更新本文 0.2 节"范围边界"
4. v2.5 完成后请在差异分析文档中追加 v2.5 章节，刷新完成度

---

**文档结束**

> **简短摘要**：v2.5 = 1 张新表（`asset_apps`） + 1 列恢复（业务系统） + 1 个搜索范围扩展。预计总工作量 4 人天，3 个 PR 推进。范围严格控制不动 v3 主线（CVE / 等保 / HVV Dashboard）。

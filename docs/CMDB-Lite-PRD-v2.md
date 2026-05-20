# CMDB Lite 产品需求文档（PRD）

> **项目代号**：CMDB Lite
> **文档版本**：v2.0
> **文档状态**：开发就绪（Ready for Implementation）
> **目标读者**：开发者（Kiro + Claude Sonnet 4.6 协同开发场景）
> **最后更新**：2026-05-18
> **v2 变更说明**：新增 5.4 节"设计系统与前端规范"；v0.1 阶段任务补充设计 token 提取；新增 12.6 节"前端设计资产清单"。

---

## 0. 文档使用说明

本文档面向 AI 辅助开发场景设计。所有功能描述、数据结构、API 命名均采用明确化、可执行化的表述方式，方便 Kiro 拆解任务、Claude Sonnet 4.6 生成代码。

阅读建议顺序：
1. 第 1～3 章理解产品定位（必读）
2. 第 4 章理解功能边界（必读）
3. 第 5～7 章作为编码依据（开发阶段查阅）
4. 第 8～9 章作为部署依据（部署阶段查阅）
5. 第 10 章作为开发节奏控制（PM 视角）

> **配套文档**：本 PRD 是给开发参考的产品文档。开发执行时请配合 `CMDB-Lite-Playbook-v1.md` 使用——Playbook 是给 Kiro 工作的硬约束规约，PRD 是给 Claude 理解需求的背景文档。两者分工：PRD 回答"做什么"，Playbook 回答"怎么协作做"。

---

## 1. 项目背景与定位

### 1.1 产品定位

**CMDB Lite 是一款"准确性优先、零门槛、面向中小团队"的轻量级配置管理数据库。**

它不对标 ServiceNow、Itop、Easyops 等企业级 CMDB 产品，而是聚焦一个非常具体的使用场景：

> 一个团队（5～50 人规模），需要把内网/办公网/IDC 资产搞清楚，用于日常运维、安全审计、HVV 排查、等保备查。市面上的 CMDB 要么太重、要么需要 Agent、要么自动采集准确度不够。CMDB Lite 选择牺牲"自动化"，换取"准确性"与"可控性"。

### 1.2 核心设计哲学

| 设计取舍 | 选择 | 放弃 |
|---------|------|------|
| 采集方式 | 手动 nmap 扫描后上传 | 自动周期采集 |
| 数据准确性 | 人工 review 兜底 | 全自动化 |
| 部署形态 | 单文件 SQLite + Docker | 分布式 / 集群 |
| 用户群体 | 运维 / 安全 / 中小团队 | 大型互联网企业 |
| 拓扑图 | LLM 生成初稿 + 手动调整 | 全自动生成 |

### 1.3 目标用户

- **主要用户**：中小企业 IT 运维负责人、安全工程师
- **次要用户**：MSP 服务商（给客户做资产梳理）、安全顾问（驻场服务）
- **审计场景**：等保 2.0 测评、ISO 27001 内审、HVV 攻防演练前的资产盘点

### 1.4 差异化价值（相对自动化 CMDB）

1. **数据准确性可信**：所有资产都经过人工确认，不存在"扫错了""漏扫了"没人发现的情况
2. **零部署门槛**：单容器 + SQLite，10 分钟跑起来
3. **安全人员友好**：内置端口暴露面分析、影子资产识别、危险端口告警
4. **审计友好**：完整操作日志 + 审计员独立角色 + 审计报告导出
5. **LLM 数据安全**：调用 LLM 时本地脱敏，敏感信息不出网

---

## 2. 产品目标与非目标

### 2.1 产品目标（v1.0 范围）

- ✅ 提供 nmap XML 报告的解析与导入能力
- ✅ 提供资产的 CRUD 管理（Web 界面）
- ✅ 提供扫描批次的差异对比与冲突解决
- ✅ 提供基于 LLM 的拓扑图初稿生成（含数据脱敏）
- ✅ 提供三权分立的账号体系（超管 / 管理员 / 审计员）
- ✅ 提供完整操作审计日志
- ✅ 提供安全视角报表（端口暴露面、影子资产、危险端口）
- ✅ 支持 Docker 部署、Linux 部署、Windows 开发

### 2.2 明确不做（Non-Goals）

为防止 feature creep，以下功能**明确不在本产品范围内**：

- ❌ 不做自动扫描调度（坚持手动上传以保证准确性）
- ❌ 不做 Agent 端采集
- ❌ 不做云资产纳管（AWS/Azure/阿里云资产应使用各云厂商自有工具）
- ❌ 不做 CI 关系图谱（不是企业级 CMDB）
- ❌ 不做监控告警（不是监控系统，不替代 Zabbix/Prometheus）
- ❌ 不做配置文件采集与版本化（不是 Ansible / SaltStack）
- ❌ 不做工单流转
- ❌ 不做多租户 SaaS 化（v1.0 仅单组织部署）
- ❌ 不做响应式移动端适配（v1.0 仅保证 1280px+ 桌面浏览器）

---

## 3. 用户角色与权限

### 3.1 角色定义

CMDB Lite 采用**三权分立**模型，主要用于应付等保审计，但兼顾日常实用性。

| 角色 | 角色代码 | 主要职责 | 实际使用频率 |
|------|---------|---------|------------|
| 超级管理员 | `super_admin` | 系统配置、用户管理、密钥管理、LLM 配置 | 偶尔 |
| 管理员 | `admin` | 日常资产管理、扫描上传、拓扑图编辑 | 高频 |
| 审计员 | `auditor` | 只读所有数据、审查日志、导出审计报告 | 定期（季度/年度） |

### 3.2 权限矩阵

| 功能模块 | super_admin | admin | auditor |
|---------|:-----------:|:-----:|:-------:|
| 用户管理（增删改） | ✅ | ❌ | ❌ |
| 系统配置（LLM、密钥） | ✅ | ❌ | ❌ |
| 资产 CRUD | ✅ | ✅ | ❌ |
| 扫描报告上传 | ✅ | ✅ | ❌ |
| 资产差异比对 / 冲突解决 | ✅ | ✅ | ❌ |
| 拓扑图编辑 | ✅ | ✅ | ❌ |
| LLM 调用（拓扑生成） | ✅ | ✅ | ❌ |
| 查看所有数据（只读） | ✅ | ✅ | ✅ |
| 查看操作日志 | ✅ | ❌ | ✅ |
| 导出审计报告 | ❌ | ❌ | ✅ |
| 修改自己的密码 | ✅ | ✅ | ✅ |

> **关键设计**：超管不能导出审计报告，审计员不能改数据。这种"三权分立"是等保审计员现场会重点查的点。

### 3.3 内置账号

系统首次启动时：
- 自动创建 `admin / <随机生成密码并写入日志一次>` 账号（super_admin 角色）
- 强制首次登录修改密码
- 必须创建至少一个 auditor 角色账号才能解锁完整功能

---

## 4. 核心功能模块

### 4.1 模块全景

```
┌──────────────────────────────────────────────────────┐
│                   CMDB Lite v1.0                     │
├──────────────────────────────────────────────────────┤
│ M1: 资产录入与导入        M5: 安全视角报表           │
│ M2: 资产管理（CRUD）      M6: 操作审计日志           │
│ M3: 扫描快照与差异对比    M7: 用户与权限管理         │
│ M4: 拓扑图生成与编辑      M8: 系统配置               │
└──────────────────────────────────────────────────────┘
```

### 4.2 M1：资产录入与导入

#### 4.2.1 nmap 扫描命令规范（固化）

为保证数据格式一致性，**用户必须使用系统提供的固定命令**进行扫描。命令模板（在 Web 界面"帮助"页面提供一键复制）：

```bash
# 标准扫描（推荐）
nmap -sS -sV -O --osscan-guess -p 1-10000 \
     --version-intensity 5 -T4 \
     -oX scan_$(date +%Y%m%d_%H%M).xml \
     <目标网段，如 192.168.1.0/24>

# 快速扫描（端口数量减少）
nmap -sS -sV -O --osscan-guess --top-ports 1000 \
     -T4 -oX scan_quick_$(date +%Y%m%d_%H%M).xml \
     <目标网段>

# 深度扫描（耗时长但更准确）
nmap -sS -sV -O --osscan-guess -p- \
     --version-intensity 7 -T3 \
     -oX scan_deep_$(date +%Y%m%d_%H%M).xml \
     <目标网段>
```

**强制要求**：
- 输出格式必须是 `-oX`（XML），系统只解析 XML
- 文件名建议带日期，系统也会自己记录上传时间
- 上传文件大小上限 50 MB（单次）

#### 4.2.2 XML 解析逻辑

后端使用 `python-libnmap` 解析 XML（推荐）或 `xmltodict` 作为备选。

**从 nmap XML 中提取的字段**：

| 提取字段 | XML 路径示例 | 用途 |
|---------|------------|------|
| IP 地址 | `host/address[@addrtype='ipv4']` | 主要识别 |
| MAC 地址 | `host/address[@addrtype='mac']` | 辅助识别（关键） |
| 主机名 | `host/hostnames/hostname` | 辅助识别 |
| 操作系统指纹 | `host/os/osmatch` | 资产分类参考 |
| 开放端口 | `host/ports/port` | 服务面板 |
| 服务名/版本 | `port/service` | 安全分析 |
| 扫描时间 | `nmaprun/@start` | 快照时间戳 |

#### 4.2.3 导入流程（Web 界面）

```
[1] 用户上传 nmap XML 文件
     ↓
[2] 系统解析并生成 scan_batch（一个扫描批次记录）
     ↓
[3] 系统对每个发现的 host，尝试匹配已有资产：
     - 优先按 MAC 匹配
     - 次按 hostname + OS 匹配
     - 都不匹配则标记为"新发现"
     ↓
[4] 进入"导入确认页"：
     - 列出新发现资产（默认全选导入）
     - 列出变更资产（端口/服务变化，需要 review）
     - 列出消失资产（本次未扫到，需要标记保留或下线）
     ↓
[5] 对新发现资产，用户必须补充：
     - 资产编号（手动填写或自动生成 SVR-YYYYMMDD-NNN）
     - 物理位置（机房/机架/U 位）
     - 资产类型（物理服务器/虚拟机/网络设备/其他）
     - 业务系统归属
     - 负责人
     - 重要性等级
     - 网络区域
     ↓
[6] 保存 → 资产入库，scan_batch 与资产关联
```

#### 4.2.4 手动新增资产

并非所有资产都能被 nmap 扫到（如已下线的交换机、防火墙、未开机的备用机）。
界面提供**手动新增资产**入口，标记为 `source=manual`，与扫描资产同等地位但拓扑图渲染时可以区分。

---

### 4.3 M2：资产管理（CRUD）

#### 4.3.1 资产核心字段

**必填字段**（导入时强制填写）：

| 字段 | 类型 | 说明 |
|------|------|------|
| asset_no | string | 资产编号（业务主键，全局唯一） |
| ip_address | string | IP 地址（v1.0 仅 IPv4） |
| asset_type | enum | physical / virtual / network_device / other |
| location | string | 物理位置（机房-机架-U位 或 办公区房间号） |
| owner | string | 负责人姓名 |
| importance | enum | core / important / normal |
| network_zone | enum | dmz / intranet / office / management / other |
| business_system | string | 业务系统归属 |

**可选字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| mac_address | string | MAC 地址 |
| hostname | string | 主机名 |
| os_info | string | 操作系统信息 |
| cpu | string | CPU 描述（手填） |
| memory_gb | int | 内存大小 |
| disk_gb | int | 磁盘大小 |
| purchase_date | date | 采购日期 |
| warranty_expiry | date | 保修到期 |
| remark | text | 备注 |
| status | enum | online / offline / decommissioned |
| source | enum | scan / manual |

**自动字段**（系统维护）：

| 字段 | 说明 |
|------|------|
| created_at | 创建时间 |
| updated_at | 更新时间 |
| last_seen_at | 最后被扫到的时间 |
| missing_count | 连续未扫到次数（用于"消失保护"机制） |
| last_scan_batch_id | 最后一次扫到的批次 ID |

#### 4.3.2 资产详情页

显示资产所有字段 + 历史端口变化时间线 + 关联的所有 scan_batch 记录。

#### 4.3.3 资产列表页

- 默认按 `network_zone + ip_address` 排序
- 支持筛选：资产类型、网络区域、重要性、业务系统、状态、负责人
- 支持全文搜索：IP、主机名、资产编号、备注
- 支持批量操作：批量改负责人、批量下线、批量导出 CSV

---

### 4.4 M3：扫描快照与差异对比

这是 CMDB Lite 最核心的差异化能力之一。

#### 4.4.1 快照机制

每次上传 nmap XML 会创建一个 `scan_batch` 记录，并把本次扫描发现的所有 host_port 信息存入 `scan_snapshot_item`。资产表本身不携带快照，快照独立存储。

#### 4.4.2 差异类型

| 差异类型 | 触发条件 | 系统行为 |
|---------|---------|---------|
| NEW | 本次扫到，IP/MAC 都没对应资产 | 进入"待录入"队列，必须人工补充字段后入库 |
| CHANGED | 已有资产，但端口/服务变化 | 高亮变化项，请管理员确认是否更新 |
| MISSING | 已有资产，本次未扫到 | missing_count + 1，达到阈值（默认 3）才标记为 offline |
| RESTORED | 之前 missing，本次又扫到 | missing_count 归零，状态恢复 online |

#### 4.4.3 冲突解决界面

页面分三栏：
- **左侧**：本次扫描数据
- **中间**：当前资产数据
- **右侧**：保留策略（保留旧值 / 采用新值 / 手动合并）

#### 4.4.4 "消失保护"机制（重要）

**问题**：一次扫描漏报会误删资产。
**解决**：默认 `missing_count >= 3` 才把资产标记为 offline，且不删除资产记录。
**配置**：阈值在"系统配置"中可调（1～10）。

---

### 4.5 M4：拓扑图生成与编辑

#### 4.5.1 总体思路

```
[资产数据] → [本地脱敏] → [LLM 调用] → [本地反脱敏] → [drawio XML]
                                                         ↓
                                              [嵌入 drawio 编辑器]
                                                         ↓
                                              [用户手动调整 / 补充]
                                                         ↓
                                              [保存为拓扑图版本]
```

#### 4.5.2 拓扑图工具选型

**推荐**：drawio embed（`embed.diagrams.net`）
- 通过 iframe 嵌入到自己的 Web 界面
- 用户已熟悉 drawio 操作，无学习成本
- 支持导出 PNG / SVG / PDF / drawio 格式
- 离线场景下也能用（drawio 提供自托管版本）

**备选**：React Flow（如需更"应用化"体验，但开发量大）

#### 4.5.3 LLM 数据脱敏管道

**脱敏前的资产数据样例**：
```json
{
  "ip": "192.168.10.5",
  "hostname": "db-prod-01",
  "os": "Ubuntu 22.04",
  "ports": [22, 3306],
  "zone": "intranet",
  "type": "physical",
  "business": "ERP系统"
}
```

**投喂给 LLM 的脱敏后数据**：
```json
{
  "id": "HOST_A_001",
  "type": "physical",
  "zone": "intranet",
  "service_hint": ["ssh", "mysql"],
  "group": "GROUP_X"
}
```

**脱敏规则**：
- IP → 占位符 `HOST_X_NNN`
- 主机名 → 占位符（不出现真实名）
- OS 版本号 → 去除（只保留大类如 Linux/Windows）
- 端口 → 仅保留服务大类（不保留具体版本号）
- 业务系统名 → 占位符 `GROUP_X`

**反脱敏**：本地保留映射表，LLM 返回结构后用映射表逐项替换回真实信息。

#### 4.5.4 LLM 调用模式（双模式）

**模式 A：云端 API**（默认）
- 支持配置：OpenAI / Claude / DeepSeek / 智谱 / 通义千问
- 适合非核心资产
- 调用前后**强制落 LLM 调用日志**

**模式 B：本地推理**（高敏感场景）
- 通过 Ollama 调用本地模型（推荐 Qwen2.5、DeepSeek-R1 等开源模型）
- 适合 importance=core 的资产
- 系统配置项中按"资产重要性"自动路由

#### 4.5.5 手动补充

LLM 只能基于已扫描资产生成初稿，**必须允许手动新增以下不可扫描元素**：
- 交换机、路由器、防火墙（网络设备，部分不响应 nmap）
- 互联网出口、专线、VPN 通道
- 云服务（外部依赖，如 OSS、CDN）
- 客户/外部连接

这些元素以"虚拟节点"形式存在于拓扑图中，可与扫描资产连线。

#### 4.5.6 拓扑图版本管理

每次保存生成一个版本，可查看历史版本、对比差异、回滚。版本号格式 `topo_YYYYMMDD_NNN`。

---

### 4.6 M5：安全视角报表

这是 CMDB Lite 区别于通用 CMDB 的差异化模块。所有报表基于现有资产数据生成，零额外采集成本。

#### 4.6.1 端口暴露面分析
- 全网开放端口 Top 10 排行
- 按网络区域分组的端口统计
- 危险端口告警列表（如 23/Telnet、445/SMB、3389/RDP、3306/MySQL 暴露在 DMZ 或办公网）

#### 4.6.2 影子资产识别
- 列出"被扫到但未登记"的 IP（source=scan 但缺少业务系统/负责人字段）
- 列出"长期 offline"的资产（>30 天未被扫到）

#### 4.6.3 资产变化时间线
- 新开端口高亮（可能是后门或私自部署的服务）
- 服务版本变化记录
- OS 指纹变化记录

#### 4.6.4 报表导出
- 支持 CSV / Excel 导出
- 报表生成动作记入操作日志

---

### 4.7 M6：操作审计日志

#### 4.7.1 日志覆盖范围

**必须记录的操作**：
- 所有登录尝试（成功/失败）
- 所有数据变更（who, when, what changed, before, after）
- 所有数据导出（含导出范围）
- 所有 LLM 调用（含脱敏后的请求摘要、调用模型、调用耗时）
- 所有用户管理操作
- 所有系统配置变更

#### 4.7.2 日志字段

| 字段 | 说明 |
|------|------|
| log_id | 自增主键 |
| timestamp | 操作时间（UTC） |
| user_id | 操作人 |
| user_role | 操作人角色（冗余记录，防止后续角色变更影响审计） |
| action_type | LOGIN / CREATE / UPDATE / DELETE / EXPORT / LLM_CALL / CONFIG |
| target_type | asset / user / config / scan_batch / topology / ... |
| target_id | 操作对象 ID |
| ip_address | 操作人来源 IP |
| user_agent | User-Agent |
| details | JSON，记录变更前后 |
| result | success / failed |

#### 4.7.3 日志不可变性
- 日志只能新增，不能修改、不能删除（即使 super_admin 也不行）
- 数据库层面通过触发器禁止 UPDATE/DELETE（或代码层面双重保护）

---

### 4.8 M7：用户与权限管理

- 用户基础字段：username, password_hash, role, full_name, email, status, created_at
- 密码策略：最小 12 位、必含大小写数字符号、90 天强制修改、5 次错误锁定
- 支持禁用账号但不删除（留痕）

---

### 4.9 M8：系统配置

| 配置项 | 默认值 | 可调 |
|-------|-------|------|
| 消失保护阈值 | 3 | ✅ |
| LLM API 配置 | 空 | ✅ |
| LLM 路由策略（按重要性） | core→local, others→cloud | ✅ |
| 资产编号自动生成规则 | SVR-YYYYMMDD-NNN | ✅ |
| 上传文件大小上限 | 50 MB | ✅ |
| Session 超时 | 30 分钟 | ✅ |

---

## 5. 技术架构

### 5.1 技术栈选型

| 层 | 选型 | 理由 |
|---|------|------|
| 后端语言 | Python 3.11+ | 用户已有经验，nmap 生态好 |
| Web 框架 | FastAPI | 异步、自动 OpenAPI 文档、用户熟悉 |
| 数据库 | SQLite 3 (WAL 模式) | 单文件、零部署门槛 |
| ORM | SQLAlchemy 2.0 | 标准选择 |
| 数据迁移 | Alembic | 标准选择 |
| 任务队列 | 无（v1.0 同步处理足够） | 保持简单 |
| 前端框架 | Vue 3 + Vite + TypeScript | 上手快、生态稳定 |
| UI 组件库 | Element Plus | 中文友好、表单/表格完备 |
| 拓扑图编辑器 | drawio (iframe embed) | 学习成本零 |
| nmap 解析 | python-libnmap | 成熟可靠 |
| 鉴权 | JWT (短期 access + httpOnly refresh) | 标准方案 |
| 密码哈希 | argon2-cffi | 比 bcrypt 更现代 |
| 部署 | Docker + docker-compose | 跨平台 |

### 5.2 架构图

```
┌─────────────────────────────────────────────────┐
│                  Web 浏览器                      │
│        Vue 3 SPA + drawio iframe                │
└──────────────────┬──────────────────────────────┘
                   │ HTTPS
┌──────────────────▼──────────────────────────────┐
│              Nginx（反向代理）                   │
│       静态文件 / API 转发 / TLS 终止             │
└──────────────────┬──────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────┐
│              FastAPI 应用                        │
│  ┌──────────────────────────────────────────┐   │
│  │  路由层（Routers）                        │   │
│  │  - /api/auth   /api/assets               │   │
│  │  - /api/scans  /api/topology             │   │
│  │  - /api/users  /api/audit                │   │
│  └──────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────┐   │
│  │  业务层（Services）                       │   │
│  │  - 资产匹配、差异分析、脱敏、LLM 调用       │   │
│  └──────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────┐   │
│  │  数据层（Repository + SQLAlchemy）         │   │
│  └──────────────────────────────────────────┘   │
└──────────────────┬──────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────┐
│         SQLite 文件 + WAL 日志文件               │
│         + uploads/ 上传文件目录                  │
└─────────────────────────────────────────────────┘

    ↕ 调用（脱敏后）
┌─────────────────────────────────────────────────┐
│      LLM 提供方（云端 API 或本地 Ollama）         │
└─────────────────────────────────────────────────┘
```

### 5.3 目录结构

```
cmdb-lite/
├── backend/
│   ├── app/
│   │   ├── main.py                # FastAPI 入口
│   │   ├── core/                  # 配置、安全、依赖注入
│   │   │   ├── config.py
│   │   │   ├── security.py        # JWT、密码哈希
│   │   │   └── deps.py            # 依赖注入
│   │   ├── models/                # SQLAlchemy 模型
│   │   ├── schemas/               # Pydantic schema
│   │   ├── routers/               # 路由
│   │   ├── services/              # 业务逻辑
│   │   │   ├── asset_service.py
│   │   │   ├── scan_service.py
│   │   │   ├── diff_service.py
│   │   │   ├── topology_service.py
│   │   │   ├── llm_service.py     # LLM 抽象层（支持多 provider）
│   │   │   └── sanitize_service.py # 脱敏管道
│   │   ├── repositories/          # 数据访问层
│   │   └── utils/
│   │       └── nmap_parser.py     # nmap XML 解析
│   ├── alembic/                   # 数据库迁移
│   ├── tests/                     # pytest 测试
│   ├── data/                      # SQLite 文件（运行时挂载）
│   ├── uploads/                   # 上传文件（运行时挂载）
│   ├── requirements.txt
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── views/                 # 页面
│   │   ├── components/            # 组件
│   │   ├── api/                   # API 封装
│   │   ├── stores/                # Pinia 状态
│   │   ├── styles/                # 全局样式
│   │   │   ├── tokens.css         # 设计 token（来自 Claude Design）
│   │   │   └── element-theme.scss # Element Plus 主题覆盖
│   │   ├── design/                # 从 Claude Design 输出的页面模板
│   │   │   └── README.md          # 9 个模板的对应关系
│   │   └── router/
│   ├── public/
│   ├── package.json
│   └── vite.config.ts
├── docker/
│   ├── Dockerfile.backend
│   ├── Dockerfile.frontend
│   ├── nginx.conf
│   └── docker-compose.yml
├── docs/
│   ├── nmap-cmd-reference.md      # nmap 命令模板（给用户的）
│   ├── api-spec.md                # API 详细规格
│   └── deployment.md
├── scripts/
│   ├── init_db.py                 # 首次初始化
│   ├── reset_admin.py             # 重置 admin 密码
│   └── export_audit.py            # 导出审计报告
├── README.md
└── LICENSE
```

### 5.4 设计系统与前端规范【v2 新增】

#### 5.4.1 设计来源

前端 UI 由 **Claude Design** 生成基础模板，开发使用 Vue 3 + Element Plus 实现。Claude Design 输出共 9 个页面/规范文档（详见附录 12.6），覆盖系统全部高频页面，其余页面（如各类报表子页、版本对比页）通过 Claude Code 按模板复用实现，**不再调用 Claude Design**。

#### 5.4.2 设计 token 单一来源

- 所有设计 token（颜色、字号、间距、圆角、阴影）从 Claude Design 第 1 次输出的"设计系统总览"中提取
- 落地为唯一的 token 文件：`frontend/src/styles/tokens.css`（CSS 变量形式）
- **禁止**在 Vue 组件中硬编码颜色（如 `color: #2563EB`）、字号、间距值
- **禁止**在不同页面定义不同的 token 副本

#### 5.4.3 Element Plus 主题对齐

- 通过 SCSS 变量覆盖 Element Plus 默认主题，统一到设计 token
- 主题覆盖文件：`frontend/src/styles/element-theme.scss`
- 仅覆盖必要变量（主色、辅助色、圆角、字体），其余保持 Element Plus 默认

#### 5.4.4 页面实现规约

- 9 个 Claude Design 输出页面 → 对应 `frontend/src/views/` 下的具体文件（映射见 12.6）
- 新增页面必须**复用已有模板布局**（顶部面包屑 + 标题区 + 筛选区 + 内容区 + 底部分页）
- 业务组件可在模板内自由组合，但不允许临场创造新的视觉模式

#### 5.4.5 响应式策略

- v1.0 仅保证 **1280px+ 桌面浏览器**可用
- 不做响应式断点适配
- 不做移动端 / 平板专属布局
- 用户场景是运维/安全工程师在办公桌前长时间使用，不存在移动端场景

#### 5.4.6 视觉风格基线

- **审美方向**：2026 年主流——克制、密度适中、不堆砌动效
- **配色基调**：浅色主题为主（深色主题 v2.0 再考虑），主色偏冷的克制蓝
- **信息密度**：表格行高 44px，紧凑但不拥挤；筛选区可折叠
- **禁用风格**：Glassmorphism、Neumorphism、过度饱和色、大圆角（>8px）、装饰性大插图
- **图标库**：统一使用 `@element-plus/icons-vue`，不混用 FontAwesome 等

---

## 6. 数据模型

### 6.1 主要数据表

> 以下为简化版 DDL，开发时使用 SQLAlchemy 模型 + Alembic 迁移管理。

```sql
-- 用户表
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(64) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL CHECK (role IN ('super_admin','admin','auditor')),
    full_name VARCHAR(100),
    email VARCHAR(100),
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active','disabled')),
    password_changed_at DATETIME,
    failed_login_count INTEGER DEFAULT 0,
    locked_until DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 资产表
CREATE TABLE assets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_no VARCHAR(64) UNIQUE NOT NULL,
    ip_address VARCHAR(45) NOT NULL,
    mac_address VARCHAR(32),
    hostname VARCHAR(255),
    asset_type VARCHAR(32) NOT NULL,
    os_info VARCHAR(255),
    location VARCHAR(255) NOT NULL,
    owner VARCHAR(100) NOT NULL,
    importance VARCHAR(20) NOT NULL,
    network_zone VARCHAR(20) NOT NULL,
    business_system VARCHAR(100) NOT NULL,
    cpu VARCHAR(100),
    memory_gb INTEGER,
    disk_gb INTEGER,
    purchase_date DATE,
    warranty_expiry DATE,
    remark TEXT,
    status VARCHAR(20) DEFAULT 'online',
    source VARCHAR(20) DEFAULT 'scan',
    last_seen_at DATETIME,
    missing_count INTEGER DEFAULT 0,
    last_scan_batch_id INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_assets_ip ON assets(ip_address);
CREATE INDEX idx_assets_mac ON assets(mac_address);
CREATE INDEX idx_assets_zone ON assets(network_zone);

-- 资产端口表（一个资产可能有多个开放端口）
CREATE TABLE asset_ports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_id INTEGER NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    port_number INTEGER NOT NULL,
    protocol VARCHAR(10) NOT NULL,  -- tcp/udp
    service_name VARCHAR(50),
    service_version VARCHAR(255),
    state VARCHAR(20),               -- open/closed/filtered
    last_seen_at DATETIME,
    UNIQUE(asset_id, port_number, protocol)
);

-- 扫描批次表
CREATE TABLE scan_batches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_name VARCHAR(255),
    uploaded_by INTEGER REFERENCES users(id),
    uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    scan_started_at DATETIME,
    scan_finished_at DATETIME,
    file_path VARCHAR(500),
    file_size_bytes INTEGER,
    total_hosts INTEGER,
    new_count INTEGER DEFAULT 0,
    changed_count INTEGER DEFAULT 0,
    missing_count INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'pending'  -- pending/confirmed/rejected
);

-- 扫描快照项（每次扫描的每个 host_port 一行）
CREATE TABLE scan_snapshot_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scan_batch_id INTEGER NOT NULL REFERENCES scan_batches(id) ON DELETE CASCADE,
    ip_address VARCHAR(45) NOT NULL,
    mac_address VARCHAR(32),
    hostname VARCHAR(255),
    os_info VARCHAR(255),
    port_number INTEGER,
    protocol VARCHAR(10),
    service_name VARCHAR(50),
    service_version VARCHAR(255),
    matched_asset_id INTEGER REFERENCES assets(id),
    diff_type VARCHAR(20)  -- new/changed/same
);

-- 拓扑图版本
CREATE TABLE topologies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    version_no VARCHAR(64) UNIQUE NOT NULL,
    title VARCHAR(255),
    description TEXT,
    drawio_xml TEXT NOT NULL,
    created_by INTEGER REFERENCES users(id),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_current BOOLEAN DEFAULT 0
);

-- 操作日志（不可修改不可删除）
CREATE TABLE audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    user_id INTEGER,
    username VARCHAR(64),       -- 冗余存储
    user_role VARCHAR(20),      -- 冗余存储
    action_type VARCHAR(32) NOT NULL,
    target_type VARCHAR(32),
    target_id VARCHAR(64),
    ip_address VARCHAR(45),
    user_agent VARCHAR(500),
    details TEXT,               -- JSON
    result VARCHAR(20) DEFAULT 'success'
);
CREATE INDEX idx_audit_timestamp ON audit_logs(timestamp);
CREATE INDEX idx_audit_user ON audit_logs(user_id);

-- LLM 调用日志（独立表，便于审计）
CREATE TABLE llm_call_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    user_id INTEGER,
    provider VARCHAR(50),        -- openai/claude/deepseek/zhipu/ollama
    model VARCHAR(100),
    purpose VARCHAR(100),        -- topology_generation
    sanitized_request TEXT,      -- 脱敏后的请求摘要
    response_summary TEXT,       -- 响应摘要
    elapsed_ms INTEGER,
    tokens_used INTEGER,
    success BOOLEAN
);

-- 系统配置（kv 存储）
CREATE TABLE system_configs (
    key VARCHAR(100) PRIMARY KEY,
    value TEXT,
    description VARCHAR(500),
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_by INTEGER REFERENCES users(id)
);
```

### 6.2 关键设计说明

1. **资产编号 `asset_no` 是业务主键**，IP 是辅助识别字段
2. **scan_snapshot_items 表会增长很快**，建议每 6 个月做一次归档（v2.0 实现）
3. **audit_logs 表禁止 UPDATE/DELETE**，通过 SQLite 触发器实现
4. **WAL 模式**：开启 SQLite WAL，提高并发读性能 + 防止意外断电损坏

---

## 7. API 设计概览

### 7.1 鉴权

```
POST /api/auth/login              # 登录，返回 access_token + 设置 refresh cookie
POST /api/auth/refresh            # 刷新 access_token
POST /api/auth/logout             # 注销
POST /api/auth/change-password    # 修改密码
```

### 7.2 用户管理（仅 super_admin）

```
GET    /api/users
POST   /api/users
GET    /api/users/{id}
PATCH  /api/users/{id}
DELETE /api/users/{id}    # 软删除（status=disabled）
```

### 7.3 资产管理

```
GET    /api/assets                    # 列表（支持筛选/搜索/分页）
POST   /api/assets                    # 手动新增
GET    /api/assets/{id}               # 详情
PATCH  /api/assets/{id}               # 更新
DELETE /api/assets/{id}               # 删除（实际是 decommissioned）
GET    /api/assets/{id}/history       # 端口变化历史
GET    /api/assets/export             # CSV 导出
```

### 7.4 扫描批次

```
POST   /api/scans/upload              # 上传 XML 文件
GET    /api/scans                     # 批次列表
GET    /api/scans/{id}                # 批次详情（含 diff 结果）
POST   /api/scans/{id}/confirm        # 确认导入（含字段补充）
DELETE /api/scans/{id}                # 拒绝并删除批次
```

### 7.5 拓扑图

```
POST   /api/topology/generate         # LLM 生成初稿
GET    /api/topology                  # 当前拓扑图
GET    /api/topology/versions         # 历史版本列表
GET    /api/topology/versions/{id}    # 特定版本
POST   /api/topology                  # 保存新版本
POST   /api/topology/{id}/rollback    # 回滚到某版本
```

### 7.6 安全报表

```
GET /api/reports/port-exposure        # 端口暴露面
GET /api/reports/dangerous-ports      # 危险端口列表
GET /api/reports/shadow-assets        # 影子资产
GET /api/reports/asset-changes        # 资产变化时间线
```

### 7.7 审计日志

```
GET  /api/audit/logs                  # 操作日志（admin+auditor 可读）
GET  /api/audit/llm-logs              # LLM 调用日志
POST /api/audit/export                # 导出审计报告（仅 auditor）
```

### 7.8 系统配置

```
GET   /api/config                     # 读取配置
PATCH /api/config                     # 修改配置（super_admin）
```

---

## 8. 部署方案

### 8.1 三环境一览

| 环境 | 用途 | 关键点 |
|------|------|--------|
| Windows 11 | 开发 | 路径分隔符、文件锁、SQLite WAL 注意事项 |
| Docker | 通用部署 | 数据卷挂载、用户权限 |
| Linux | 生产部署 | systemd、文件权限、SELinux |

### 8.2 Windows 11 开发环境

#### 8.2.1 推荐工具链

- Python 3.11+（建议用 [uv](https://github.com/astral-sh/uv) 管理，比 venv 快）
- Node.js 20 LTS + pnpm
- Git for Windows
- WSL2 Ubuntu（**强烈推荐**：用于本地跑 Docker、测试 Linux 部署）
- Docker Desktop（依赖 WSL2 后端）
- VS Code + Kiro 插件

#### 8.2.2 Windows 特有注意事项

**1. 路径分隔符**
```python
# ❌ 错误：硬编码反斜杠
file_path = "data\\uploads\\scan.xml"

# ✅ 正确：使用 pathlib
from pathlib import Path
file_path = Path("data") / "uploads" / "scan.xml"
```

**2. SQLite WAL 模式与 OneDrive / 杀软**

Windows 上 SQLite 在以下场景容易出问题：
- 数据库文件放在 OneDrive 同步目录（**强禁止**）
- 杀软实时扫描 `.db-wal` `.db-shm` 文件
- 文件被其他进程持有句柄

**解决**：
- 开发期间数据库统一放 `./data/cmdb.db`（项目目录下，加入 `.gitignore`）
- OneDrive 同步目录排除项目目录
- 杀软白名单加入项目目录

**3. 换行符**

Git 配置 `core.autocrlf=input`，避免 Docker 内执行 shell 脚本时遇到 CRLF 报错。

**4. nmap 测试**

Windows 开发时如需本地跑 nmap 测试，安装 Nmap for Windows，但建议在 WSL2 中执行（避免 WinPcap 兼容性问题）。

#### 8.2.3 启动命令

```powershell
# 后端
cd backend
uv venv
.\.venv\Scripts\activate
uv pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 前端
cd frontend
pnpm install
pnpm dev
```

### 8.3 Docker 部署

#### 8.3.1 Dockerfile.backend

```dockerfile
FROM python:3.11-slim AS builder
WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
    tini \
    && rm -rf /var/lib/apt/lists/*
RUN groupadd -r cmdb && useradd -r -g cmdb -u 1001 cmdb
WORKDIR /app
COPY --from=builder /root/.local /home/cmdb/.local
COPY --chown=cmdb:cmdb ./app ./app
COPY --chown=cmdb:cmdb ./alembic ./alembic
COPY --chown=cmdb:cmdb ./alembic.ini ./
RUN mkdir -p /app/data /app/uploads && chown -R cmdb:cmdb /app
ENV PATH=/home/cmdb/.local/bin:$PATH
USER cmdb
EXPOSE 8000
ENTRYPOINT ["tini", "--"]
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
```

#### 8.3.2 Dockerfile.frontend

```dockerfile
FROM node:20-alpine AS builder
WORKDIR /build
COPY package.json pnpm-lock.yaml ./
RUN corepack enable && pnpm install --frozen-lockfile
COPY . .
RUN pnpm build

FROM nginx:1.27-alpine
COPY --from=builder /build/dist /usr/share/nginx/html
COPY ./nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
```

#### 8.3.3 docker-compose.yml

```yaml
services:
  backend:
    build:
      context: ./backend
      dockerfile: ../docker/Dockerfile.backend
    container_name: cmdb-backend
    restart: unless-stopped
    volumes:
      - ./data:/app/data
      - ./uploads:/app/uploads
    environment:
      - DATABASE_URL=sqlite:///./data/cmdb.db
      - JWT_SECRET_FILE=/run/secrets/jwt_secret
      - TZ=Asia/Shanghai
    secrets:
      - jwt_secret
    networks:
      - cmdb-net

  frontend:
    build:
      context: ./frontend
      dockerfile: ../docker/Dockerfile.frontend
    container_name: cmdb-frontend
    restart: unless-stopped
    ports:
      - "8080:80"
    depends_on:
      - backend
    networks:
      - cmdb-net

networks:
  cmdb-net:

secrets:
  jwt_secret:
    file: ./secrets/jwt_secret.txt
```

#### 8.3.4 关键部署点

- **数据持久化**：`./data` 与 `./uploads` 挂载为命名卷或本地路径
- **用户权限**：容器内用非 root 用户（UID 1001），宿主机目录需相应 chown
- **时区**：通过 `TZ` 环境变量统一
- **密钥**：JWT secret 使用 docker secret 而非环境变量
- **健康检查**：可加 healthcheck 检测 `/api/health`

### 8.4 Linux 生产部署

#### 8.4.1 推荐方式

**方式 A：Docker Compose（推荐）**
直接复用上述 docker-compose.yml，配合 systemd service 守护。

**方式 B：原生部署**
- Python venv + gunicorn + nginx + systemd
- 适合不允许装 Docker 的国央企环境

#### 8.4.2 systemd 单元示例（方式 B）

```ini
# /etc/systemd/system/cmdb-lite.service
[Unit]
Description=CMDB Lite Backend
After=network.target

[Service]
Type=simple
User=cmdb
Group=cmdb
WorkingDirectory=/opt/cmdb-lite/backend
Environment="PATH=/opt/cmdb-lite/backend/.venv/bin"
ExecStart=/opt/cmdb-lite/backend/.venv/bin/gunicorn \
    -k uvicorn.workers.UvicornWorker \
    -w 2 -b 127.0.0.1:8000 app.main:app
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

#### 8.4.3 文件权限

```bash
sudo useradd -r -s /usr/sbin/nologin cmdb
sudo mkdir -p /opt/cmdb-lite/data /opt/cmdb-lite/uploads
sudo chown -R cmdb:cmdb /opt/cmdb-lite
sudo chmod 700 /opt/cmdb-lite/data    # 数据库目录严格权限
```

#### 8.4.4 反向代理（Nginx）

```nginx
server {
    listen 443 ssl http2;
    server_name cmdb.example.com;

    ssl_certificate     /etc/ssl/cmdb.crt;
    ssl_certificate_key /etc/ssl/cmdb.key;

    client_max_body_size 60M;     # nmap XML 上传

    location / {
        root /opt/cmdb-lite/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass         http://127.0.0.1:8000/api/;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;   # LLM 调用可能慢
    }
}
```

### 8.5 跨平台代码注意事项

| 项 | 注意点 |
|---|--------|
| 文件路径 | 全部使用 `pathlib.Path`，禁止字符串拼接 |
| 文件锁 | SQLite 已处理，无需额外加锁 |
| 字符编码 | 所有文件 IO 显式指定 `encoding="utf-8"` |
| 换行符 | Git `core.autocrlf=input`，Python 用 `newline=""` |
| 时区 | 数据库统一存 UTC，前端按用户时区展示 |
| 临时文件 | 使用 `tempfile` 模块而非硬编码 `/tmp` |
| 权限 | 不依赖 Linux 文件权限做业务逻辑，鉴权放应用层 |

---

## 9. 安全设计

### 9.1 身份与会话

- 密码哈希:argon2id，参数 m=65536, t=3, p=4
- JWT：access_token 15 分钟，refresh_token 7 天（httpOnly cookie）
- 5 次失败登录锁定 15 分钟
- 强制 HTTPS（生产环境）

### 9.2 数据安全

- LLM API key 加密存储（使用 envelope encryption，主密钥从环境变量读取）
- 上传文件类型严格校验（仅接受 `.xml` 且 magic number 校验）
- 防 XML 外部实体注入（XXE）：使用 `defusedxml`
- SQL 注入：全部使用参数化查询（SQLAlchemy ORM 默认满足）
- XSS：前端框架默认转义 + CSP 头
- CSRF：JWT 在 Authorization header 中传递，refresh cookie 使用 SameSite=Strict

### 9.3 LLM 数据出境

- 默认所有 LLM 调用都过脱敏管道
- super_admin 可在系统配置中**全局禁用云端 LLM**，所有调用走本地 Ollama
- 每次 LLM 调用必落 `llm_call_logs`，审计员可查

### 9.4 文件上传安全

- 大小限制：50 MB
- 仅接受 XML
- 上传后扫描 nmap 特征头部，不符合则拒绝
- 上传文件存储路径不可猜测（UUID 命名）
- 上传目录禁止 Web 直接访问

---

## 10. 项目里程碑（MVP 路线）

> 给 Kiro / Claude Sonnet 4.6 拆解任务的颗粒度参考。每个里程碑建议 1～2 周完成。

### v0.1（脚手架）
- [ ] 项目结构搭建
- [ ] FastAPI 基础框架 + SQLAlchemy + Alembic
- [ ] 用户表 + 登录接口 + JWT
- [ ] Vue 3 前端脚手架 + Element Plus + 登录页
- [ ] **使用 Claude Design 输出 9 个页面模板**（参考 Playbook 第 5 章）【v2 新增】
- [ ] **提取设计 token 到 `frontend/src/styles/tokens.css`**【v2 新增】
- [ ] **Element Plus 主题覆盖文件 `element-theme.scss` 与 token 对齐**【v2 新增】
- [ ] Docker 本地跑通

### v0.2（资产基础 CRUD）
- [ ] 资产表 + 端口表的 schema
- [ ] 资产列表/详情/新增/编辑/删除 API
- [ ] 前端资产管理页面（基于 Design 模板）
- [ ] 资产 CSV 导出

### v0.3（nmap 导入核心）
- [ ] nmap XML 解析（python-libnmap）
- [ ] 上传接口 + 文件校验
- [ ] 资产匹配逻辑（MAC → hostname+OS）
- [ ] 扫描批次表 + 快照项表
- [ ] 导入确认页（前端）
- [ ] 字段补充表单

### v0.4（差异对比与冲突解决）
- [ ] diff_service 实现 NEW/CHANGED/MISSING/RESTORED
- [ ] 消失保护机制（missing_count）
- [ ] 冲突解决三栏页面
- [ ] 端口历史变化时间线

### v0.5（三权分立 + 审计）
- [ ] 角色与权限中间件
- [ ] 用户管理 API + 页面
- [ ] audit_logs 表 + 中间件埋点
- [ ] 审计日志查看页（admin/auditor）
- [ ] 审计报告导出（CSV/PDF）

### v0.6（拓扑图）
- [ ] 脱敏管道 sanitize_service
- [ ] LLM 抽象层 llm_service（OpenAI/Claude/DeepSeek/智谱/Ollama）
- [ ] 拓扑生成 API
- [ ] drawio iframe 嵌入
- [ ] 拓扑版本管理
- [ ] llm_call_logs 表

### v0.7（安全报表）
- [ ] 端口暴露面分析
- [ ] 危险端口告警
- [ ] 影子资产识别
- [ ] 资产变化时间线

### v1.0（打磨发布）
- [ ] 完整中文文档
- [ ] nmap 命令一键复制页面
- [ ] 单元测试覆盖率 60%+
- [ ] Docker 镜像发布
- [ ] 离线安装包（针对涉密内网）

---

## 11. 风险与待决事项

### 11.1 已识别风险

| 风险 | 影响 | 缓解措施 |
|------|------|--------|
| 用户不按规范使用 nmap 命令 | XML 字段缺失导致解析失败 | 在界面强提示+提供一键复制+解析失败给出友好提示 |
| SQLite 写并发性能不足 | 多人同时操作可能阻塞 | WAL 模式 + v2 视情况切换 PG |
| LLM 提供方 API 变更 | 拓扑生成失败 | LLM 抽象层 + 多 provider 支持 + 优雅降级 |
| 大网段扫描产生超大 XML | 上传超时或解析慢 | 限制 50MB + 流式解析 |
| 用户忘记 admin 密码 | 无法登录 | 提供 `reset_admin.py` 脚本（需服务器权限） |
| 误删资产 | 数据丢失 | 软删除 + 回收站（30 天） |
| 时区混乱 | 日志时间不准 | 全局 UTC 存储，前端转换 |
| Claude Design 额度耗尽前未覆盖核心页面 | 后续页面视觉不一致 | 严格按 Playbook 第 5 章的 9 次调用计划执行 |

### 11.2 待决事项（v2.0 再考虑）

- 是否支持 IPv6
- 是否支持 PostgreSQL（团队规模超过 50 时）
- 是否做企业微信 / 钉钉 SSO
- 是否做 Agent 端补充采集（仅采集 CPU/内存等 nmap 扫不到的）
- 是否做 CMDB 数据 API 给其他系统消费（CI/CD、ITSM）
- 深色主题
- 响应式适配（平板/手机）

---

## 12. 附录

### 12.1 nmap 命令快速参考

详见 `docs/nmap-cmd-reference.md`。Web 界面"帮助"页面提供一键复制。

### 12.2 危险端口清单（用于报表模块）

| 端口 | 协议 | 风险 |
|------|------|------|
| 21 | FTP | 明文传输 |
| 22 | SSH | 暴露管理面 |
| 23 | Telnet | 明文+常被爆破 |
| 135 | RPC | Windows 横向移动 |
| 139, 445 | SMB | 永恒之蓝等 |
| 1433 | MSSQL | 数据库暴露 |
| 1521 | Oracle | 数据库暴露 |
| 2375 | Docker | 容器逃逸 |
| 3306 | MySQL | 数据库暴露 |
| 3389 | RDP | 远程桌面 |
| 5432 | PostgreSQL | 数据库暴露 |
| 5984 | CouchDB | 未授权访问 |
| 6379 | Redis | 未授权 RCE |
| 8080, 8888 | HTTP-alt | 常见管理面 |
| 9200 | Elasticsearch | 数据泄露 |
| 11211 | Memcached | 反射放大 |
| 27017 | MongoDB | 未授权访问 |

判定逻辑：以上端口暴露在 `dmz` 或 `office` 区域时高危告警，暴露在 `intranet` 时中危提示。

### 12.3 推荐 Python 依赖（requirements.txt）

```
fastapi>=0.110
uvicorn[standard]>=0.27
sqlalchemy>=2.0
alembic>=1.13
pydantic>=2.6
pydantic-settings>=2.2
python-multipart>=0.0.9
python-jose[cryptography]>=3.3
argon2-cffi>=23.1
python-libnmap>=0.7.3
defusedxml>=0.7
httpx>=0.27
openai>=1.30
anthropic>=0.25
gunicorn>=21.2
```

### 12.4 推荐前端依赖（package.json 关键项）

```
vue ^3.4
vue-router ^4.3
pinia ^2.1
element-plus ^2.7
@element-plus/icons-vue ^2.3
axios ^1.6
@vueuse/core ^10.9
dayjs ^1.11
echarts ^5.5            # 报表图表
typescript ^5.4
vite ^5.2
sass ^1.77              # Element Plus 主题覆盖
```

### 12.5 Kiro + Claude Sonnet 4.6 协作建议

1. **任务拆解粒度**：按本文档 v0.1～v1.0 的 checkbox 拆，每个 checkbox 一个 Kiro Task
2. **代码生成 prompt 建议**：每次让 Claude Sonnet 4.6 生成代码时附带：
   - 本 PRD 对应章节
   - 当前已存在的相关文件
   - 该 Task 的输入输出
3. **优先生成的文件**：
   - `app/core/config.py`、`app/core/security.py`
   - `app/models/`（先把所有模型类一次性生成）
   - `app/schemas/`
   - 再开始写 router 和 service
4. **测试策略**：核心 service 必须有 pytest 单元测试，特别是 `nmap_parser`、`diff_service`、`sanitize_service`
5. **不要让 LLM 直接写 Alembic 迁移**：用 `alembic revision --autogenerate` 生成后人工 review
6. **详细规约见 Playbook**：本附录仅是引子，完整协作规约见 `CMDB-Lite-Playbook-v1.md`

### 12.6 前端设计资产清单【v2 新增】

Claude Design 共输出 9 份设计产物，对应前端 Vue 文件如下：

| Design # | 产物名 | 用途 | 实现文件 | 复用范围 |
|----------|--------|------|---------|---------|
| 1 | 设计系统总览 | 提取所有 token | `src/styles/tokens.css` + `src/styles/element-theme.scss` | 全局 |
| 2 | 登录页 + 主框架 | 登录与系统骨架 | `src/views/Login.vue` + `src/layouts/MainLayout.vue` | 登录、整个系统外壳 |
| 3 | 资产列表页 | 列表页模板 | `src/views/asset/AssetList.vue` | 资产列表、批次列表、用户列表、审计日志（结构复用） |
| 4 | 资产详情页 | 详情页模板 | `src/views/asset/AssetDetail.vue` | 资产详情、批次详情、拓扑版本详情（结构复用） |
| 5 | 资产表单页 | 表单页模板 | `src/views/asset/AssetForm.vue` | 资产新增/编辑、用户新增/编辑、系统配置（结构复用） |
| 6 | 扫描导入冲突解决页 | 导入流程专用页 | `src/views/scan/ScanConfirm.vue` | 仅本页（最复杂，无复用） |
| 7 | 拓扑图编辑页 | 拓扑专用页 | `src/views/topology/TopologyEditor.vue` | 仅本页 |
| 8 | 安全报表 Dashboard | 报表入口 | `src/views/report/ReportDashboard.vue` | 报表 dashboard，子报表页复用 #3 列表模板 |
| 9 | 审计日志页 | 审计专用页 | `src/views/audit/AuditLog.vue` | 操作日志、LLM 日志（结构复用） |

**关键复用规则**：
- 列表类页面（用户管理、批次历史、报表子页等）**复用 #3 资产列表页**的布局，仅替换表格列定义和筛选条件
- 详情类页面**复用 #4 资产详情页**的 Tab 布局
- 表单类页面**复用 #5 资产表单页**的分段布局
- 新增页面时**不允许调用 Claude Design**，必须从已有模板派生

**额度规划说明**：
- 9 次调用预计消耗约 50% Design 额度（每次约 4～6% 不等，复杂页面更多）
- 预留约 13% 额度用于修订（如某个页面输出不满意时重做）
- 剩余 0%（Pro 账户当前剩 63%，扣除后约剩 13%）

---

**文档结束**

> v2 主要变更：新增 5.4 节明确前端规范、10 章 v0.1 加入设计 token 落地任务、12.6 附录列出 9 个 Design 产物的对应实现。配套的工作手册见 `CMDB-Lite-Playbook-v1.md`。

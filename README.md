# Z-CMDB Lite

> 准确性优先、零门槛、面向中小团队的轻量级配置管理数据库

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://python.org)
[![Vue](https://img.shields.io/badge/Vue-3-4FC08D?logo=vue.js&logoColor=white)](https://vuejs.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)

---

## 简介

Z-CMDB Lite 面向 **5～50 人规模**的中小企业 IT 运维和安全工程师，通过 nmap 扫描上传的方式管理内网 / 办公网 / IDC / 云上资产，用于：

- 日常运维资产台账
- 安全审计 & 等保备查
- HVV / 红蓝对抗资产梳理
- 端口暴露面分析

**核心设计原则**：SQLite 单文件、零中间件依赖、所有写操作可审计、敏感数据不出内网。

---

## 功能概览

### 🗂 资产管理

![资产列表](img/001.png)

- 支持物理服务器、虚拟机、**云服务器**、网络设备、其他五种资产类型
- 云服务器选择后，网络区域自动切换为云服务商（阿里云 / 腾讯云 / 华为云 / AWS / Azure / GCP）
- 多维度筛选：网络区域、资产类型、重要性、状态
- 全文搜索：IP、主机名、资产编号、业务系统、**应用名称**（如 nginx、mysql）
- 批量操作：批量修改负责人、业务系统、重要性、网络区域
- 导出：标准 CSV + 威胁狩猎助手兼容格式

### 📋 资产详情

![资产详情](img/003.png)

三个标签页一站式查看：

| 标签页 | 内容 |
|--------|------|
| 基本信息 | 资产编号、IP/MAC/主机名、OS、归属、硬件、采购保修 |
| 端口 | 扫描发现的开放端口，含服务名、版本、状态 |
| 应用 | 手动登记或扫描提取的应用清单，含版本、端口、安装路径 |

**端口与应用双向同步**：手动新增应用时填写端口，自动写入端口表；nmap 扫描确认导入时，有 service_name 的端口同步生成应用记录。

### 📡 扫描批次

![扫描批次](img/005.png)
![差异确认](img/006.png)

1. 在跳板机运行 nmap，生成 XML 报告
2. 上传到平台，自动解析并与现有资产做差异分析
3. 差异分为四类：**新发现** / **变更** / **消失** / **恢复**
4. 人工审核每台主机的端口变更详情后确认导入
5. 消失主机不立即删除，`missing_count + 1`，超过阈值才标记离线

### 🗺 拓扑图（AI 生成）

![拓扑图](img/007.png)

- 一键调用 LLM 生成 drawio 网络拓扑图初稿
- 支持 DeepSeek / OpenRouter / 本地 Ollama
- 资产数据**自动脱敏**后投喂 LLM（IP → 占位符，业务系统 → 代号）
- 核心资产可配置强制走本地模型，敏感数据不出内网
- 生成后可在内嵌 drawio 编辑器中手工调整，支持版本管理和回滚

### 📊 安全报表

![安全报表](img/008.png)

- 资产分布：网络区域、重要性、操作系统、资产类型
- 端口暴露面分析：Top 端口、高危端口统计
- 扫描覆盖率：最近扫描时间分布
- 威胁狩猎助手兼容导出：按"资产 × 应用"展开，含 environment / criticality / exposure_scope / vendor 字段

### 📝 审计日志

![审计日志](img/009.png)

- 记录所有登录、增删改、导出、LLM 调用操作
- **不可篡改**：SQLite 触发器在数据库层禁止 UPDATE / DELETE
- 支持按动作类型、用户、目标类型筛选

### 👥 用户与权限

![用户管理](img/010.png)

三种角色，职责分离：

| 角色 | 权限 |
|------|------|
| `super_admin` | 全部操作 + 用户管理 + 系统配置 |
| `admin` | 资产增删改、扫描上传确认、拓扑生成 |
| `auditor` | 只读 + 审计日志查看 |

> 系统要求至少创建一个 auditor 账号才能解锁完整功能（等保职责分离要求）。

### ⚙️ 系统配置

- LLM 提供方 / API Key / 模型 / Base URL
- 核心资产路由策略（是否强制走本地 Ollama）
- 资产编号前缀（默认 `CMDB`）
- 扫描消失阈值（连续 N 次未扫到才标记离线）
- 上传文件大小限制

---

## 技术栈

| 层 | 选型 |
|---|------|
| 后端语言 | Python 3.11+ |
| Web 框架 | FastAPI |
| 数据库 | SQLite 3（WAL 模式，单文件） |
| ORM | SQLAlchemy 2.0 |
| 数据迁移 | Alembic |
| 前端框架 | Vue 3 + Vite + TypeScript |
| UI 组件库 | Element Plus |
| 状态管理 | Pinia |
| 密码哈希 | argon2id |
| 认证 | JWT（access + refresh token） |
| 部署 | Docker + docker-compose |

---

## 快速开始

### 方式一：Docker（推荐）

```bash
# 1. 克隆项目
git clone https://github.com/Zer00n/z-cmdb.git
cd z-cmdb

# 2. 配置 JWT 密钥
cp secrets/jwt_secret.txt.example secrets/jwt_secret.txt
# 编辑 secrets/jwt_secret.txt，填入随机字符串（建议 32 位以上）

# 3. 启动
docker compose -f docker/docker-compose.yml up --build -d

# 4. 访问
# http://localhost:8080

# 5. 获取初始密码（首次启动自动生成）
# 方式一：查看容器日志
docker compose -f docker/docker-compose.yml logs backend | grep "密码"
# 方式二：读取密码文件
cat data/INITIAL_ADMIN_PASSWORD.txt
# 默认账号：admin，用上面获取的密码登录

# （可选）预设初始密码，Docker 与 Windows 两模式一致：
# 在仓库根目录创建 .env 文件，写入：
# CMDB_INITIAL_ADMIN_PASSWORD=YourPassword@123
# 然后用以下命令启动：
# docker compose --env-file .env -f docker/docker-compose.yml up --build -d
```

### 方式二：本地开发（Windows 11）

**一键启动**

项目根目录提供了 Windows 批处理脚本，双击即可同时启动前后端：

```
dev-start.bat    # 一键启动后端 + 前端（自动打开两个终端窗口）
dev-stop.bat     # 一键停止所有服务
```

> 前提：已完成下方的环境初始化（venv + pnpm install + alembic upgrade head）。

**环境初始化（仅首次）**

```powershell
# 后端
cd backend
uv venv
.venv\Scripts\activate
uv pip install -r requirements.txt
alembic upgrade head

# 前端
cd ..\frontend
pnpm install
```

**手动启动（如需分别调试）**

后端：

```powershell
cd backend
.venv\Scripts\activate
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

前端（新终端）：

```powershell
cd frontend
pnpm dev
```

访问 http://localhost:5173  
初始密码见 `backend/data/INITIAL_ADMIN_PASSWORD.txt`（首次启动自动生成）。

---

## 项目结构

```
z-cmdb/
├── backend/
│   ├── app/
│   │   ├── cli.py            # 管理 CLI（init-db / reset-admin）
│   │   ├── core/           # 配置、安全、依赖注入、加密
│   │   ├── models/         # SQLAlchemy 模型
│   │   ├── schemas/        # Pydantic v2 Schema
│   │   ├── routers/        # API 路由
│   │   ├── services/       # 业务逻辑
│   │   ├── repositories/   # 数据访问层
│   │   └── utils/          # nmap 解析等工具
│   ├── alembic/            # 数据库迁移脚本
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── views/          # 页面组件
│       ├── components/     # 通用组件
│       ├── api/            # API 封装
│       ├── stores/         # Pinia 状态
│       ├── styles/         # 全局样式 & Design Token
│       ├── types/          # TypeScript 类型定义
│       └── constants/      # 枚举常量（OS 选项、应用分类等）
├── docker/                 # Dockerfile & docker-compose
├── scripts/                # 运维脚本（重置密码、导出审计等）
├── secrets/                # JWT 密钥（不提交，仅 .example 文件）
├── img/                    # 功能截图
└── README.md
```

---

## nmap 扫描参考

```bash
# 快速扫描（常用端口）
nmap -sV -T4 -oX scan_result.xml 192.168.1.0/24

# 全端口扫描
nmap -sV -p- -T4 -oX scan_full.xml 192.168.1.0/24

# 指定端口 + OS 识别
nmap -sV -O -p 22,80,443,3306,6379,8080 -oX scan_web.xml 192.168.1.0/24
```

扫描完成后，将 `.xml` 文件上传到平台「扫描批次」页面即可。

---

## 安全说明

- 密码使用 argon2id 哈希（memory=64MB, time=3, parallelism=4）
- JWT 支持 access token（短期）+ refresh token（长期）
- 登录失败超过阈值自动锁定账户
- 所有响应头包含 CSP / X-Content-Type-Options / X-Frame-Options
- 审计日志通过数据库触发器保证不可篡改
- LLM 调用前对资产数据脱敏，核心资产可强制走本地模型

---

## 忘记密码 / 重置管理员

**Docker 环境：**

```bash
# 重置为随机密码（新密码打印到终端并写入 data/INITIAL_ADMIN_PASSWORD.txt）
docker compose -f docker/docker-compose.yml exec backend python -m app.cli reset-admin

# 重置为指定密码
docker compose -f docker/docker-compose.yml exec backend python -m app.cli reset-admin --password 'YourNew@Pass1'
```

**本地开发：**

```powershell
cd backend
.venv\Scripts\activate
python -m app.cli reset-admin
# 或指定密码：
python -m app.cli reset-admin --password 'YourNew@Pass1'
```

---

## ⚠️ 注意事项

**本项目不建议部署到正式生产环境。**

Z-CMDB Lite 的设计定位是个人或小团队的本机工具，适合以下使用方式：

- 部署在**本机或内网工作站**上，随用随启动
- 用完后关闭服务（`dev-stop.bat` 或直接关终端），不长期暴露在网络上
- **不要将服务端口暴露到公网**，如确需远程访问请配合 VPN 或 SSH 隧道
- 数据库为 SQLite 单文件（`backend/data/cmdb.db`），定期备份即可
- 默认管理员密码请在首次登录后立即修改（系统会强制要求）

如果你的场景涉及多人并发写入（>50 人）、高可用、或需要对外提供服务，请考虑使用 PostgreSQL 等生产级数据库方案。

---

## 更新日志

### V0.2（2026-06-19）

**资产总览**
- 新增 `/dashboard` 资产总览页面，作为登录后默认首页
- 8 类 KPI 指标卡片（资产总数、在线/离线/已下线、危险端口、影子资产、本月变更、扫描覆盖率），带数字翻牌动效
- 网络区域拓扑图（ECharts force-directed），按 `network_zone` 聚合，核心资产红色边框
- 资产分布环形图，支持网络区域/资产类型/重要性/操作系统四维度切换
- 端口暴露面：开放端口 Top 10 水平柱状图 + 按区域分布环形图
- 危险端口告警滚动列表，按严重性着色（高危脉冲动画），悬停暂停
- 影子资产（缺字段 + 长期离线）Tab 切换展示
- 资产变化时间线、审计与 LLM 活动流滚动播报
- 后端聚合接口 `GET /api/reports/dashboard-summary`，SQL 聚合 + 30s TTL 缓存，单次刷新仅一次请求
- 危险端口清单与高危区域从硬编码迁入 `system_configs` 配置，报表与总览共用同一判定逻辑
- 布局持久化（个人布局 + 全局默认），`system_configs` KV 存储

**Docker 部署修复**
- 后端依赖改用 `/opt/venv` 虚拟环境，解决 `docker exec` 下 `import sqlalchemy` 失败
- 新增应用内 CLI `python -m app.cli`（`init-db` / `reset-admin`），无需拷贝 scripts 进容器
- 初始密码可控：支持 `CMDB_INITIAL_ADMIN_PASSWORD` 环境变量预设，未设置则随机生成并写入 `data/INITIAL_ADMIN_PASSWORD.txt`
- 新增 `COOKIE_SECURE` 配置项，修复 HTTP 部署下 refresh token cookie 被浏览器拒绝的问题
- 新增 `.env.example` 环境变量模板
- 本地开发脚本（`scripts/reset_admin.py`、`init_db.py`）修正路径逻辑，复用 CLI 服务层

**拓扑图优化**
- 修复路由到 Ollama 时复用 OpenRouter 模型名导致 502 的 Bug
- 新增 Ollama 可用性检测，不可用时给出明确中文提示（而非晦涩的 502）
- 新增 `llm_ollama_model` 独立配置，Ollama 路由使用专用模型名
- LLM 提供方简化为「自定义」和「本地」两个选项，自定义支持任意 OpenAI 兼容 API
- 拓扑图页面新增「生成日志」Tab，显示 LLM 调用过程和详情（提供方/模型/耗时）
- 修复配置页面保存时掩码值覆盖真实 API Key 的 Bug

**其他改进**
- 修复修改密码 422 错误：前端密码策略校验（>= 12 位 + 大小写数字符号）与后端对齐
- 422 Pydantic 校验错误信息正确展示（从 `detail` 数组提取 `msg`）
- 后端 `llm_service.get_provider()` 不再校验 provider 名称，非 ollama 一律走 OpenAI 兼容接口

---

## License

[MIT](LICENSE)

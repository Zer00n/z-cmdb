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

<!-- 截图：资产列表页 -->
<!-- img/002.png -->

- 支持物理服务器、虚拟机、**云服务器**、网络设备、其他五种资产类型
- 云服务器选择后，网络区域自动切换为云服务商（阿里云 / 腾讯云 / 华为云 / AWS / Azure / GCP）
- 多维度筛选：网络区域、资产类型、重要性、状态
- 全文搜索：IP、主机名、资产编号、业务系统、**应用名称**（如 nginx、mysql）
- 批量操作：批量修改负责人、业务系统、重要性、网络区域
- 导出：标准 CSV + 威胁狩猎助手兼容格式

### 📋 资产详情

<!-- 截图：资产详情页 -->
<!-- img/004.png -->

三个标签页一站式查看：

| 标签页 | 内容 |
|--------|------|
| 基本信息 | 资产编号、IP/MAC/主机名、OS、归属、硬件、采购保修 |
| 端口 | 扫描发现的开放端口，含服务名、版本、状态 |
| 应用 | 手动登记或扫描提取的应用清单，含版本、端口、安装路径 |

**端口与应用双向同步**：手动新增应用时填写端口，自动写入端口表；nmap 扫描确认导入时，有 service_name 的端口同步生成应用记录。

### 📡 扫描批次

<!-- 截图：扫描批次 / 差异确认页 -->
<!-- img/007.png img/008.png -->

1. 在跳板机运行 nmap，生成 XML 报告
2. 上传到平台，自动解析并与现有资产做差异分析
3. 差异分为四类：**新发现** / **变更** / **消失** / **恢复**
4. 人工审核每台主机的端口变更详情后确认导入
5. 消失主机不立即删除，`missing_count + 1`，超过阈值才标记离线

### 🗺 拓扑图（AI 生成）

<!-- 截图：拓扑图编辑器 -->
<!-- img/009.png -->

- 一键调用 LLM 生成 drawio 网络拓扑图初稿
- 支持 DeepSeek / OpenRouter / 本地 Ollama
- 资产数据**自动脱敏**后投喂 LLM（IP → 占位符，业务系统 → 代号）
- 核心资产可配置强制走本地模型，敏感数据不出内网
- 生成后可在内嵌 drawio 编辑器中手工调整，支持版本管理和回滚

### 📊 安全报表

<!-- 截图：报表仪表盘 -->
<!-- img/010.png -->

- 资产分布：网络区域、重要性、操作系统、资产类型
- 端口暴露面分析：Top 端口、高危端口统计
- 扫描覆盖率：最近扫描时间分布
- 威胁狩猎助手兼容导出：按"资产 × 应用"展开，含 environment / criticality / exposure_scope / vendor 字段

### 📝 审计日志

<!-- 截图：审计日志页 -->
<!-- img/011.png -->

- 记录所有登录、增删改、导出、LLM 调用操作
- **不可篡改**：SQLite 触发器在数据库层禁止 UPDATE / DELETE
- 支持按动作类型、用户、目标类型筛选

### 👥 用户与权限

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
docker-compose -f docker/docker-compose.yml up --build -d

# 4. 访问
# http://localhost:8080
# 默认账号：admin / Admin@123456（首次启动自动创建）
```

### 方式二：本地开发

**后端**

```bash
cd backend

# 推荐使用 uv（也可用 pip）
uv venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/macOS

uv pip install -r requirements.txt

# 初始化数据库
alembic upgrade head

# 启动
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**前端**（新终端）

```bash
cd frontend
pnpm install
pnpm dev
```

访问 http://localhost:5173

---

## 项目结构

```
z-cmdb/
├── backend/
│   ├── app/
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

## License

[MIT](LICENSE)

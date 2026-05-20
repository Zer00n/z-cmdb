# CMDB Lite

> 准确性优先、零门槛、面向中小团队的轻量级配置管理数据库

## 项目简介

CMDB Lite 面向 5～50 人规模的中小企业 IT 运维和安全工程师，通过手动 nmap 扫描上传的方式管理内网/办公网/IDC 资产，用于日常运维、安全审计、HVV 排查、等保备查。

## 技术栈

| 层 | 选型 |
|---|------|
| 后端语言 | Python 3.11+ |
| Web 框架 | FastAPI |
| 数据库 | SQLite 3 (WAL 模式) |
| ORM | SQLAlchemy 2.0 |
| 数据迁移 | Alembic |
| 前端框架 | Vue 3 + Vite + TypeScript |
| UI 组件库 | Element Plus |
| 状态管理 | Pinia |
| 部署 | Docker + docker-compose |

## 快速开始

### Windows 11 开发环境

```powershell
# 后端
cd backend
uv venv
.\.venv\Scripts\activate
uv pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 前端（新终端）
cd frontend
pnpm install
pnpm dev
```

### Docker 部署

```bash
# 首次启动
cp secrets/jwt_secret.txt.example secrets/jwt_secret.txt
# 编辑 jwt_secret.txt，填入随机字符串

docker-compose -f docker/docker-compose.yml up --build
```

访问 http://localhost:8080

### Linux 生产部署

参见 `docs/deployment.md`

## 项目结构

```
cmdb-lite/
├── backend/          # FastAPI 后端
│   ├── app/          # 应用代码
│   │   ├── core/     # 配置、安全、依赖注入
│   │   ├── models/   # SQLAlchemy 模型
│   │   ├── schemas/  # Pydantic schema
│   │   ├── routers/  # 路由
│   │   ├── services/ # 业务逻辑
│   │   ├── repositories/ # 数据访问层
│   │   └── utils/    # 工具函数
│   ├── alembic/      # 数据库迁移
│   └── tests/        # pytest 测试
├── frontend/         # Vue 3 前端
│   └── src/
│       ├── views/    # 页面
│       ├── components/ # 组件
│       ├── api/      # API 封装
│       ├── stores/   # Pinia 状态
│       ├── styles/   # 全局样式
│       └── types/    # TypeScript 类型
├── docker/           # Docker 配置
├── docs/             # 文档
└── scripts/          # 运维脚本
```

## 文档

- [产品需求文档](docs/CMDB-Lite-PRD-v2.md)
- [开发工作手册](docs/CMDB-Lite-Playbook-v1.md)
- [nmap 命令参考](docs/nmap-cmd-reference.md)
- [API 规格](docs/api-spec.md)
- [部署指南](docs/deployment.md)

## License

MIT

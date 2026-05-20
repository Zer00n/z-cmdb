# CMDB Lite 部署指南

## 1. Docker 部署（推荐）

### 前置条件

- Docker 20.10+
- Docker Compose v2+

### 步骤

```bash
# 1. 克隆项目
git clone <repo-url> cmdb-lite && cd cmdb-lite

# 2. 配置 JWT Secret
cp secrets/jwt_secret.txt.example secrets/jwt_secret.txt
# 编辑 jwt_secret.txt，填入随机字符串（建议 32 位以上）

# 3. （可选）配置 LLM 主密钥
export LLM_MASTER_KEY="your-random-master-key"

# 4. 启动
docker-compose -f docker/docker-compose.yml up --build -d

# 5. 查看日志
docker-compose -f docker/docker-compose.yml logs -f backend
```

访问 http://localhost:8080

### 数据持久化

- `./data/cmdb.db` — SQLite 数据库文件
- `./uploads/` — 上传的 nmap XML 文件

### 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| DATABASE_URL | sqlite:///./data/cmdb.db | 数据库连接 |
| JWT_SECRET_FILE | /run/secrets/jwt_secret | JWT 密钥文件路径 |
| LLM_MASTER_KEY | （空，用 JWT_SECRET 派生） | LLM API Key 加密主密钥 |
| TZ | Asia/Shanghai | 时区 |
| APP_ENV | production | 环境标识 |

---

## 2. Linux 原生部署

适用于不允许安装 Docker 的环境（如国央企内网）。

### 前置条件

- Python 3.11+
- Node.js 20 LTS
- Nginx

### 步骤

```bash
# 1. 创建系统用户
sudo useradd -r -s /usr/sbin/nologin cmdb
sudo mkdir -p /opt/cmdb-lite
sudo chown cmdb:cmdb /opt/cmdb-lite

# 2. 部署后端
cd /opt/cmdb-lite
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
cd backend && alembic upgrade head

# 3. 构建前端
cd /opt/cmdb-lite/frontend
npm install -g pnpm
pnpm install && pnpm build

# 4. 配置 systemd
sudo cp /opt/cmdb-lite/docs/cmdb-lite.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now cmdb-lite

# 5. 配置 Nginx
sudo cp /opt/cmdb-lite/docker/nginx.conf /etc/nginx/conf.d/cmdb.conf
sudo systemctl reload nginx
```

### systemd 单元文件

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
Environment="PATH=/opt/cmdb-lite/.venv/bin"
ExecStart=/opt/cmdb-lite/.venv/bin/gunicorn \
    -k uvicorn.workers.UvicornWorker \
    -w 2 -b 127.0.0.1:8000 app.main:app
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

---

## 3. Windows 11 开发环境

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

### 注意事项

- 数据库文件放在项目目录下 `backend/data/cmdb.db`，不要放在 OneDrive 同步目录
- Git 配置 `core.autocrlf=input`
- 杀软白名单加入项目目录

---

## 4. HTTPS 配置

生产环境强烈建议启用 HTTPS。参考 `docker/nginx.conf` 中注释掉的 443 server block。

需要准备：
- SSL 证书（`/etc/ssl/cmdb.crt`）
- SSL 私钥（`/etc/ssl/cmdb.key`）

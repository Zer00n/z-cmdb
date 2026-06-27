# Z-CMDB v0.6 部署说明

> 本文档面向运维和最终用户，覆盖三种部署方式：Windows 双击启动、Linux 裸机、Linux Docker。

---

## 重要警告

**`./data` 目录存放 SQLite 数据库，严禁放在以下位置：**
- 网络盘（NFS/SMB/CIFS）
- OneDrive / Dropbox / Google Drive 等同步目录
- 任何支持 WAL 锁异常的远程文件系统

SQLite 的 WAL 模式在这些路径上会导致锁异常或写入丢失。请始终使用本地磁盘。

**数据备份**：备份 `./data/cmdb.db` 文件即可（建议在服务停止状态下备份）。

---

## 1. Windows 双击启动

### 前置条件

- Windows 10/11 64 位
- 开发机：Python 3.12 (win_amd64) + pnpm + **联网**（需下载嵌入式 Python 和依赖包）
- 用户机器：**无需安装任何软件，无需联网**

### 首次部署（开发机执行）

```cmd
cd z-cmdb
deploy\windows\build_bundle.bat
```

产物在 `dist\Z-CMDB\`，包含嵌入式 Python + 全部依赖 + 前端 + 启动器（约 160MB，打包需几分钟）。

> <b><font color="red">⚠️ build_bundle.bat 会清空整个 dist\ 目录！首次打包不影响，但后续升级时请先备份 dist\Z-CMDB\data\cmdb.db，或使用下方「增量更新」方式。</font></b>

将 `dist\Z-CMDB\` 文件夹拷贝到目标机器，双击 `start.bat` 即可。

### 使用

1. 双击 `start.bat`
2. 浏览器自动打开 `http://127.0.0.1:8000`
3. 使用默认账号 `admin` 登录，初始密码见 `data\INITIAL_ADMIN_PASSWORD.txt`（首次启动自动生成，登录后修改密码该文件会自动删除）

**端口修改**：`start.bat 9000`（传入端口号作为参数）

**移动文件夹**：整个 `Z-CMDB` 文件夹可自由移动到任何盘符，数据跟随。

### 升级（推荐：增量更新）

GitHub 有新版本时，只需覆盖代码区，**不动嵌入式 Python 和依赖包**：

> <b><font color="red">⚠️ 只覆盖 app\、alembic\、static\、alembic.ini，不要动 data\ 和 .env，否则数据库和密钥会丢失！</font></b>

```cmd
:: 1. 停止服务（关闭 start.bat 窗口）

:: 2. 在开发机重新打包前端
cd z-cmdb
deploy\windows\build_bundle.bat

:: 3. 将以下目录从 dist\Z-CMDB\ 拷贝到目标机器覆盖（保留 data\ 和 .env 不动）
::    app\          ← 后端代码
::    alembic\      ← 数据库迁移
::    static\       ← 前端产物
::    alembic.ini

:: 4. 双击 start.bat（自动运行新迁移）
```

> **注意**：`start.bat` 启动时会自动执行 `alembic upgrade head`，无需手动迁移。

### 升级（备选：全量重打包）

如果依赖版本有变化，或需要完整重建：

> <b><font color="red">⚠️ 全量重打包会删除整个 dist\ 目录，必须先备份 data\cmdb.db！否则所有资产数据、用户账号、审计日志将永久丢失。</font></b>

```cmd
:: 1. 停止服务

:: 2. 备份数据
copy dist\Z-CMDB\data\cmdb.db  C:\backup\cmdb.db

:: 3. 重新打包
deploy\windows\build_bundle.bat

:: 4. 恢复数据
mkdir dist\Z-CMDB\data
copy C:\backup\cmdb.db  dist\Z-CMDB\data\cmdb.db

:: 5. 双击 start.bat
```

---

## 2. Linux 裸机部署

### 前置条件

- Python 3.12+
- 前端已 build（`cd frontend && pnpm build`），产物拷贝到 `backend/static/`

### 操作步骤

```bash
cd z-cmdb/deploy/linux
chmod +x start.sh
./start.sh
```

脚本会自动：
1. 创建 `.venv`（首次）
2. 安装依赖（使用清华镜像，可通过 `PIP_MIRROR` 环境变量覆盖）
3. 生成 `.env`（首次，含随机 JWT_SECRET）
4. 运行数据库迁移
5. 启动 uvicorn（监听 `0.0.0.0:8000`）

**二次执行**：不会重装依赖、不会覆盖 `.env`、不会丢失数据。

**首次登录**：用户名 `admin`，初始密码见 `data/INITIAL_ADMIN_PASSWORD.txt`（首次启动自动生成，登录后修改密码该文件会自动删除）。

### systemd 服务（可选）

```bash
# 创建专用用户
sudo useradd -r -s /sbin/nologin cmdb

# 部署代码
sudo cp -r z-cmdb /opt/z-cmdb
sudo chown -R cmdb:cmdb /opt/z-cmdb

# 安装服务
sudo cp deploy/linux/z-cmdb.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now z-cmdb

# 查看日志
sudo journalctl -u z-cmdb -f
```

### 升级

```bash
sudo systemctl stop z-cmdb
sudo cp -r /opt/z-cmdb/backend/data /tmp/z-cmdb-backup  # 备份
# 覆盖代码（保留 data/ 和 .env）
sudo systemctl start z-cmdb
```

---

## 3. Linux Docker 部署

### 前置条件

- Docker 20.10+
- Docker Compose v2
- 前端已 build（`cd frontend && pnpm build`）

### 一键部署

```bash
cd z-cmdb/deploy/docker
export JWT_SECRET=$(python3 -c "import secrets;print(secrets.token_urlsafe(48))")
./release.sh
```

脚本会自动：
1. 构建基础镜像 `z-cmdb-base:0.6`（含依赖，偶尔重建）
2. 构建应用镜像 `z-cmdb-app:0.6`（仅 COPY 代码，秒级）
3. 创建 `./data` 目录
4. 启动容器

访问 `http://localhost:8000`。

**首次登录**：用户名 `admin`，初始密码见宿主 `./data/INITIAL_ADMIN_PASSWORD.txt`（首次启动自动生成，登录后修改密码该文件会自动删除）。

### 离线分发

```bash
OFFLINE=1 ./release.sh
# 产物：z-cmdb-base-0.6.tar.gz
# 目标机器：docker load < z-cmdb-base-0.6.tar.gz
```

### 数据持久化

数据库通过 bind mount 落在宿主 `./data` 目录：
```bash
docker compose down
docker compose up -d
# 数据仍在 ./data/cmdb.db
```

### 升级

```bash
# 备份
cp data/cmdb.db data/cmdb.db.bak

# 重建（仅应用层，秒级）
docker compose up -d --build
```

---

## 配置说明

所有环境共享以下 `.env` 配置项：

| 变量 | 说明 | 默认值 |
|---|---|---|
| `APP_ENV` | 运行环境 | `production` |
| `DATABASE_URL` | 数据库连接 | `sqlite:///./data/cmdb.db` |
| `JWT_SECRET` | JWT 签名密钥（≥32 字符） | 自动生成 |
| `CORS_ORIGINS` | 允许的前端地址 | 按部署方式生成 |
| `PORT` | 服务端口 | `8000` |

**生产环境密钥校验**：若 `APP_ENV=production` 且 `JWT_SECRET` 为默认值或长度 <32，服务拒绝启动。

---

## 常见问题

**Q: 忘记管理员密码？**
A: 删除 `data/cmdb.db`（会丢失所有数据），重新启动会自动生成新的 `data/INITIAL_ADMIN_PASSWORD.txt`。默认账号 `admin`，登录后修改密码该文件会自动删除。

**Q: 端口被占用？**
A: Windows: `start.bat 9000`；Linux: `PORT=9000 ./start.sh`。注意：首次运行后 `.env` 中的 `CORS_ORIGINS` 已写入原端口，如需更换端口请同时删除 `.env` 让其重新生成。

**Q: Docker 容器重启后数据还在吗？**
A: 是的，数据库通过 bind mount 落在宿主 `./data`，容器删除也不影响。

---

*Z-CMDB v0.6.0 | 2026-06-27*

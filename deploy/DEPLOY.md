# Z-CMDB v0.6.5 部署说明

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
- pnpm 或 npm（用于自动构建前端，如已预编译可跳过）

### 操作步骤

```bash
cd z-cmdb/deploy/linux
chmod +x start.sh
./start.sh
```

脚本会自动：
1. 检测并构建前端（如 `frontend/dist/` 不存在）
2. 同步静态文件到 `backend/static/`
3. 创建 `.venv`（首次）
4. 安装依赖（使用清华镜像，可通过 `PIP_MIRROR` 环境变量覆盖）
5. 生成 `.env`（首次，含随机 JWT_SECRET）
6. 启动 uvicorn（监听 `0.0.0.0:8000`）

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
- pnpm 或 npm（用于自动构建前端，如已预编译可跳过）

### 一键部署

```bash
cd z-cmdb/deploy/docker
export JWT_SECRET=$(python3 -c "import secrets;print(secrets.token_urlsafe(48))")
./release.sh
```

脚本会自动：
0. 检测并构建前端（如 `frontend/dist/` 不存在）
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

## 数据库加密（SQLite 静态加密）

> v0.7 新增。`.db` 文件单独泄露后无法用任何 SQLite 工具打开，必须在程序内通过管理员口令或恢复码解锁才能访问数据。加密采用信封加密（envelope encryption）：DEK（32 字节随机密钥）+ KEK（口令经 Argon2id 派生）。

### 加密原理

- **DEK（Data Encryption Key）**：32 字节随机密钥，是数据库的真实加密密钥，永不明文落盘，解锁后仅驻留内存
- **KEK（Key Encryption Key）**：管理员口令经 Argon2id 派生，用于包裹/解包 DEK
- **keystore.json**：存于 `data/` 目录，每条记录包含：salt + nonce + wrapped DEK（全是密文/随机数据）。单独泄露 keystore 无害（无口令解不开）
- **防护边界**：只防文件层窃取，不防运行态进程内存 dump（见 PRD §1 非目标）

### 首次启动（Setup）

应用以 **LOCKED** 态启动（DB 引擎未初始化）：

1. 浏览器访问应用，自动进入 Setup 页
2. 设置管理员用户名（默认 `admin`）+ 口令（≥12 位，含大小写+数字+特殊字符）
3. 系统自动生成**一次性恢复码**（base32 分组，如 `ABCD-EFGH-IJKL-...`）
4. **恢复码务必立即离线保存**（纸质、密码管理器），关闭后不再可查看
5. Setup 完成，应用自动解锁进入正常模式

> 桌面/裸机首次启动：启动脚本不再自动建库，改为浏览器打开后走 Setup 流程。

### 日常解锁

| 场景 | 方式 | 操作 |
|---|---|---|
| **桌面（交互，最强）** | 浏览器解锁页 | 输入管理员口令 → 解锁 + 自动登录 |
| **恢复码应急** | 浏览器或 API | 输入恢复码 → 仅解锁，不自动登录（需再用真实口令登录） |
| **裸机无人值守** | systemd 注入 | 在 `.unlock.env` 写入 `CMDB_UNLOCK_PASSWORD` 后重启，**用后立即删除** |
| **Docker 无人值守** | compose 注入 | `CMDB_UNLOCK_PASSWORD="xxx" docker compose up -d` |
| **更安全替代** | systemd-ask-password | 口令通过终端交互输入，永不落盘 |

### 解锁强度分档

| 档位 | 方式 | 口令落盘 | 抗单独文件窃取 | 抗同机攻击 |
|---|---|---|---|---|
| 最强 | 交互解锁（浏览器/systemd-ask-password） | ❌ 不落盘 | ✅ | ❌ |
| 中等 | CMDB_UNLOCK_PASSWORD 启动注入 | ⚠️ 环境变量（临时） | ✅ | ❌ |
| Phase 2 | OS 密钥库 / TPM | 设计中 | ✅ | 部分 |

### 改密 / 增删管理员

- **改密**（用户自己改）：库内 argon2 哈希与 keystore 的 wrapped-DEK 记录原子同步，库本身一字节不动。旧口令立即失效
- **增管理员**：管理员在系统创建新用户后，自动入册 keystore（用初始口令包裹 DEK），具备解锁能力
- **删管理员**：禁用用户时自动移除 keystore 记录，其口令立即不能再解锁

### 恢复码 — 唯一生命线

恢复码是**所有管理员口令丢失时的唯一出路**：

- 用恢复码解锁后，仍需用真实管理员口令登录（恢复码只解锁库，不签发会话）
- **恢复码丢失 = 数据永久不可读**。这是加密的代价，请妥善保管
- 丢失口令但有恢复码：恢复码解锁 → 改密 → 继续使用
- 口令和恢复码都丢失：无法恢复，只能从备份重建

### 备份要求

备份对象：**加密库 `cmdb.db` + keystore.json**（缺一不可）

- keystore 含密文，可安全备份到云盘/异地，单独泄露无害
- keystore 丢失且无恢复码 = 数据永久不可读
- `-wal` / `-shm` 侧文件也应一起备份（WAL 模式下有未合并数据）

### 存量明文库迁移（一次性工具）

现有 v0.6 明文库可一次性加密迁移，**不丢数据**：

```bash
# 1. 停止服务
# 2. 备份（以防万一）
cp data/cmdb.db data/cmdb.db.plaintext.bak

# 3. 执行迁移（在 backend/ 下）
cd backend
PYTHONPATH=. python tools/encrypt_existing_db.py \
    --password '<管理员口令>' \
    --db data/cmdb.db

# 4. 输出一次性恢复码 → 立即离线保存
# 5. 启动服务 → 用管理员口令解锁
```

迁移过程：
- 自动加密库 + 生成 keystore + 恢复码
- 校验每张表行数一致
- 安全覆盖明文原件（随机覆写，SSD 不保证真擦除，但文件已被密文替代）
- `--keep-plain` 调试用：保留明文原件（安全删除生效前，仅限受控环境）

---

## 常见问题

**Q: 忘记管理员密码？**
A: 使用恢复码解锁（一次性，不自动登录），然后用任意管理员口令登录后改密。如果恢复码也丢失：数据永久不可读，请从备份恢复（加密库 + keystore）。**妥善保管恢复码是唯一的保险。**

**Q: 端口被占用？**
A: Windows: `start.bat 9000`；Linux: `PORT=9000 ./start.sh`。注意：首次运行后 `.env` 中的 `CORS_ORIGINS` 已写入原端口，如需更换端口请同时删除 `.env` 让其重新生成。

**Q: Docker 容器重启后数据还在吗？**
A: 是的，数据库通过 bind mount 落在宿主 `./data`，容器删除也不影响。

---

*Z-CMDB v0.6.5 | 2026-06-28*

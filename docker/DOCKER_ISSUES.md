# Docker 部署问题记录与修复说明

## 问题 1: nginx.conf 路径无法访问

**现象**: 前端构建失败
```
COPY ./nginx.conf /etc/nginx/conf.d/default.conf
ERROR: "/nginx.conf": not found
```

**原因**: Dockerfile.frontend 的 build context 为 `../frontend`，但 `nginx.conf` 位于 `../docker/nginx.conf`。
Docker COPY 不能访问 context 之外的文件。

**修复**: 将 frontend 的 build context 改为项目根目录 `..`，同时调整 Dockerfile 中的 COPY 路径。

---

## 问题 2: pnpm 版本与 Node.js 不兼容

**现象**: 前端构建失败
```
ERR_UNKNOWN_BUILTIN_MODULE: No such built-in module: node:sqlite
```

**原因**: `corepack prepare pnpm@latest` 安装了 pnpm v11.x，该版本要求 Node.js >= 22.13，
但 Dockerfile 使用的是 `node:20-alpine`（Node.js v20.20.2）。pnpm 11.x 使用了 `node:sqlite`
这个仅在 Node 22+ 中存在的内置模块。

**修复**: 将 pnpm 版本固定为 `pnpm@9`，兼容 Node 20。

---

## 问题 3: pnpm workspace 配置冲突

**现象**: 前端构建失败
```
ERROR  packages field missing or empty
```

**原因**: 前端目录存在 `pnpm-workspace.yaml` 文件（内容为 `allowBuilds` 配置），
pnpm 检测到此文件后进入 workspace 模式，但该文件缺少 `packages` 字段，
导致 `pnpm run build` 报错。

**修复**: 在 Dockerfile 构建阶段删除 `pnpm-workspace.yaml`：
```dockerfile
RUN rm -f pnpm-workspace.yaml && pnpm run build
```

---

## 问题 4: SQLite 数据库文件权限不足

**现象**: 后端启动失败，健康检查不通过
```
sqlite3.OperationalError: unable to open database file
```

**原因**: 容器以非 root 用户 `cmdb`（UID 1001）运行，但挂载的 `data/` 和 `uploads/` 目录
属主为宿主机用户（UID 1000），cmdb 用户没有写入权限。

**修复**: 在 Dockerfile 的 entrypoint 中添加 chown 逻辑，或在宿主机上设置正确的目录权限。
最终方案：在 Dockerfile.backend 中将 entrypoint 改为自定义脚本，先用 root 修复权限再切换用户运行应用。

---

## 问题 5: JWT Secret 文件路径未配置

**现象**: 容器运行时使用默认 JWT secret（`change-me-in-production`），存在安全风险。

**原因**: docker-compose.yml 配置了 Docker secrets 挂载到 `/run/secrets/jwt_secret`，
但未设置 `JWT_SECRET_FILE` 环境变量，导致应用无法从 secrets 文件读取密钥。

**修复**: 在 docker-compose.yml 的 backend environment 中添加：
```yaml
- JWT_SECRET_FILE=/run/secrets/jwt_secret
```

---

## 问题 6: Python stdout 缓冲导致初始管理员密码丢失

**现象**: `docker logs cmdb-backend` 中看不到首次启动时打印的管理员密码。

**原因**: Python 在非 TTY 环境下（Docker 容器）会对 stdout 进行缓冲，
`print()` 的输出不会立即刷新到容器日志。加上 `gosu`/`su` 等降权工具创建子进程，
stdout 缓冲区内容可能在进程退出前丢失。

**修复**: 在 Dockerfile.backend 中设置环境变量禁用 Python 输出缓冲：
```dockerfile
ENV PYTHONUNBUFFERED=1
```

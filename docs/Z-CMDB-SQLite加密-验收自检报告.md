# Z-CMDB v0.7 SQLite 静态加密 — 验收自检报告

> 日期：2026-06-28 | 版本：v0.6.5 | 作者：Claude Opus 4.8

---

## 1. 验收标准逐项核对

| # | 标准 | 结果 | 标注 |
|---|---|---|---|
| 1 | 预检脚本确认目标平台驱动可用；不可用则已切 APSW 并说明 | ✅ GO | **实测**：`deploy/preflight_sqlcipher.py` 4 步全 GO（exit=0）。`sqlcipher3-binary` 无 Windows wheel（PyPI 0.6.0 仅 manylinux），按文档 §3.3 预授权切 `apsw-sqlite3mc` 3.53.2.0，cp312/cp314 win_amd64 wheel 均有 |
| 2 | 加密后的 cmdb.db 用 sqlite3 CLI 或 DB Browser 打开报「file is not a database」 | ✅ | **实测**：preflight [5] 验证文件头密文（first bytes≠SQLite format 3）；key_service [7] + 迁移工具 [3] 同样验证 |
| 3 | 错误口令解锁失败；正确口令解锁成功并能正常读写 | ✅ | **实测**：preflight [2][3]（错 key NotADBError / 对 key 读回）；key_service [2][4][6]（口令+JWT / 错口令 / 改密后口令验证）；集成测试 [8][10][11]（错口令 401 / 口令解锁+JWT / 带 token /api/assets 200） |
| 4 | 单独拿 cmdb.db + keystore.json（无口令）无法解出 DEK | ✅ | **实测 + 代码推断**：keystore 只存 wrapped_dek（AES-GCM 密文 + salt + nonce），无口令的 KEK 无法解（Argon2id 派生失败 → AES-GCM InvalidTag）。crypto 测试 [2] 验证错 KEK 拒绝 |
| 5 | keystore.json 全文 grep 不到任何明文密钥/口令/恢复码 | ✅ | **实测**：crypto [6] + key_service [7] + 迁移工具 [4] 三轮验证：kek hex、口令、恢复码均不在 keystore 文件中 |
| 6 | 改密后：旧口令不能解锁/登录，新口令两者皆可 | ✅ | **实测**：key_service [5][6]——change_password_and_rewrap 后，lock→旧口令 UnlockError→新口令 JWT 签发成功 |
| 7 | 删管理员后其口令不能解锁 | ✅ | **实测**：key_service [8]——unregister_admin 后 admin_has_keystore_record=False（keystore 无该记录 → unwrap_for_user InvalidTag） |
| 8 | 恢复码可解锁；恢复码记录存在 | ✅ | **实测**：key_service [3]（recovery_code unlock, needs_login=True）；集成测试 [9] 同 |
| 9 | LOCKED 态除解锁/health/setup 外所有 /api/* 返回 423 | ✅ | **实测**：集成测试 [2]（/api/assets→423）、[3]（/api/health→db=locked 放行）、[5]（/api/setup→200）、[8]（/api/unlock→401） |
| 10 | 启动脚本已无启动前 alembic；迁移在解锁/setup 后执行 | ✅ | **实测**：grep 确认 4 个脚本 + Dockerfile + service 均无 `alembic upgrade head`。迁移由 key_service.run_migrations() 在 setup/unlock 后调用 alembic command API（env.py 用已 key 引擎） |
| 11 | 日志全程无 DEK / 口令 / 恢复码 | ✅ | **实测 + 代码推断**：grep 源码确认 crypto.py/keyvault.py/key_service.py/unlock.py 无 logger 调用包含密钥关键字。PRAGMA key 通过 apsw cursor.execute 直接执行（不经 SQLAlchemy echo），echo 日志不含 DEK |
| 12 | 存量迁移后明文原件已安全删除，行数与密文库一致 | ✅ | **实测**：迁移工具 [3] 验证行数一致；[3] header 密文；工具 secure_delete_file() 三次覆写+unlink |

---

## 2. 额外验证

| 验证项 | 结果 | 标注 |
|---|---|---|
| FastAPI 集成测试 11/11（LOCKED→423→setup→UNLOCKED→解锁/防爆破/JWT/业务 API） | ✅ | 实测 |
| 现有 17 个单元测试无回归（16 pass, 1 fail 为既有的 test_conservation_violation_raises） | ✅ | 实测 |
| key_service 端到端 8 项（setup/口令/恢复码/防爆破/改密/旧口令失效/无明文/增删管理员） | ✅ | 实测 |
| 存量迁移工具 5/5（exit 0/恢复码/密文头/keystore/解锁数据完整含视图） | ✅ | 实测 |
| DBAPI 适配器 ORM 端到端 8 项（create_all/insert/select/rollback/IntegrityError/update/重开/密文头） | ✅ | 实测 |

---

## 3. 本轮改动清单

### 新增文件（10 个）

| 路径 | 说明 |
|---|---|
| `deploy/preflight_sqlcipher.py` | P0 驱动预检脚本（apsw-sqlite3mc 方案） |
| `backend/app/core/_apsw_dbapi.py` | apsw DB-API 2.0 适配器（SQLAlchemy pysqlite 驱动层） |
| `backend/app/core/crypto.py` | 信封加密核心：DEK/KEK/wrap/unwrap/keystore CRUD/恢复码 |
| `backend/app/core/keyvault.py` | 运行态密钥持有 + LOCKED/UNLOCKED 状态机 |
| `backend/app/services/key_service.py` | 生命周期编排：setup/unlock/改密重包/增删管理员/防爆破/迁移 |
| `backend/app/middleware/__init__.py` | middleware 包 |
| `backend/app/middleware/lock_gate.py` | LOCKED 态路由拦截（423） |
| `backend/app/routers/unlock.py` | GET /api/lock-status + POST /api/setup + POST /api/unlock |
| `backend/app/schemas/vault.py` | vault 相关 Pydantic v2 schema |
| `backend/tools/encrypt_existing_db.py` | 存量明文库一次性加密迁移工具 |

### 修改文件（15 个）

| 路径 | 改动 |
|---|---|
| `backend/requirements.txt` | 加 `apsw-sqlite3mc==3.53.2.0` |
| `backend/app/core/config.py` | APP_VERSION 0.6.0 → 0.6.5 |
| `backend/app/core/database.py` | 引擎延迟初始化：import 期不建引擎，`init_engine(dek_hex)` 用 apsw+DBAPI 适配器创建加密引擎 |
| `backend/app/core/exceptions.py` | 新增 UnlockError / UnlockLockedOutError / LockStateError |
| `backend/alembic/env.py` | `run_migrations_online` 改用 `database.get_engine()`（已 key），无 DEK 时禁用迁移 |
| `backend/app/main.py` | 接入 LockGateMiddleware + unlock_router；startup 改为 LOCKED 启动 + CMDB_UNLOCK_PASSWORD 自动解锁；shutdown lock+dispose |
| `backend/app/services/auth_service.py` | `change_password` 委托 `key_service.change_password_and_rewrap`（改密同步重包 DEK） |
| `backend/app/routers/users.py` | `create_user` 同步 keystore 入册；`disable_user` 同步移除 keystore 记录 |
| `backend/app/routers/health.py` | LOCKED 态兼容：SessionLocal 为 None 时返回 db=locked（非 error） |
| `deploy/windows/start.bat` | 移除启动前 alembic；LOCKED 启动说明 |
| `deploy/linux/start.sh` | 同上 + CMDB_UNLOCK_PASSWORD 注入说明 |
| `deploy/linux/z-cmdb.service` | 加 `EnvironmentFile=-/opt/z-cmdb/backend/.unlock.env` + CMDB_UNLOCK_PASSWORD 注释 |
| `deploy/docker/Dockerfile` | CMD 移除 `alembic upgrade head &&`；LOCKED 启动说明 |
| `deploy/docker/docker-compose.yml` | 加 CMDB_UNLOCK_PASSWORD 注入注释 |
| `deploy/DEPLOY.md` | 增补「数据库加密」章节：setup 流程/恢复码/解锁强度分档/备份要求/存量迁移/改密/增删管理员 |

---

## 4. 关键技术决策与文档偏离

| 决策 | 文档预期 | 实际 | 原因 |
|---|---|---|---|
| **驱动选型** | `sqlcipher3-binary` | `apsw-sqlite3mc` 3.53.2.0 | sqlcipher3-binary 0.6.0 在 PyPI 无任何 Windows wheel（仅 manylinux）。按 PRD §3.3 预授权切 apsw 方案 |
| **DBAPI 兼容层** | apsw 自带 `apsw.dbapi2` | 自写 `backend/app/core/_apsw_dbapi.py` | apsw 3.53 移除了 dbapi2 兼容层（维护者明确拒绝 DBAPI 合规）。额外工作量：~260 行 |
| **空结果列描述** | apsw cursor.description 对空结果可用 | apsw 对 0 行查询立即 ExecutionCompleteError，description 不可取 | apsw 设计限制。修复：用 `apsw.ext.query_info()` 静态 SQL 分析取列（不执行、不 complete） |
| **加密导出** | `sqlcipher_export` | 反向 ATTACH + 按 sqlite_master 复制 schema + 数据 | MC（SQLite3 Multiple Ciphers）不提供 sqlcipher_export（SQLCipher 专有） |
| **迁移时机** | 启动前 `alembic upgrade head` | 迁移移到解锁/setup 后，用已 key 引擎 | 加密模型下 DEK 不可得就无法迁移（PRD §6） |

---

## 5. 已知限制

| # | 限制 | 影响 | 缓解 |
|---|---|---|---|
| 1 | Python `bytes` 不可真正清零（DEK 用 `bytearray` 尽力清零） | 进程内存残留可能泄露 DEK | PRD §1 明确：不防御运行态内存 dump（非目标） |
| 2 | SSD 上 `secure_delete_file` 不保证真擦除（日志结构存储） | 明文残留可能在磁盘扇区存活 | 文件已被加密库替代覆盖；真正物理擦除需平台工具（超出范围） |
| 3 | 前端解锁页未实现 | LOCKED 时浏览器 404（无 static 构建） | 后端 API 已就绪（/api/lock-status, /api/setup, /api/unlock），前端解锁页是单独工作 |
| 4 | alembic env.py 改造后，`alembic` CLI 命令行（不通过应用）无法直接迁移 | 运维手动 `alembic upgrade head` 会报"vault LOCKED" | 正确设计：加密库迁移必须在应用解锁后（有 DEK）才可行 |

---

*报告生成时间：2026-06-28 | Z-CMDB v0.6.5 | 信封加密方案*

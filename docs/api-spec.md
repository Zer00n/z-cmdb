# CMDB Lite API 规格

> 完整的 OpenAPI 文档可通过运行后端后访问 http://localhost:8000/docs 查看。
> 本文档为快速参考。

## 鉴权

所有 API（除 `/api/auth/login` 和 `/api/health`）需要在 Header 中携带：

```
Authorization: Bearer <access_token>
```

### POST /api/auth/login
登录，返回 access_token + 设置 refresh_token cookie。

### POST /api/auth/refresh
用 refresh_token cookie 换新 access_token。

### POST /api/auth/logout
注销，清除 refresh_token cookie。

### POST /api/auth/change-password
修改当前用户密码。

---

## 用户管理（仅 super_admin）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/users | 用户列表 |
| POST | /api/users | 创建用户 |
| GET | /api/users/{id} | 用户详情 |
| PATCH | /api/users/{id} | 更新用户 |
| DELETE | /api/users/{id} | 禁用用户（软删除） |

---

## 资产管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/assets | 资产列表（支持筛选/搜索/分页） |
| POST | /api/assets | 手动新增资产 |
| GET | /api/assets/export | CSV 导出 |
| GET | /api/assets/{id} | 资产详情（含端口） |
| PATCH | /api/assets/{id} | 更新资产 |
| DELETE | /api/assets/{id} | 下线资产（decommissioned） |
| GET | /api/assets/{id}/history | 端口变化历史 |
| PATCH | /api/assets/bulk | 批量更新（owner/status/...） |

---

## 扫描批次

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/scans/upload | 上传 nmap XML |
| GET | /api/scans | 批次列表 |
| GET | /api/scans/{id} | 批次详情 |
| GET | /api/scans/{id}/diff | 差异详情（新发现/变更/消失） |
| POST | /api/scans/{id}/confirm | 确认导入 |
| DELETE | /api/scans/{id} | 拒绝批次 |

---

## 拓扑图

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/topology/generate | LLM 生成拓扑图初稿 |
| GET | /api/topology | 当前拓扑图 |
| GET | /api/topology/versions | 历史版本列表 |
| POST | /api/topology | 保存新版本 |
| POST | /api/topology/{id}/rollback | 回滚到某版本 |

---

## 安全报表

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/reports/port-exposure | 端口暴露面分析 |
| GET | /api/reports/dangerous-ports | 危险端口告警 |
| GET | /api/reports/dangerous-ports/export | 导出危险端口 CSV |
| GET | /api/reports/shadow-assets | 影子资产 |
| GET | /api/reports/shadow-assets/export | 导出影子资产 CSV |
| GET | /api/reports/asset-changes | 资产变化时间线 |

---

## 审计日志

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/audit/logs | 操作日志（super_admin + auditor） |
| GET | /api/audit/llm-logs | LLM 调用日志 |
| POST | /api/audit/export | 导出审计报告 CSV（仅 auditor） |

---

## 系统配置

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/config | 读取所有配置 |
| PATCH | /api/config | 修改配置（super_admin） |

---

## 健康检查

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/health | 健康检查（含数据库连通性） |

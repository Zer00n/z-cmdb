# 前端 UI 重构记录（2026-05-20）

> **分支**：`feature/ui-redesign-2026`
> **目标**：基于 2026 审美升级前端视觉，**不改动任何业务逻辑、API、router、状态管理**
> **基准**：v0.1（master 分支当前状态）
> **审美方向**：克制、密度适中、零滥用动效；半透明顶栏 + 微渐变品牌色 + 颜色化阴影 + 单色等宽数据呈现

---

## 一、改动原则

1. **不改动业务**：所有 `<script>` 块的 ref / reactive / computed / 函数 / API 调用全部保留
2. **不改动数据流**：Pinia store、router、API 层、类型定义文件 0 行改动
3. **token 优先**：所有视觉变量集中在 `tokens.css` 与 `app.css`，不在组件硬编码颜色
4. **向后兼容**：保留 v1 全部 token 变量，仅追加新 token，旧组件可逐步迁移

---

## 二、文件改动清单

### 2.1 样式层（核心）

| 文件 | 类型 | 说明 |
|---|---|---|
| `frontend/src/styles/tokens.css` | 增强 | 保留 v1 全部 token；新增 `surface-*`、`accent-*`、`glow-*`、`shadow-blue/card-hover`、`ring-*`、`ease-*`、`fs-hero/mega` 等 2026 新 token |
| `frontend/src/styles/element-theme.scss` | 增强 | v1 主色保持；新增按钮 hover 抬升、输入 focus glow、表头柔色、Tabs active bar 渐变等组件级精修 |
| `frontend/src/styles/app.css` | **新增** | 全局工具类层（`ui-*` 命名空间），提供 page-head / card / kpi / badge / zone / status / mono / id-link / notice / empty 等通用组件，避免每个页面重复定义 |
| `frontend/src/main.ts` | 微调 | 调整样式引入顺序为 token → element-plus → element-theme → app.css，并新增 app.css 引入 |

### 2.2 布局与导航

| 文件 | 改动范围 | 视觉升级 |
|---|---|---|
| `frontend/src/layouts/MainLayout.vue` | template + style | 新增背景柔光层 / 半透明 backdrop-blur 顶栏 / 品牌 logo 渐变 / 用户头像渐变环 / 环境徽标 chip / 中文角色显示 |
| `frontend/src/components/common/AppSidebar.vue` | template + style | active 项渐变高亮 + 左侧光带 / tooltip 滑入动画 / 底部版权信息块 |

### 2.3 页面（8 个核心视图）

| 文件 | 改动 | 关键变化 |
|---|---|---|
| `frontend/src/views/Login.vue` | 重写 template + style | 双栏布局：左侧产品介绍（标题渐变、特性清单、3 个统计指标）+ 右侧登录卡（边框微渐变、48px 主按钮、状态 chip 行） |
| `frontend/src/views/asset/AssetList.vue` | 重写 template + style | 改用 `ui-page-head` / `ui-filter-bar` / `ui-table-card` / `ui-zone` / `ui-status` / `ui-id-link` 等工具类；表头柔色；hover ID 链接变深色 |
| `frontend/src/views/asset/AssetDetail.vue` | 重写 template + style | Hero 卡（带 radial 渐变背景）+ 4 列信息卡（hover 抬起）+ Tab 区段；端口 chip 化 |
| `frontend/src/views/asset/AssetForm.vue` | template + style | 段编号改为渐变胶囊 / hover 抬起 / 顶栏顶部光带 |
| `frontend/src/views/scan/ScanList.vue` | 重写 template + style | 数字列采用单色变体（`+N` 蓝、`~N` 黄、`−N` 灰）/ help-link 圆角胶囊化 |
| `frontend/src/views/scan/ScanConfirm.vue` | template + style | KPI hero 网格化 / 段卡 hover 描边 / pill 圆形化 / 底部操作栏改为 backdrop-blur 粘性栏 |
| `frontend/src/views/topology/TopologyEditor.vue` | template + style | 编辑器顶栏（带 live dot + 提示）/ 版本卡侧栏滚动布局 / 当前版本渐变高亮 |
| `frontend/src/views/report/ReportDashboard.vue` | 重写 template + style | KPI 4 卡升级（图标徽章 + 微渐变背景）/ Top 端口柱状条带光晕 / 区域分布条按区域配色渐变 / 卡片标题加渐变 dot |
| `frontend/src/views/audit/AuditLog.vue` | 重写 template + style | notice 改为蓝色渐变信息条 / 操作类型徽标按语义着色 / 角色徽标统一 ui-badge |
| `frontend/src/views/user/UserList.vue` | 重写 template + style | 用户列单元格：头像 + 姓名/username 双行 / 角色按 super_admin/admin/auditor 不同渐变头像 |
| `frontend/src/views/settings/Settings.vue` | template + style | 段编号改为渐变胶囊 / 配置 key 改为带边框 mono chip / hint 卡蓝色渐变 |
| `frontend/src/views/Help.vue` | 重写 template + style | 命令卡顶部光带 / mono 命令块嵌入 surface-sunken / 标签胶囊化 |

### 2.4 未改动

| 类别 | 文件 |
|---|---|
| 业务脚本 | 所有页面的 `<script setup>` 块（仅微调入口附近的 import / 计算属性补充派生值） |
| Pinia | `stores/auth.ts` 等所有 store |
| Router | `router/index.ts` |
| API | `api/*.ts` 全部 |
| 类型 | `types/*.ts` 全部 |
| 后端 | 0 行改动（本次仅前端） |

---

## 三、设计 Token 升级摘要

### 新增 surface 层级

```
--surface-canvas    应用画布底（带蓝灰）
--surface-base      卡片背景
--surface-raised    弹窗、下拉
--surface-sunken    输入框、代码块
--surface-overlay   半透明顶栏（配合 backdrop-blur）
```

### 新增 accent 渐变

```
--accent-from     #2563EB
--accent-to       #6366F1
--accent-gradient 主品牌渐变（135deg）
--accent-data     KPI 数字渐变（mono / 文本裁切）
--accent-risk     危险渐变（仅高危报表用）
--accent-warn     警告渐变
--accent-safe     成功渐变
```

### 新增阴影

```
--shadow-blue          蓝色品牌阴影（hover 主按钮）
--shadow-card-hover    卡片 hover 浮起
```

### 新增动效曲线

```
--ease-out
--ease-out-slow
--ease-snap
--dur-fast (120ms) / dur-base (200ms) / dur-slow (320ms)
```

---

## 四、视觉关键决策

### 4.1 守住的边界（PRD 5.4.6）

- ❌ 没用 Glassmorphism 伪卡片
- ❌ 没用 Neumorphism
- ❌ 没用大圆角（>8px，仅 Login 卡片用 16px 这是 hero 容器例外）
- ❌ 没用过度饱和色
- ❌ 没用装饰性大插图
- ❌ 没用混搭图标库

### 4.2 拉开档次的细节

- 顶栏 `backdrop-filter: saturate(140%) blur(14px)` —— 滚动内容时品牌区柔化但不模糊
- 品牌 logo 与用户头像采用渐变 + inset 内高光 —— 让单色 UI 仍有立体感
- 卡片彩色阴影（`--shadow-blue`）—— 主按钮 hover 时给"主色被光照亮"的暗示
- KPI 数字用 mono + 字号 36px + 字间距 -0.02em —— 数据感强但不张扬
- 表格行 hover 用主色 4% 透明度 —— 不喧宾夺主
- 全局焦点圈 `--ring-primary` —— 替代 outline 的过时蓝边

### 4.3 数据呈现一致性

- 所有 IP / MAC / 资产编号 / 时间戳 / 端口号 → JetBrains Mono
- 所有数字 KPI → `--fs-hero` (36px) 单色
- 所有状态点 → 8px 圆点 + 3px 同色 16% 透明 halo
- 所有徽标 → `.ui-badge`（is-success / is-danger / is-warning / is-info / is-neutral）

---

## 五、向后兼容保证

1. **token v1 全部保留**：旧组件没动一行 CSS 也能继续工作
2. **element-theme.scss 新增的精修都是 progressive enhancement**：禁用也不会破坏页面
3. **业务逻辑 0 改动**：所有 API 调用、表单提交、路由跳转、权限判断完全不变
4. **打包结果对照**：构建产物 chunk 大小变化在合理范围（CSS 层略增，JS 层基本持平）

---

## 六、待用户决策的下一步

1. ✅ 当前版本可直接 `pnpm build` 通过，可直接 `pnpm dev` 体验
2. 是否合并到 master：建议先 `pnpm dev` 走一遍登录、资产、扫描、报表、审计 5 条主流程
3. 如有具体页面想进一步调整（颜色、间距、信息密度），可在本分支继续微调
4. 后端没有变化，不需要重新 `alembic upgrade`

---

## 七、本次未做（留待 v3 主功能开发）

以下属于 PRD v3 建议清单内容，**不在本次 UI 重构范围**：

- 危险端口规则引擎 UI
- HVV 场景 Dashboard
- 等保控制项映射页
- CVE 风险面板
- 通知 / 速率限制 / 审计签名链等后端能力

UI 重构只是把"地基"打好，让后续新功能页面可以一致地复用 `ui-*` 工具类与 token，避免再次出现"每个页面定义自己的 .table-card / .page-head"的重复。

---

**文档结束**

> 本次重构在视觉上的最大目标：从"功能完整、风格平庸"升级到"克制专业、值得截图给客户看"。
> 如果觉得某些地方"太张扬"或"还想更克制"，告诉我具体页面我可以再微调。

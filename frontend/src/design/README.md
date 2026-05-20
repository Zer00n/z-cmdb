# \# Design Templates - 对应关系

# 

# 每份 HTML 是从 Claude Design 输出的视觉模板，Vue 实现时作为 Claude Code 的上下文附带。

# 

# \## 当前进度

# 

# \- ✅ 已完成：6 个页面（2026-05-18 调用）

# \- ⏳ 待补充：4 个页面（计划 2026-05-19 Design 额度恢复后调用）

# 

# \## 文件对应关系

# 

# | 文件 | 调用时间 | 对应 Vue 实现 | 复用范围 |

# |------|---------|--------------|---------|

# | 01-design-system.html | 2026-05-18 | （仅作可视化参考，不直接实现） | 配合 tokens.css 使用，开发时对照设计 token |

# | 02-login.html | 2026-05-18 | src/views/Login.vue | 仅登录页 |

# | 03-layout.html | 2026-05-18 | src/layouts/MainLayout.vue + src/components/common/AppSidebar.vue + src/components/common/AppHeader.vue | 系统主框架,所有登录后页面共用外壳 |

# | 04-asset-list.html | 2026-05-18 | src/views/asset/AssetList.vue | \*\*列表模板\*\*,可派生:批次列表、用户列表、审计日志列表、影子资产清单、危险端口清单、批次历史 |

# | 05-asset-detail.html | 2026-05-18 | src/views/asset/AssetDetail.vue | \*\*详情模板\*\*,可派生:批次详情、拓扑版本详情、用户详情 |

# | 06-asset-form.html | 2026-05-18 | src/views/asset/AssetForm.vue | \*\*表单模板\*\*,可派生:用户新增/编辑、系统配置 |

# | 07-scan-confirm.html | 待补充 | src/views/scan/ScanConfirm.vue | 仅本页(三栏对比,最复杂,无复用) |

# | 08-topology-editor.html | 待补充 | src/views/topology/TopologyEditor.vue | 仅本页(drawio 嵌入) |

# | 09-report-dashboard.html | 待补充 | src/views/report/ReportDashboard.vue | 报表入口,子报表页复用列表模板 |

# | 10-audit-log.html | 待补充 | src/views/audit/AuditLog.vue | 审计日志,LLM 调用日志复用同样结构 |

# 

# \## 辅助文件

# 

# | 文件 | 用途 | 是否项目正式资产 |

# |------|------|----------------|

# | shell.css | Design 输出的辅助样式,用于让 HTML 独立显示 | ❌ 仅参考,Vue 实现时不引用 |

# 

# \## 设计 token 来源

# 

# `01-design-system.html` 中的所有 CSS 变量已提取到 `src/styles/tokens.css`(项目唯一 token 来源)。

# 

# \*\*禁止行为\*\*:

# \- 在 Vue 组件中硬编码颜色、间距、字号

# \- 创建副本 token 文件

# \- 在新页面里新增设计 token(必须先在 tokens.css 中定义)

# 

# \## 复用规则(重要)

# 

# 按 Playbook v1 第 2.3 节:

# 

# \- 列表类页面 → 复用 04-asset-list.html 的布局,仅替换表格列和筛选条件

# \- 详情类页面 → 复用 05-asset-detail.html 的 Tab 布局

# \- 表单类页面 → 复用 06-asset-form.html 的分段布局

# \- 新增页面时\*\*不再调用 Claude Design\*\*,从已有模板派生

# 

# \## 派生页面与模板的对应

# 

# | 派生页面 | 派生自 | 备注 |

# |---------|-------|------|

# | src/views/scan/ScanBatchList.vue | 04-asset-list.html | 仅替换列定义和筛选 |

# | src/views/user/UserList.vue | 04-asset-list.html | 同上 |

# | src/views/user/UserForm.vue | 06-asset-form.html | 字段不同 |

# | src/views/config/SystemConfig.vue | 06-asset-form.html | 配置项以表单形式呈现 |

# | src/views/report/PortExposure.vue | 04-asset-list.html | 列表展示 + 顶部统计卡 |

# | src/views/report/DangerousPorts.vue | 04-asset-list.html | 同上 |

# | src/views/report/ShadowAssets.vue | 04-asset-list.html | 同上 |

# | src/views/audit/LlmCallLog.vue | 10-audit-log.html | 复用审计日志结构 |

# 

# \## 修订历史

# 

# \- 2026-05-18:初始版本,完成 01-06 共 6 个模板

# \- 待:2026-05-19,补充 07-10 共 4 个模板后更新本文档


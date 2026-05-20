# nmap 扫描命令参考

> 本文档提供 CMDB Lite 推荐的 nmap 扫描命令模板。Web 界面"帮助"页面提供一键复制。

## 标准扫描（推荐）

适用于日常资产盘点，覆盖 1-10000 端口，耗时约 10-30 分钟（/24 网段）。

```bash
nmap -sS -sV -O --osscan-guess -p 1-10000 \
     --version-intensity 5 -T4 \
     -oX scan_$(date +%Y%m%d_%H%M).xml \
     <目标网段，如 192.168.1.0/24>
```

## 快速扫描

适用于快速确认主机存活和常见服务，仅扫描 Top 1000 端口，耗时约 3-10 分钟。

```bash
nmap -sS -sV -O --osscan-guess --top-ports 1000 \
     -T4 -oX scan_quick_$(date +%Y%m%d_%H%M).xml \
     <目标网段>
```

## 深度扫描

适用于安全审计、HVV 前的全面盘点，扫描全部 65535 端口，耗时较长（30 分钟 - 数小时）。

```bash
nmap -sS -sV -O --osscan-guess -p- \
     --version-intensity 7 -T3 \
     -oX scan_deep_$(date +%Y%m%d_%H%M).xml \
     <目标网段>
```

## 强制要求

- 输出格式必须是 `-oX`（XML），系统只解析 XML 格式
- 文件名建议带日期，系统也会自己记录上传时间
- 上传文件大小上限 50 MB（单次），可在系统配置中调整

## Windows 环境

Windows 下 `$(date ...)` 不可用，请手动命名文件：

```cmd
nmap -sS -sV -O --osscan-guess -p 1-10000 --version-intensity 5 -T4 -oX scan_20260520.xml 192.168.1.0/24
```

## 常见问题

- **需要 root/管理员权限**：`-sS`（SYN 扫描）和 `-O`（OS 检测）需要 root 权限
- **防火墙干扰**：如果大量端口显示 filtered，考虑降低扫描速度（`-T3` 或 `-T2`）
- **大网段拆分**：建议按 /24 拆分扫描，避免单次文件过大

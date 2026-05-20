"""
LLM 数据脱敏管道
资产数据 → 脱敏 → 投喂 LLM → 反脱敏 → 真实数据
"""
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class SanitizeMapping:
    """脱敏映射表，用于反脱敏"""
    ip_map: dict[str, str] = field(default_factory=dict)       # HOST_X_NNN → real_ip
    hostname_map: dict[str, str] = field(default_factory=dict) # HOST_X_NNN → real_hostname
    business_map: dict[str, str] = field(default_factory=dict) # GROUP_X → real_business


def sanitize_assets(assets: list[dict]) -> tuple[list[dict], SanitizeMapping]:
    """
    对资产数据进行脱敏，返回 (脱敏后数据, 映射表)。
    脱敏规则（PRD 4.5.3）：
    - IP → 占位符 HOST_X_NNN
    - 主机名 → 占位符
    - OS 版本号 → 去除（只保留大类）
    - 端口 → 仅保留服务大类
    - 业务系统名 → 占位符 GROUP_X
    """
    mapping = SanitizeMapping()
    sanitized = []

    # 业务系统去重映射
    biz_counter = 0
    biz_seen: dict[str, str] = {}

    for idx, asset in enumerate(assets):
        host_id = f"HOST_A_{idx + 1:03d}"

        # IP 映射
        real_ip = asset.get("ip_address", "")
        mapping.ip_map[host_id] = real_ip

        # 主机名映射
        real_hostname = asset.get("hostname", "")
        mapping.hostname_map[host_id] = real_hostname

        # 业务系统映射
        real_biz = asset.get("business_system", "")
        if real_biz not in biz_seen:
            biz_counter += 1
            biz_seen[real_biz] = f"GROUP_{chr(64 + biz_counter)}"
        group_id = biz_seen[real_biz]
        mapping.business_map[group_id] = real_biz

        # OS 大类
        os_info = asset.get("os_info", "") or ""
        os_category = "unknown"
        if "linux" in os_info.lower() or "ubuntu" in os_info.lower() or "centos" in os_info.lower():
            os_category = "Linux"
        elif "windows" in os_info.lower():
            os_category = "Windows"

        # 端口 → 服务大类
        ports = asset.get("ports", [])
        service_hints = list(set(
            p.get("service_name", "") for p in ports
            if p.get("service_name")
        ))

        sanitized_item = {
            "id": host_id,
            "type": asset.get("asset_type", "other"),
            "zone": asset.get("network_zone", "other"),
            "os_category": os_category,
            "service_hint": service_hints[:5],  # 最多 5 个
            "group": group_id,
        }
        sanitized.append(sanitized_item)

    logger.info(
        "assets sanitized for LLM",
        extra={"count": len(sanitized), "groups": len(biz_seen)},
    )
    return sanitized, mapping


def desanitize_topology(
    topology_data: dict,
    mapping: SanitizeMapping,
) -> dict:
    """
    反脱敏：将 LLM 返回的拓扑数据中的占位符替换回真实信息。
    """
    import json
    text = json.dumps(topology_data, ensure_ascii=False)

    # 替换 HOST_X_NNN → 真实 IP
    for placeholder, real_ip in mapping.ip_map.items():
        text = text.replace(placeholder, real_ip)

    # 替换 GROUP_X → 真实业务系统名
    for placeholder, real_biz in mapping.business_map.items():
        text = text.replace(placeholder, real_biz)

    return json.loads(text)

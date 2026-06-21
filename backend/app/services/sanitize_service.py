"""
LLM data sanitization pipeline
Asset data -> sanitize -> feed to LLM -> desanitize -> real data
"""
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class SanitizeMapping:
    """Sanitization mapping table, used for desanitization"""
    ip_map: dict[str, str] = field(default_factory=dict)       # HOST_X_NNN → real_ip
    hostname_map: dict[str, str] = field(default_factory=dict) # HOST_X_NNN → real_hostname
    business_map: dict[str, str] = field(default_factory=dict) # GROUP_X → real_business


def sanitize_assets(assets: list[dict]) -> tuple[list[dict], SanitizeMapping]:
    """
    Sanitize asset data and return (sanitized data, mapping table).
    Sanitization rules (PRD 4.5.3):
    - IP -> placeholder HOST_X_NNN
    - Hostname -> placeholder
    - OS version -> removed (keep category only)
    - Ports -> keep service category only
    - Business system name -> placeholder GROUP_X
    """
    mapping = SanitizeMapping()
    sanitized = []

    # Business system dedup mapping
    biz_counter = 0
    biz_seen: dict[str, str] = {}

    for idx, asset in enumerate(assets):
        host_id = f"HOST_A_{idx + 1:03d}"

        # IP mapping
        real_ip = asset.get("ip_address", "")
        mapping.ip_map[host_id] = real_ip

        # Hostname mapping
        real_hostname = asset.get("hostname", "")
        mapping.hostname_map[host_id] = real_hostname

        # Business system mapping
        real_biz = asset.get("business_system", "")
        if real_biz not in biz_seen:
            biz_counter += 1
            biz_seen[real_biz] = f"GROUP_{chr(64 + biz_counter)}"
        group_id = biz_seen[real_biz]
        mapping.business_map[group_id] = real_biz

        # OS category
        os_info = asset.get("os_info", "") or ""
        os_category = "unknown"
        if "linux" in os_info.lower() or "ubuntu" in os_info.lower() or "centos" in os_info.lower():
            os_category = "Linux"
        elif "windows" in os_info.lower():
            os_category = "Windows"

        # Ports -> service category
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
            "service_hint": service_hints[:5],  # At most 5
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
    Desanitize: replace placeholders in LLM-returned topology data with real information.
    """
    import json
    text = json.dumps(topology_data, ensure_ascii=False)

    # Replace HOST_X_NNN -> real IP
    for placeholder, real_ip in mapping.ip_map.items():
        text = text.replace(placeholder, real_ip)

    # Replace GROUP_X -> real business system name
    for placeholder, real_biz in mapping.business_map.items():
        text = text.replace(placeholder, real_biz)

    return json.loads(text)

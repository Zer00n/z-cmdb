"""
拓扑图业务逻辑
生成、保存、版本管理
"""
import json
import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import TopologyNotFoundError, ValidationError
from app.models.user import User
from app.services import llm_service, sanitize_service

logger = logging.getLogger(__name__)

# 拓扑图版本存储在 topologies 表（v0.1 已在 PRD 中定义）
# 这里先用简化方案：存在 audit_log 中或单独表
# 由于 topologies 表模型还没创建，先创建它


def generate_topology(
    db: Session,
    user: User,
    provider_name: str,
    api_key: str,
    base_url: str,
    model: str,
) -> dict:
    """
    生成拓扑图初稿：
    1. 获取所有在线资产
    2. 脱敏
    3. 调用 LLM（按重要性路由 + 全局禁用云端检查）
    4. 反脱敏
    5. 返回拓扑数据
    """
    from app.repositories import asset_repo
    from app.schemas.asset import AssetQueryParams
    from app.services.config_service import get_config_value

    # 检查全局禁用云端 LLM 开关
    cloud_enabled = get_config_value(db, "llm_cloud_enabled", "true").lower() == "true"
    route_core_to_local = get_config_value(db, "llm_route_core_to_local", "true").lower() == "true"

    # 获取所有在线资产（含端口）
    params = AssetQueryParams(page=1, page_size=10000, status="online")
    assets, _ = asset_repo.list_assets(db, params)

    if not assets:
        raise ValidationError("没有在线资产，无法生成拓扑图")

    # 判断是否有核心资产
    has_core = any(a.importance == "core" for a in assets)

    # 路由决策
    actual_provider = provider_name
    actual_api_key = api_key
    actual_base_url = base_url
    actual_model = model

    def _ollama_available() -> bool:
        """检测本地 Ollama 是否在运行"""
        import httpx
        try:
            resp = httpx.get("http://localhost:11434/api/tags", timeout=3)
            return resp.status_code == 200
        except Exception:
            return False

    # Ollama 使用独立的模型配置，不复用主 llm_model
    ollama_model = get_config_value(db, "llm_ollama_model", "qwen2.5")

    should_route_local = False
    route_reason = ""

    if not cloud_enabled:
        should_route_local = True
        route_reason = "全局禁用云端 LLM"
    elif has_core and route_core_to_local and actual_provider != "ollama":
        should_route_local = True
        route_reason = "存在核心资产且配置了路由到本地 LLM"

    if should_route_local:
        if _ollama_available():
            actual_provider = "ollama"
            actual_api_key = ""
            actual_base_url = "http://localhost:11434"
            actual_model = ollama_model
            logger.info("routed to local ollama: %s", route_reason)
        else:
            raise ValidationError(
                f"检测到需要使用本地 LLM（{route_reason}），但本地 Ollama 服务未运行。"
                "请启动 Ollama（ollama serve），或将系统配置中的 llm_route_core_to_local 设为 false。"
            )

    # 构造资产数据（含端口），限制最多 20 个避免推理模型 token 耗尽
    asset_data = []
    for a in assets[:20]:
        ports = asset_repo.get_ports_by_asset(db, a.id)
        asset_data.append({
            "ip_address": a.ip_address,
            "hostname": a.hostname,
            "os_info": a.os_info,
            "asset_type": a.asset_type,
            "network_zone": a.network_zone,
            "business_system": a.business_system,
            "importance": a.importance,
            "ports": [
                {"port_number": p.port_number, "protocol": p.protocol, "service_name": p.service_name}
                for p in ports
            ],
        })

    # 脱敏
    sanitized, mapping = sanitize_service.sanitize_assets(asset_data)

    # 精简 system_prompt（推理模型自带推理能力，不需要冗长指令）
    system_prompt = (
        "你是网络拓扑图生成助手。根据资产 JSON 生成 drawio XML。"
        "要求：①按 zone 字段用 swimlane 分组 ②节点用 rounded 矩形 ③importance=core 加红色边框"
        "④直接输出 <mxfile>...</mxfile>，不加任何解释或 markdown 代码块。"
    )

    prompt = (
        f"资产数据（共 {len(sanitized)} 个）：\n"
        f"{json.dumps(sanitized, ensure_ascii=False, indent=2)}\n\n"
        "生成 drawio 网络拓扑图 XML。按 zone 分 swimlane，节点显示 id 和 service_hint，"
        "core 资产红色边框。直接输出完整 <mxfile>...</mxfile>。"
    )

    logger.info(
        "topology generation: calling LLM",
        extra={
            "provider": actual_provider,
            "model": actual_model,
            "base_url": actual_base_url,
            "asset_count": len(assets),
            "prompt_length": len(prompt),
            "sanitized_data": json.dumps(sanitized, ensure_ascii=False)[:500],
        },
    )

    # 调用 LLM
    response = llm_service.call_llm(
        db=db,
        provider_name=actual_provider,
        api_key=actual_api_key,
        base_url=actual_base_url,
        model=actual_model,
        prompt=prompt,
        system_prompt=system_prompt,
        user=user,
        purpose="topology_generation",
    )

    # 清洗 LLM 返回：去掉 markdown 代码块包裹
    response = response.strip()
    if response.startswith("```"):
        # 去掉首行 ```xml 或 ```
        lines = response.split("\n")
        lines = lines[1:]  # 去掉 ```xml
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]  # 去掉尾部 ```
        response = "\n".join(lines).strip()

    # 提取有效的 drawio XML（优先 <mxfile>，其次 <mxGraphModel>）
    if "<mxfile" in response and "</mxfile>" in response:
        start = response.index("<mxfile")
        end = response.index("</mxfile>") + len("</mxfile>")
        response = response[start:end]
    elif "<mxGraphModel" in response and "</mxGraphModel>" in response:
        start = response.index("<mxGraphModel")
        end = response.index("</mxGraphModel>") + len("</mxGraphModel>")
        response = response[start:end]
    else:
        # LLM 未返回有效 XML，记录原始响应并抛出友好错误
        logger.error(
            "topology LLM response is not valid drawio XML",
            extra={"response_preview": response[:300]},
        )
        raise ValidationError(
            f"LLM 未返回有效的 drawio XML（模型：{actual_model}）。"
            "请尝试更换模型，或检查 prompt 是否被截断。"
            f"模型原始回复（前200字）：{response[:200]}"
        )

    # 去掉 XML 声明（drawio embed 不需要）
    if response.startswith("<?xml"):
        newline_pos = response.index("?>") + 2
        response = response[newline_pos:].strip()

    # 反脱敏（LLM 返回的是 drawio XML，直接做文本替换）
    for placeholder, real_ip in mapping.ip_map.items():
        response = response.replace(placeholder, real_ip)
    for placeholder, real_biz in mapping.business_map.items():
        response = response.replace(placeholder, real_biz)

    return {
        "drawio_xml": response,
        "asset_count": len(assets),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

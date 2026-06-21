"""
Topology graph business logic
Generation, saving, version management
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

# Topology graph versions are stored in the topologies table (defined in PRD v0.1)
# Using a simplified approach for now: stored in audit_log or a separate table
# Since the topologies table model hasn't been created yet, creating it here


def generate_topology(
    db: Session,
    user: User,
    provider_name: str,
    api_key: str,
    base_url: str,
    model: str,
) -> dict:
    """
    Generate a topology graph draft:
    1. Fetch all online assets
    2. Sanitize
    3. Call LLM (with importance-based routing and global cloud-check disabled)
    4. Desanitize
    5. Return topology data
    """
    from app.repositories import asset_repo
    from app.schemas.asset import AssetQueryParams
    from app.services.config_service import get_config_value

    # Check global cloud LLM disable switch
    cloud_enabled = get_config_value(db, "llm_cloud_enabled", "true").lower() == "true"
    route_core_to_local = get_config_value(db, "llm_route_core_to_local", "true").lower() == "true"

    # Fetch all online assets (including ports)
    params = AssetQueryParams(page=1, page_size=10000, status="online")
    assets, _ = asset_repo.list_assets(db, params)

    if not assets:
        raise ValidationError("No online assets available, cannot generate topology")

    # Check if there are any core assets
    has_core = any(a.importance == "core" for a in assets)

    # Routing decision
    actual_provider = provider_name
    actual_api_key = api_key
    actual_base_url = base_url
    actual_model = model

    def _ollama_available() -> bool:
        """Check if local Ollama is running"""
        import httpx
        try:
            resp = httpx.get("http://localhost:11434/api/tags", timeout=3)
            return resp.status_code == 200
        except Exception:
            return False

    # Ollama uses its own model config, not shared with main llm_model
    ollama_model = get_config_value(db, "llm_ollama_model", "qwen2.5")

    should_route_local = False
    route_reason = ""

    if not cloud_enabled:
        should_route_local = True
        route_reason = "Global cloud LLM is disabled"
    elif has_core and route_core_to_local and actual_provider != "ollama":
        should_route_local = True
        route_reason = "Core assets present and local LLM routing is enabled"

    if should_route_local:
        if _ollama_available():
            actual_provider = "ollama"
            actual_api_key = ""
            actual_base_url = "http://localhost:11434"
            actual_model = ollama_model
            logger.info("routed to local ollama: %s", route_reason)
        else:
            raise ValidationError(
                f"Local LLM required ({route_reason}), but local Ollama service is not running. "
                "Please start Ollama (ollama serve), or set llm_route_core_to_local to false in system config."
            )

    # Build asset data (including ports), limit to 20 to avoid token exhaustion in reasoning models
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

    # Sanitize
    sanitized, mapping = sanitize_service.sanitize_assets(asset_data)

    # Streamlined system_prompt (reasoning models have built-in reasoning ability, no verbose instructions needed)
    system_prompt = (
        "You are a network topology graph generation assistant. Generate drawio XML from asset JSON. "
        "Requirements: 1) Group by zone field using swimlanes 2) Use rounded rectangles for nodes "
        "3) Add red border for importance=core assets "
        "4) Output <mxfile>...</mxfile> directly, no explanations or markdown code blocks."
    )

    prompt = (
        f"Asset data ({len(sanitized)} items):\n"
        f"{json.dumps(sanitized, ensure_ascii=False, indent=2)}\n\n"
        "Generate a drawio network topology XML. Group by zone using swimlanes, display id and service_hint on nodes, "
        "red border for core assets. Output the complete <mxfile>...</mxfile> directly."
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

    # Call LLM
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

    # Clean up LLM response: remove markdown code block wrappers
    response = response.strip()
    if response.startswith("```"):
        # Remove first line ```xml or ```
        lines = response.split("\n")
        lines = lines[1:]  # Remove ```xml
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]  # Remove trailing ```
        response = "\n".join(lines).strip()

    # Extract valid drawio XML (prefer <mxfile>, fall back to <mxGraphModel>)
    if "<mxfile" in response and "</mxfile>" in response:
        start = response.index("<mxfile")
        end = response.index("</mxfile>") + len("</mxfile>")
        response = response[start:end]
    elif "<mxGraphModel" in response and "</mxGraphModel>" in response:
        start = response.index("<mxGraphModel")
        end = response.index("</mxGraphModel>") + len("</mxGraphModel>")
        response = response[start:end]
    else:
        # LLM did not return valid XML, log raw response and raise a friendly error
        logger.error(
            "topology LLM response is not valid drawio XML",
            extra={"response_preview": response[:300]},
        )
        raise ValidationError(
            f"LLM did not return valid drawio XML (model: {actual_model}). "
            "Please try a different model or check if the prompt was truncated. "
            f"Raw model response (first 200 chars): {response[:200]}"
        )

    # Remove XML declaration (not needed for drawio embed)
    if response.startswith("<?xml"):
        newline_pos = response.index("?>") + 2
        response = response[newline_pos:].strip()

    # Desanitize (LLM returns drawio XML, perform text replacement directly)
    for placeholder, real_ip in mapping.ip_map.items():
        response = response.replace(placeholder, real_ip)
    for placeholder, real_biz in mapping.business_map.items():
        response = response.replace(placeholder, real_biz)

    return {
        "drawio_xml": response,
        "asset_count": len(assets),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

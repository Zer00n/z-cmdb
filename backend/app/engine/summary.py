"""
V0.6 AI project summary generator

Generates a natural language summary + risk alert from topology data.
Cached in the project table (summary_overview / summary_risk / summary_lang).
Must be clearly labeled as "AI generated draft" on the frontend.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.engine.topology import generate_topology

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT_BASE = """You are a project architecture analyst for an IT operations team.
Given the topology data of a project, provide:
1. A 2-3 sentence overview of the project architecture (what components exist, how they connect, where they run).
2. A single key risk or observation (e.g., single point of failure, high resource usage, missing redundancy).

CRITICAL CONSTRAINTS:
- Describe ONLY what exists in the provided topology data.
- Do NOT invent components, dependencies, or numbers not present in the data.
- Do NOT make recommendations — only state observations.
- Keep the overview factual and concise.
- The risk should be directly derivable from the data (e.g., "mysql has only 1 instance on 1 host" → single point of failure)."""

_LANG_INSTRUCTIONS = {
    "zh": "\n\nIMPORTANT: Respond entirely in Chinese (简体中文). The output will be displayed in a Chinese-language UI.",
    "en": "\n\nIMPORTANT: Respond entirely in English.",
}

SUMMARY_TEMPLATE = """## Topology Data

Project: {project_id}
Hosts: {hosts}
Components: {components}
Dependencies: {dependencies}

Please provide a project overview and identify the key risk."""


def _format_topology_for_prompt(topo: dict[str, Any]) -> str:
    """Format topology JSON into a readable prompt section."""
    hosts_desc = []
    for h in topo.get("hosts", []):
        shared = " (shared)" if h.get("shared") else ""
        hosts_desc.append(f"  - {h['id']}: ¥{h['monthly_cost']}/month{shared}")

    components_desc = []
    for u in topo.get("units", []):
        runtime = u.get("runtime", {})
        instances = runtime.get("instances", "?") if runtime else "?"
        host = u.get("host_id", "unknown")
        components_desc.append(
            f"  - {u['name']} ({u['type']}): {instances} instances on {host}, "
            f"owner={u.get('owner', 'N/A')}, env={u.get('environment', 'N/A')}"
        )

    deps_desc = []
    for d in topo.get("dependencies", []):
        cycle_warn = " [CYCLE]" if d.get("in_cycle") else ""
        deps_desc.append(f"  - {d['source']} → {d['target']} ({d['type']}){cycle_warn}")

    return SUMMARY_TEMPLATE.format(
        project_id=topo.get("project_id", "unknown"),
        hosts="\n".join(hosts_desc) or "  (none)",
        components="\n".join(components_desc) or "  (none)",
        dependencies="\n".join(deps_desc) or "  (none)",
    )


def generate_project_summary(
    db: Session,
    project_id: str,
    lang: str = "zh",
) -> dict[str, Any]:
    """
    Generate AI project summary from topology data.

    Args:
        lang: Output language — "zh" for Chinese, "en" for English.

    Returns:
        {
            "overview": str,
            "risk": str,
            "draft": True,
            "lang": str,
        }

    Raises:
        LLMCallError if LLM is unavailable.
    """
    # Get topology data
    topo = generate_topology(db, project_id)

    # Format for LLM
    user_prompt = _format_topology_for_prompt(topo)

    # Build system prompt with language instruction
    system_prompt = _SYSTEM_PROMPT_BASE + _LANG_INSTRUCTIONS.get(lang, _LANG_INSTRUCTIONS["zh"])

    # Try to call LLM
    try:
        # Read LLM config from SystemConfig table
        from app.models.config import SystemConfig
        from app.core.encryption import decrypt_value

        def _cfg(key: str) -> str:
            row = db.get(SystemConfig, key)
            val = row.value if row else ""
            if key == "llm_api_key" and val:
                val = decrypt_value(val)
            return val

        provider_name = _cfg("llm_provider")
        if not provider_name:
            raise RuntimeError("No LLM provider configured")

        from app.services.llm_service import get_provider
        provider = get_provider(
            provider_name=provider_name,
            api_key=_cfg("llm_api_key"),
            base_url=_cfg("llm_base_url"),
            model=_cfg("llm_model"),
        )

        # call() signature: call(prompt, system_prompt) -> str
        text = provider.call(prompt=user_prompt, system_prompt=system_prompt)

        # Parse response: try to extract overview and risk
        overview, risk = _parse_response(text)

        return {
            "overview": overview,
            "risk": risk,
            "draft": True,
            "lang": lang,
        }

    except Exception as e:
        logger.warning("AI summary generation failed: %s", e)
        raise


def _parse_response(text: str) -> tuple[str, str]:
    """Parse LLM response into overview and risk sections."""
    # Simple heuristic: first paragraph is overview, rest is risk
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

    if len(paragraphs) >= 2:
        overview = paragraphs[0]
        risk = " ".join(paragraphs[1:])
    elif len(paragraphs) == 1:
        overview = paragraphs[0]
        risk = ""
    else:
        overview = text.strip()
        risk = ""

    return overview, risk

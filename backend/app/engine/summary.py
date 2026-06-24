"""
V0.6 AI project summary generator

Generates a natural language summary + risk alert from topology data.
Result is ephemeral — never stored in the database.
Must be clearly labeled as "AI generated draft" on the frontend.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy.orm import Session

from app.engine.topology import generate_topology

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a project architecture analyst for an IT operations team.
Given the topology data of a project, provide:
1. A 2-3 sentence overview of the project architecture (what components exist, how they connect, where they run).
2. A single key risk or observation (e.g., single point of failure, high resource usage, missing redundancy).

CRITICAL CONSTRAINTS:
- Describe ONLY what exists in the provided topology data.
- Do NOT invent components, dependencies, or numbers not present in the data.
- Do NOT make recommendations — only state observations.
- Keep the overview factual and concise.
- The risk should be directly derivable from the data (e.g., "mysql has only 1 instance on 1 host" → single point of failure).
"""

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


def generate_project_summary(db: Session, project_id: str) -> dict[str, Any]:
    """
    Generate AI project summary from topology data.

    Returns:
        {
            "overview": str,       # 2-3 sentence architecture overview
            "risk": str,           # Key risk or observation
            "draft": True,         # Always marked as draft
            "disclaimer": str,     # Standard disclaimer text
        }

    Raises:
        LLMCallError if LLM is unavailable.
    """
    # Get topology data
    topo = generate_topology(db, project_id)

    # Format for LLM
    user_prompt = _format_topology_for_prompt(topo)

    # Try to call LLM
    try:
        from app.services.llm_service import get_provider
        provider = get_provider()
        if not provider:
            raise RuntimeError("No LLM provider configured")

        response = provider.chat(
            system=SYSTEM_PROMPT,
            user=user_prompt,
            temperature=0.3,
            max_tokens=500,
        )

        # Parse response: try to extract overview and risk
        text = response.get("content", "")
        overview, risk = _parse_response(text)

        return {
            "overview": overview,
            "risk": risk,
            "draft": True,
            "disclaimer": "AI generated draft. For reference only. Not guaranteed accurate. Please refer to the architecture topology data.",
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

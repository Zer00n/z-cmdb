"""
LLM 抽象层
支持多 provider：OpenAI / Claude / DeepSeek / 智谱 / Ollama
"""
import json
import logging
import time
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.exceptions import LLMCallError
from app.models.user import User

logger = logging.getLogger(__name__)


class LLMProvider:
    """LLM 提供方基类"""

    def __init__(self, api_key: str = "", base_url: str = "", model: str = ""):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model

    def call(self, prompt: str, system_prompt: str = "") -> str:
        """调用 LLM，返回文本响应"""
        raise NotImplementedError


class OpenAIProvider(LLMProvider):
    """OpenAI / DeepSeek / 智谱（兼容 OpenAI API 格式）"""

    def call(self, prompt: str, system_prompt: str = "") -> str:
        try:
            import httpx
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            body = {"model": self.model, "messages": messages, "temperature": 0.3}
            url = f"{self.base_url.rstrip('/')}/chat/completions"

            resp = httpx.post(url, json=body, headers=headers, timeout=300)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except Exception as exc:
            raise LLMCallError(f"OpenAI API 调用失败: {exc}") from exc


class ClaudeProvider(LLMProvider):
    """Anthropic Claude"""

    def call(self, prompt: str, system_prompt: str = "") -> str:
        try:
            import httpx
            headers = {
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            }
            body = {
                "model": self.model or "claude-sonnet-4-20250514",
                "max_tokens": 4096,
                "messages": [{"role": "user", "content": prompt}],
            }
            if system_prompt:
                body["system"] = system_prompt

            url = self.base_url or "https://api.anthropic.com/v1/messages"
            resp = httpx.post(url, json=body, headers=headers, timeout=120)
            resp.raise_for_status()
            data = resp.json()
            return data["content"][0]["text"]
        except Exception as exc:
            raise LLMCallError(f"Claude API 调用失败: {exc}") from exc


class OllamaProvider(LLMProvider):
    """本地 Ollama"""

    def call(self, prompt: str, system_prompt: str = "") -> str:
        try:
            import httpx
            url = f"{self.base_url or 'http://localhost:11434'}/api/generate"
            body = {
                "model": self.model or "qwen2.5",
                "prompt": prompt,
                "system": system_prompt,
                "stream": False,
            }
            resp = httpx.post(url, json=body, timeout=300)
            resp.raise_for_status()
            data = resp.json()
            return data.get("response", "")
        except Exception as exc:
            raise LLMCallError(f"Ollama 调用失败: {exc}") from exc


def get_provider(provider_name: str, api_key: str, base_url: str, model: str) -> LLMProvider:
    """根据配置获取 LLM 提供方实例"""
    providers = {
        "deepseek": OpenAIProvider,
        "openrouter": OpenAIProvider,
        "ollama": OllamaProvider,
    }
    cls = providers.get(provider_name.lower())
    if cls is None:
        raise LLMCallError(f"不支持的 LLM 提供方: {provider_name}")
    return cls(api_key=api_key, base_url=base_url, model=model)


def call_llm(
    db: Session,
    provider_name: str,
    api_key: str,
    base_url: str,
    model: str,
    prompt: str,
    system_prompt: str = "",
    user: User | None = None,
    purpose: str = "topology_generation",
) -> str:
    """
    统一 LLM 调用入口，自动记录 llm_call_logs。
    """
    from app.models.audit import AuditLog  # 避免循环导入

    provider = get_provider(provider_name, api_key, base_url, model)

    logger.info(
        "LLM call starting",
        extra={
            "provider": provider_name,
            "model": model,
            "base_url": base_url,
            "prompt_length": len(prompt),
            "has_api_key": bool(api_key),
        },
    )

    start_time = time.time()
    success = False
    response_text = ""

    try:
        response_text = provider.call(prompt, system_prompt)
        success = True
        return response_text
    except LLMCallError:
        raise
    except Exception as exc:
        raise LLMCallError(f"LLM 调用异常: {exc}") from exc
    finally:
        elapsed_ms = int((time.time() - start_time) * 1000)
        # 记录到独立 llm_call_logs 表
        from app.models.llm_log import LlmCallLog
        llm_log = LlmCallLog(
            timestamp=datetime.now(timezone.utc),
            user_id=user.id if user else None,
            provider=provider_name,
            model=model,
            purpose=purpose,
            sanitized_request=prompt[:500] if prompt else None,
            response_summary=response_text[:200] if response_text else None,
            elapsed_ms=elapsed_ms,
            success=success,
        )
        db.add(llm_log)
        # 同时记录到 audit_logs（兼容）
        from app.services.audit_service import log_action
        log_action(
            db,
            action_type="LLM_CALL",
            user=user,
            target_type="topology",
            details={
                "provider": provider_name,
                "model": model,
                "purpose": purpose,
                "elapsed_ms": elapsed_ms,
                "success": success,
                "prompt_length": len(prompt),
                "response_length": len(response_text),
            },
        )
        db.flush()

"""
LLM base_url 出站安全校验（v0.6.6 安全修复，安全审计 V4）

防止通过未校验的 llm_base_url 实现 SSRF 与存储凭据外发：
  - 必须是带主机名的 http(s) URL，且不得内嵌用户名/口令；
  - 主机解析后的 IP 不得是回环地址；
  - 默认拒绝私网 / 链路本地 / 组播 / 保留 / 未指定地址；
  - 主机运维可显式设置环境变量 LLM_ALLOW_PRIVATE_BASE_URL=true 放行内网
    自建 LLM 主机（回环仍拒绝）。

在 PATCH /api/config 写入时校验，并在 llm_service 实际发起请求前再次校验
（纵深防御）。服务内部硬编码的本地 Ollama 路由通过 trusted_base_url 豁免。
"""
import ipaddress
import os
import socket
from urllib.parse import urlparse

from app.core.exceptions import ValidationError


def private_base_url_allowed() -> bool:
    return os.environ.get("LLM_ALLOW_PRIVATE_BASE_URL", "false").lower() in (
        "1",
        "true",
        "yes",
    )


def assert_external_url(value: str) -> None:
    """校验 LLM base URL；空值（未配置）放行。不合法时抛 ValidationError。"""
    if not value:
        return

    parsed = urlparse(value)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ValidationError("llm_base_url must be an http(s) URL with a hostname")
    if parsed.username or parsed.password:
        raise ValidationError("llm_base_url must not contain credentials")

    try:
        infos = socket.getaddrinfo(
            parsed.hostname, parsed.port or 443, proto=socket.IPPROTO_TCP
        )
    except socket.gaierror as exc:
        raise ValidationError(
            f"llm_base_url host does not resolve: {parsed.hostname}"
        ) from exc

    allow_private = private_base_url_allowed()
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        # 回环一律拒绝（即使显式允许内网）
        if ip.is_loopback:
            raise ValidationError("llm_base_url must not target loopback addresses")
        if not allow_private and (
            ip.is_private
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        ):
            raise ValidationError(
                "llm_base_url must not target private/link-local/reserved addresses; "
                "set LLM_ALLOW_PRIVATE_BASE_URL=true only for approved internal LLM hosts"
            )

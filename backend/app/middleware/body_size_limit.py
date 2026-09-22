"""
ASGI 请求体大小限制中间件（v0.6.6 安全修复）

在 multipart 解析之前执行上限：
  - Content-Length 超限时立即返回 413；
  - 包装 receive，对分块传输（无 Content-Length）按累计字节计数，超限即中断。

端点此前先把完整请求体缓冲进内存、之后才在服务层检查大小，单工作进程可被
超大请求 OOM 拖垮（见安全审计 V5）。
"""
from starlette.responses import JSONResponse


class RequestBodyTooLarge(Exception):
    """内部哨兵：413 已发出，用于中断后续请求处理。"""


class BodySizeLimitMiddleware:
    def __init__(self, app, max_bytes_provider):
        self.app = app
        self._max_bytes_provider = max_bytes_provider

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        max_bytes = self._max_bytes_provider()

        # 显式 Content-Length 超限：解析前拒绝
        headers = dict(scope["headers"])
        try:
            content_length = int(headers.get(b"content-length", 0))
        except ValueError:
            content_length = 0
        if content_length > max_bytes:
            await self._send_413(scope, receive, send)
            return

        seen = 0

        async def limited_receive():
            nonlocal seen
            message = await receive()
            if message["type"] == "http.request":
                seen += len(message.get("body", b""))
                if seen > max_bytes:
                    await self._send_413(scope, receive, send)
                    raise RequestBodyTooLarge()
            return message

        try:
            await self.app(scope, limited_receive, send)
        except RequestBodyTooLarge:
            pass  # 413 已发出，仅中断处理

    async def _send_413(self, scope, receive, send):
        await JSONResponse(
            status_code=413,
            content={
                "error_code": "PAYLOAD_TOO_LARGE",
                "message": "Request body too large",
            },
        )(scope, receive, send)

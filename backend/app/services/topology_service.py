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

    # 路由决策：如果全局禁用云端 或 有核心资产且配置路由到本地 → 使用 ollama
    actual_provider = provider_name
    # api_key 已在 router 层解密过，这里直接使用
    actual_api_key = api_key
    actual_base_url = base_url
    actual_model = model

    if not cloud_enabled:
        # 全局禁用云端，强制走 ollama
        actual_provider = "ollama"
        actual_api_key = ""
        actual_base_url = "http://localhost:11434"
        actual_model = get_config_value(db, "llm_model", "qwen2.5")
    elif has_core and route_core_to_local and actual_provider != "ollama":
        # 有核心资产且配置路由到本地
        actual_provider = "ollama"
        actual_api_key = ""
        actual_base_url = "http://localhost:11434"
        actual_model = get_config_value(db, "llm_model", "qwen2.5")

    # 构造资产数据（含端口）
    asset_data = []
    for a in assets:
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

    # 构造 prompt
    system_prompt = """你是一个专业的网络拓扑图生成助手。根据资产信息生成符合 drawio 标准格式的网络拓扑图，要求布局清晰、视觉美观。

## 输出格式（严格遵守）
返回完整的 drawio XML，包含 <mxfile> 根元素。结构如下：

<mxfile host="app.diagrams.net">
  <diagram name="Network Topology" id="topology">
    <mxGraphModel dx="1200" dy="800" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="1600" pageHeight="1200" math="0" shadow="0">
      <root>
        <mxCell id="0"/>
        <mxCell id="1" parent="0"/>
        <!-- 区域容器（swimlane） -->
        <!-- 资产节点 -->
        <!-- 连线 -->
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>

## 视觉规范

### 1. 区域分组（用 swimlane 容器）
不同 zone 用不同颜色的 swimlane 包裹，垂直并列布局：
- intranet: 蓝色 fillColor=#DBE5FE strokeColor=#1E40AF
- dmz: 橙色 fillColor=#FEF3C7 strokeColor=#92400E
- office: 青色 fillColor=#CFFAFE strokeColor=#0E7490
- management: 紫色 fillColor=#EDE9FE strokeColor=#5B21B6
- other: 灰色 fillColor=#F3F4F6 strokeColor=#6B7280

swimlane 节点 style 模板：
style="swimlane;fontStyle=1;align=center;verticalAlign=top;childLayout=stackLayout;horizontal=1;startSize=30;horizontalStack=0;resizeParent=0;resizeParentMax=0;collapsible=0;swimlaneFillColor=#ffffff;fillColor=#DBE5FE;strokeColor=#1E40AF;fontColor=#1E40AF;fontSize=13;"

### 2. 资产节点形状
不同 asset_type 用不同形状（drawio 内置 shape）：
- physical (物理服务器): shape=mscae/server, fillColor=#0078D4, fontColor=#FFFFFF
- virtual (虚拟机): shape=mscae/virtual_machine, fillColor=#0078D4, fontColor=#FFFFFF
- network_device (网络设备): shape=mscae/router, fillColor=#107C10, fontColor=#FFFFFF
- other: shape=ellipse, fillColor=#737373, fontColor=#FFFFFF

如果 importance=core，节点边框加粗为 strokeColor=#DC2626 strokeWidth=3。

简化示例 style（可直接使用）：
- 物理/虚拟: "rounded=1;whiteSpace=wrap;html=1;fillColor=#DBE5FE;strokeColor=#1E40AF;fontColor=#1E40AF;fontSize=12;"
- 网络设备: "shape=mxgraph.cisco.routers.router;html=1;fillColor=#107C10;strokeColor=#0B5A0B;fontColor=#FFFFFF;fontSize=12;"
- 核心资产边框: 在 style 后追加 "strokeColor=#DC2626;strokeWidth=3;"

### 3. 节点尺寸与布局
- 节点宽 120 高 60
- swimlane 容器宽至少 400，高根据子节点数量自适应（每行 3 个，间距 30）
- 不同 swimlane 之间留 60px 间距
- 节点 label 显示资产 ID + 服务大类（如 HOST_A_001\\nweb）

### 4. 节点 label 格式
使用换行展示多行信息：value="HOST_A_001&#10;ssh, http"
不要显示真实 IP 或主机名（脱敏数据）。

### 5. 连线规则
- 同一 group 内的节点用细线连接（strokeWidth=1）
- 跨 group 但 service_hint 互补的（如 web→db）用粗线带箭头（strokeWidth=2;endArrow=classic）
- 连线 style: "edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;exitX=0.5;exitY=1;exitDx=0;exitDy=0;entryX=0.5;entryY=0;entryDx=0;entryDy=0;"

## 关键要求
1. 必须返回完整的 <mxfile>...</mxfile>，不要包含任何解释文字
2. 不要使用 markdown 代码块包裹
3. 每个节点必须有 vertex="1" parent 属性
4. 每个连线必须有 edge="1" source/target 属性
5. swimlane 子节点的 parent 指向 swimlane 的 id
6. mxGeometry 必须包含 x, y, width, height 属性"""

    prompt = f"""以下是脱敏后的资产信息，请按上述视觉规范生成精美的网络拓扑图。

资产数据：
{json.dumps(sanitized, ensure_ascii=False, indent=2)}

请按以下步骤思考：
1. 按 zone 分组，每个 zone 一个 swimlane 容器
2. 每个节点放入对应的 swimlane，节点 label 包含 id 和 service_hint
3. importance=core 的节点用红色加粗边框突出
4. 同 group 节点用细线连接，跨 group 的服务关系用箭头
5. 整体水平布局，swimlane 自左向右排列

直接输出完整的 <mxfile>...</mxfile> XML，无任何额外文字。"""

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

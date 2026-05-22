"""
应用服务清单 Pydantic v2 Schema
"""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


AppSource = Literal["manual", "scan"]
AppStatus = Literal["active", "decommissioned"]


class AssetAppCreate(BaseModel):
    """新增应用"""
    name: str = Field(..., max_length=100, description="应用名称，如 nginx、mysql-server")
    version: str | None = Field(None, max_length=100, description="版本号")
    category: str | None = Field(None, max_length=50, description="应用大类")
    port: int | None = Field(None, ge=1, le=65535, description="主要监听端口")
    protocol: str | None = Field(None, pattern=r"^(tcp|udp)$", description="协议 tcp/udp")
    install_path: str | None = Field(None, max_length=255, description="安装路径")
    config_path: str | None = Field(None, max_length=255, description="配置文件路径")
    notes: str | None = Field(None, description="备注")


class AssetAppUpdate(BaseModel):
    """更新应用（PATCH，所有字段可选）"""
    name: str | None = Field(None, max_length=100)
    version: str | None = Field(None, max_length=100)
    category: str | None = Field(None, max_length=50)
    port: int | None = Field(None, ge=1, le=65535)
    protocol: str | None = Field(None, pattern=r"^(tcp|udp)$")
    install_path: str | None = Field(None, max_length=255)
    config_path: str | None = Field(None, max_length=255)
    notes: str | None = None
    status: AppStatus | None = None


class AssetAppRead(BaseModel):
    """应用响应"""
    model_config = {"from_attributes": True}

    id: int
    asset_id: int
    name: str
    version: str | None
    category: str | None
    port: int | None
    protocol: str | None
    install_path: str | None
    config_path: str | None
    notes: str | None
    source: str
    status: str
    created_at: datetime
    updated_at: datetime
    created_by: int | None


class AssetAppListResponse(BaseModel):
    """应用列表响应"""
    items: list[AssetAppRead]
    total: int


class AppSearchItem(BaseModel):
    """全局应用搜索结果项"""
    model_config = {"from_attributes": True}

    id: int
    asset_id: int
    name: str
    version: str | None
    category: str | None
    port: int | None
    # 关联资产信息
    asset_no: str
    ip_address: str
    hostname: str | None


class AppSearchResponse(BaseModel):
    """全局应用搜索响应"""
    items: list[AppSearchItem]
    total: int

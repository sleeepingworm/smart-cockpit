from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional


# ============= 数据库表模型 =============
class Alert(SQLModel, table=True):
    """告警表"""
    __tablename__ = "alerts"

    id: int | None = Field(default=None, primary_key=True)
    vehicle_id: int = Field(foreign_key="vehicles.id", nullable=False, index=True, description="关联车辆ID")
    alert_type: str = Field(max_length=50, nullable=False, description="告警类型：fatigue/distraction/speeding/collision/other")
    alert_level: str = Field(max_length=20, nullable=False, description="告警级别：info/warning/critical")
    content: str = Field(max_length=500, nullable=False, description="告警内容")
    status: int = Field(default=0, description="状态：0未处理 1已确认 2已处理")
    occurred_at: datetime = Field(default_factory=datetime.now, description="告警发生时间")
    handled_at: datetime | None = Field(default=None, description="处理时间")
    handler: str | None = Field(default=None, max_length=50, description="处理人")
    remark: str | None = Field(default=None, max_length=500, description="处理备注")
    created_at: datetime | None = Field(default_factory=datetime.now)
    updated_at: datetime | None = Field(default_factory=datetime.now)


# ============= 请求模型 =============
class AlertCreate(SQLModel):
    """创建告警"""
    vehicle_id: int = Field(description="车辆ID")
    alert_type: str = Field(description="告警类型", max_length=50)
    alert_level: str = Field(description="告警级别：info/warning/critical", max_length=20)
    content: str = Field(description="告警内容", max_length=500)
    occurred_at: datetime = Field(default_factory=datetime.now, description="告警发生时间")


class AlertUpdate(SQLModel):
    """更新告警（全部可选）"""
    alert_type: str | None = Field(default=None, description="告警类型", max_length=50)
    alert_level: str | None = Field(default=None, description="告警级别", max_length=20)
    content: str | None = Field(default=None, description="告警内容", max_length=500)
    status: int | None = Field(default=None, description="状态：0未处理 1已确认 2已处理")
    handled_at: datetime | None = Field(default=None, description="处理时间")
    handler: str | None = Field(default=None, description="处理人", max_length=50)
    remark: str | None = Field(default=None, description="处理备注", max_length=500)


# ============= 响应模型 =============
class AlertResp(SQLModel):
    """返回给前端的告警信息"""
    id: int
    vehicle_id: int
    alert_type: str
    alert_level: str
    content: str
    status: int
    occurred_at: datetime | None = None
    handled_at: datetime | None = None
    handler: str | None = None
    remark: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
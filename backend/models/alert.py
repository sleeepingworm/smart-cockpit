from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional


# ============= 数据库表模型 =============
class Alert(SQLModel, table=True):
    """告警表"""
    __tablename__ = "alerts"

    id: Optional[int] = Field(default=None, primary_key=True)
    alert_type: str = Field(max_length=50, nullable=False, description="告警类型：疲劳驾驶/障碍物检测/超速警告")
    level: str = Field(default="warning", max_length=20, description="级别：info(提示)/warning(警告)/danger(危险)")
    status: str = Field(default="pending", max_length=20, description="状态：pending(待处理)/handled(已处理)/ignored(已忽略)")
    description: Optional[str] = Field(default=None, description="详细描述")
    vehicle_id: Optional[str] = Field(default=None, max_length=50, description="车牌号（字符串存）")
    driver_name: Optional[str] = Field(default=None, max_length=50, description="司机姓名（冗余）")
    image_path: Optional[str] = Field(default=None, description="告警截图路径（Day10接入）")
    handled_at: Optional[datetime] = Field(default=None, description="处理时间")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = Field(default=None)


# ============= 请求模型 =============
class AlertCreate(SQLModel):
    """创建告警"""
    alert_type: str = Field(description="告警类型", max_length=50)
    level: str = Field(default="warning", description="级别", max_length=20)
    status: str = Field(default="pending", description="状态", max_length=20)
    description: Optional[str] = Field(default=None, description="详细描述")
    vehicle_id: Optional[str] = Field(default=None, description="车牌号", max_length=50)
    driver_name: Optional[str] = Field(default=None, description="司机姓名", max_length=50)
    image_path: Optional[str] = Field(default=None, description="告警截图路径")


class AlertHandle(SQLModel):
    """处理告警请求"""
    status: str = Field(description="目标状态：handled(已处理) / ignored(已忽略)", max_length=20)


# ============= 响应模型 =============
class AlertResp(SQLModel):
    """返回给前端的告警信息"""
    id: int
    alert_type: str
    level: str
    status: str
    description: Optional[str] = None
    vehicle_id: Optional[str] = None
    driver_name: Optional[str] = None
    image_path: Optional[str] = None
    handled_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
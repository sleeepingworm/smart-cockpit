from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional


# ============= 数据库表模型 =============
class Vehicle(SQLModel, table=True):
    """车辆表"""
    __tablename__ = "vehicles"

    id: int | None = Field(default=None, primary_key=True)
    plate_number: str = Field(max_length=20, unique=True, nullable=False, description="车牌号")
    brand: str = Field(max_length=50, nullable=False, description="品牌")
    model: str = Field(max_length=50, nullable=False, description="型号")
    color: str | None = Field(default=None, max_length=20, description="颜色")
    owner: str | None = Field(default=None, max_length=50, description="车主")
    owner_phone: str | None = Field(default=None, max_length=20, description="车主电话")
    status: int = Field(default=1, description="状态：1正常 0停用")
    created_at: datetime | None = Field(default_factory=datetime.now)
    updated_at: datetime | None = Field(default_factory=datetime.now)


# ============= 请求模型 =============
class VehicleCreate(SQLModel):
    """创建车辆时客户端需要传的字段"""
    plate_number: str = Field(description="车牌号（7-20字符）", min_length=7, max_length=20)
    brand: str = Field(description="品牌，如：比亚迪/特斯拉/大众", max_length=50)
    model: str = Field(description="型号，如：汉EV/Model 3/速腾", max_length=50)
    color: str | None = Field(default=None, description="颜色，如：珍珠白/星空黑", max_length=20)
    owner: str | None = Field(default=None, description="车主姓名", max_length=50)
    owner_phone: str | None = Field(default=None, description="车主联系电话", max_length=20)
    status: int = Field(default=1, description="车辆状态：1=正常 0=停用")


class VehicleUpdate(SQLModel):
    """更新车辆时所有字段可选（想改哪个传哪个）"""
    plate_number: str | None = Field(default=None, description="车牌号", min_length=7, max_length=20)
    brand: str | None = Field(default=None, description="品牌", max_length=50)
    model: str | None = Field(default=None, description="型号", max_length=50)
    color: str | None = Field(default=None, description="颜色", max_length=20)
    owner: str | None = Field(default=None, description="车主", max_length=50)
    owner_phone: str | None = Field(default=None, description="联系电话", max_length=20)
    status: int | None = Field(default=None, description="状态：1=正常 0=停用")


# ============= 响应模型 =============
class VehicleResp(SQLModel):
    """返回给前端的车辆信息"""
    id: int = Field(description="车辆ID")
    plate_number: str = Field(description="车牌号")
    brand: str = Field(description="品牌")
    model: str = Field(description="型号")
    color: str | None = Field(description="颜色")
    owner: str | None = Field(description="车主")
    owner_phone: str | None = Field(description="联系电话")
    status: int = Field(description="状态：1=正常 0=停用")
    created_at: datetime = Field(description="创建时间")
    updated_at: datetime | None = Field(description="更新时间")
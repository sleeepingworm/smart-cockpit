from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional


class Face(SQLModel, table=True):
    __tablename__ = "faces"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True, description="关联驾驶员ID")
    name: str = Field(max_length=50, description="驾驶员姓名（冗余快照）")
    employee_id: str | None = Field(default=None, max_length=50, description="工号")
    image_url: str = Field(max_length=255, description="访问URL：/media/faces/xxx.jpg")
    file_path: str = Field(max_length=255, description="服务器物理路径")
    is_active: bool = Field(default=True, description="是否启用")
    created_by: int | None = Field(default=None, foreign_key="users.id", description="录入人（管理员）")
    created_at: datetime | None = Field(default_factory=datetime.now)
    updated_at: datetime | None = Field(default_factory=datetime.now)


class FaceCreate(SQLModel):
    user_id: int
    name: str
    employee_id: str | None = None
    image_url: str
    file_path: str


class FaceResp(SQLModel):
    id: int
    user_id: int
    name: str
    employee_id: str | None
    image_url: str
    file_path: str  # 新增file_path字段，编辑时需要
    is_active: bool
    created_at: datetime
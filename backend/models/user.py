from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional


class User(SQLModel, table=True):
    __tablename__ = "users"
    id: int | None = Field(default=None, primary_key=True)
    username: str = Field(max_length=50, unique=True, nullable=False, description="用户名")
    email: str = Field(max_length=100, unique=True, nullable=False, description="邮箱")
    hashed_password: str = Field(max_length=255, nullable=False, description="哈希后的密码")
    full_name: str | None = Field(default=None, max_length=50, description="真实姓名")
    phone: str | None = Field(default=None, max_length=20, description="手机号")
    avatar: str | None = Field(default=None, max_length=255, description="头像URL")
    role: str = Field(default="driver", max_length=20, description="角色：admin管理员/driver驾驶员")
    is_active: bool = Field(default=True, description="是否启用")
    created_at: datetime | None = Field(default_factory=datetime.now)
    updated_at: datetime | None = Field(default_factory=datetime.now)


class UserCreate(SQLModel):
    """注册/创建用户请求"""
    username: str = Field(min_length=3, max_length=50, description="用户名")
    email: str = Field(max_length=100, description="邮箱")
    password: str = Field(min_length=6, max_length=50, description="密码（至少6位）")
    full_name: str | None = Field(default=None, description="姓名")
    phone: str | None = Field(default=None, description="手机号")
    role: str = Field(default="driver", description="角色：admin/driver")


class UserLogin(SQLModel):
    """登录请求"""
    username: str = Field(description="用户名")
    password: str = Field(description="密码")


class UserResp(SQLModel):
    """返回给前端的用户信息（不含密码！）"""
    id: int
    username: str
    email: str
    full_name: str | None
    phone: str | None
    avatar: str | None
    role: str
    is_active: bool
    created_at: datetime


class TokenResp(SQLModel):
    """登录成功返回的token"""
    access_token: str = Field(description="JWT访问令牌")
    token_type: str = Field(default="bearer", description="令牌类型")
    user: UserResp
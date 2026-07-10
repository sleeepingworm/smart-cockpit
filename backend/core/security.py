from hashlib import sha256
from secrets import token_hex
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import jwt, JWTError
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlmodel import Session, select

from config.settings import settings
from db.database import SessionDep
from models.user import User

bearer_scheme = HTTPBearer()


def hash_password(password: str) -> str:
    """
    密码哈希：生成随机salt，返回 'salt$sha256hex' 格式
    """
    salt = token_hex(16)  # 生成16字节(32字符)随机十六进制字符串
    hashed = sha256((salt + password).encode("utf-8")).hexdigest()
    return f"{salt}${hashed}"


def verify_password(password: str, password_hash: str) -> bool:
    """
    校验密码：从password_hash中取出salt，用同样方式算hash比较
    """
    try:
        salt, hashed = password_hash.split("$", 1)
    except ValueError:
        return False
    return sha256((salt + password).encode("utf-8")).hexdigest() == hashed


def _create_token(sub: str | int, expires_delta: timedelta) -> str:
    """内部函数：创建JWT token"""
    expire = datetime.now(timezone.utc) + expires_delta
    payload = {"sub": str(sub), "exp": expire}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_access_token(user_id: int) -> str:
    """创建访问token（登录时调用）"""
    return _create_token(
        sub=user_id,
        expires_delta=timedelta(days=settings.JWT_EXPIRE_DAYS),
    )


def get_current_user(
    db: SessionDep,
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> User:
    """
    依赖项：从请求头Bearer token中解析出当前用户
    用在需要登录的接口上：current_user: User = Depends(get_current_user)
    """
    token = credentials.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无效的凭证",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
        )
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.get(User, int(user_id))
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(status_code=403, detail="账号已禁用")
    return user
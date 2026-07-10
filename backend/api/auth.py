from fastapi import APIRouter, HTTPException, status
from sqlmodel import Session, select

from db.database import SessionDep
from models.user import User, UserCreate, UserLogin, UserResp, TokenResp
from core.security import hash_password, verify_password, create_access_token

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/register", response_model=dict, summary="用户注册", status_code=201)
def register(req: UserCreate, db: SessionDep):
    """用户注册（默认role=driver，管理员需要手动创建或seed初始）"""
    # 检查用户名是否已存在
    exists_user = db.exec(select(User).where(User.username == req.username)).first()
    if exists_user:
        raise HTTPException(status_code=400, detail="用户名已被注册")

    # 检查邮箱是否已存在
    exists_email = db.exec(select(User).where(User.email == req.email)).first()
    if exists_email:
        raise HTTPException(status_code=400, detail="邮箱已被注册")

    # 创建用户（密码哈希）
    user = User(
        username=req.username,
        email=req.email,
        hashed_password=hash_password(req.password),
        full_name=req.full_name,
        phone=req.phone,
        role=req.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return {
        "code": 200,
        "message": "注册成功",
        "data": UserResp.model_validate(user),
    }


@router.post("/login", response_model=dict, summary="用户名密码登录")
def login(req: UserLogin, db: SessionDep):
    """账号密码登录，返回JWT token"""
    # 查用户
    user = db.exec(select(User).where(User.username == req.username)).first()
    if not user:
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    # 验密码
    if not verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    # 检查账号状态
    if not user.is_active:
        raise HTTPException(status_code=403, detail="账号已被禁用")

    # 签发token
    token = create_access_token(user.id)

    return {
        "code": 200,
        "message": "登录成功",
        "data": TokenResp(
            access_token=token,
            token_type="bearer",
            user=UserResp.model_validate(user),
        ).model_dump(),
    }
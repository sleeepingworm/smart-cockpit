from fastapi import APIRouter, Query, Depends
from sqlmodel import Session, select, or_
from typing import Optional
from datetime import datetime

from db.database import SessionDep
from models.user import User, UserCreate, UserResp
from core.security import hash_password, get_current_user, require_role

router = APIRouter(
    prefix="/users",
    tags=["用户管理"],
    dependencies=[Depends(get_current_user)],    # 所有接口要登录（用无返回值的守卫，避免response field错误）
)


@router.get("/", summary="分页查询用户列表")
def list_users(
    db: SessionDep,
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(10, ge=1, le=100, description="每页条数"),
    keyword: Optional[str] = Query(None, description="搜索关键字（用户名/邮箱/姓名）"),
    role: Optional[str] = Query(None, description="按角色筛选"),
    is_active: Optional[int] = Query(None, ge=0, le=1, description="按启用状态筛选"),
):
    """分页搜索用户列表"""
    # 构建查询
    statement = select(User)
    count_statement = select(User)

    # 关键字模糊搜索（用户名或邮箱或姓名包含keyword）
    if keyword:
        like = f"%{keyword}%"
        statement = statement.where(or_(
            User.username.like(like),
            User.email.like(like),
            User.full_name.like(like),
        ))
        count_statement = count_statement.where(or_(
            User.username.like(like),
            User.email.like(like),
            User.full_name.like(like),
        ))

    if role:
        statement = statement.where(User.role == role)
        count_statement = count_statement.where(User.role == role)

    if is_active is not None:
        statement = statement.where(User.is_active == bool(is_active))
        count_statement = count_statement.where(User.is_active == bool(is_active))

    # 总数
    total = len(db.exec(count_statement).all())

    # 分页
    statement = statement.offset((page - 1) * size).limit(size).order_by(User.created_at.desc())
    users = db.exec(statement).all()

    return {
        "code": 200,
        "message": "查询成功",
        "data": [UserResp.model_validate(u) for u in users],
        "total": total,
        "page": page,
        "size": size,
    }


@router.get("/{user_id}", summary="获取用户详情")
def get_user(user_id: int, db: SessionDep):
    user = db.get(User, user_id)
    if not user:
        return {"code": 404, "message": "用户不存在", "data": None}
    return {"code": 200, "message": "success", "data": UserResp.model_validate(user)}


@router.post("/", summary="新增用户（管理员）", status_code=201)
def create_user(
    req: UserCreate,
    db: SessionDep,
    current_user: User = Depends(require_role(["admin"])),
):
    """管理员新建用户"""
    # 查重
    if db.exec(select(User).where(User.username == req.username)).first():
        return {"code": 400, "message": "用户名已存在", "data": None}
    if db.exec(select(User).where(User.email == req.email)).first():
        return {"code": 400, "message": "邮箱已存在", "data": None}

    user = User(
        username=req.username,
        email=req.email,
        hashed_password=hash_password(req.password),   # 密码哈希！绝对不能明文存
        full_name=req.full_name,
        phone=req.phone,
        role=req.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return {"code": 200, "message": "创建成功", "data": UserResp.model_validate(user)}


@router.put("/{user_id}", summary="更新用户（管理员）")
def update_user(
    user_id: int,
    req_data: dict,
    db: SessionDep,
    current_user: User = Depends(require_role(["admin"])),
):
    """更新用户。允许更新：full_name/phone/role/is_active/email/password"""
    user = db.get(User, user_id)
    if not user:
        return {"code": 404, "message": "用户不存在", "data": None}

    allowed_fields = {"full_name", "phone", "role", "is_active", "email", "password"}
    for field, value in req_data.items():
        if field in allowed_fields:
            if field == "password" and value:
                user.hashed_password = hash_password(value)   # 密码改了重新哈希
            else:
                setattr(user, field, value)

    user.updated_at = datetime.now()
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"code": 200, "message": "更新成功", "data": UserResp.model_validate(user)}


@router.delete("/{user_id}", summary="删除用户（管理员）")
def delete_user(
    user_id: int,
    db: SessionDep,
    current_user: User = Depends(require_role(["admin"])),
):
    """删除用户（不能删自己）"""
    if user_id == current_user.id:
        return {"code": 400, "message": "不能删除自己的账号", "data": None}

    user = db.get(User, user_id)
    if not user:
        return {"code": 404, "message": "用户不存在", "data": None}

    db.delete(user)
    db.commit()
    return {"code": 200, "message": "删除成功", "data": None}
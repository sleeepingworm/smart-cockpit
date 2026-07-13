from fastapi import APIRouter, HTTPException, status
from sqlmodel import Session, select

from db.database import SessionDep
from models.user import User, UserCreate, UserLogin, UserResp, TokenResp
from core.security import hash_password, verify_password, create_access_token
import os
import uuid
from fastapi import UploadFile, File
from pathlib import Path

from config.settings import settings
from models.face_library import Face
from ai.face_recognition import verify_face

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/face-login", summary="人脸识别登录")
async def face_login(
    db: SessionDep,
    file: UploadFile = File(..., description="人脸抓拍 JPEG"),
):
    # 1. 校验文件类型
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(400, detail="请上传图片文件")

    # 2. 保存到临时目录
    tmp_dir = Path(settings.UPLOAD_DIR) / "tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    tmp_name = f"{uuid.uuid4().hex}.jpg"
    tmp_path = tmp_dir / tmp_name

    try:
        # 写入文件
        content = await file.read()
        with open(tmp_path, "wb") as f:
            f.write(content)

        # 3. 拉人脸库（只查 driver 且启用中的）
        stmt = (
            select(Face, User)
            .join(User, Face.user_id == User.id)
            .where(
                Face.is_active == True,
                Face.is_deleted == False,
                User.is_active == True,
                User.is_deleted == False,
                User.role == "driver",
            )
        )
        rows = db.exec(stmt).all()

        if not rows:
            raise HTTPException(404, detail="人脸库为空，请联系管理员录入")

        # 组装成 face_db_items
        face_items = []
        for face, user in rows:
            face_items.append({
                "user_id": user.id,
                "name": user.full_name or user.username,
                # ⚠️ file_path 存的是相对路径，比对时要拼绝对路径
                "file_path": os.path.join(settings.UPLOAD_DIR, face.file_path),
            })

        # 4. 1:N 比对
        match = verify_face(str(tmp_path), face_items)

        if not match:
            raise HTTPException(401, detail="未识别到已录入的驾驶员")

        # 5. 命中，签发 token
        user = db.get(User, match["user_id"])
        if not user or not user.is_active:
            raise HTTPException(403, detail="账号已被禁用")

        token = create_access_token(user.id)

        return {
            "code": 200,
            "message": f"欢迎，{match['name']}",
            "data": TokenResp(
                access_token=token,
                token_type="bearer",
                user=UserResp.model_validate(user),
            ).model_dump(),
        }

    finally:
        # 6. 无论成功失败，删临时文件
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except Exception:
                pass


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
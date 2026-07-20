import os
import uuid
from pathlib import Path
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlmodel import Session, SQLModel, select
from datetime import datetime

from db.database import SessionDep
from config.settings import settings
from models.face_library import Face, FaceCreate, FaceResp
from core.security import get_current_user

router = APIRouter(
    prefix="/faces",
    tags=["人脸库管理"],
    dependencies=[Depends(get_current_user)],
)

# ============= 上传配置 ==============
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/bmp", "image/webp"}
MAX_SIZE = 5 * 1024 * 1024  # 5MB


@router.post("/upload", summary="上传人脸图片")
async def upload_face(file: UploadFile = File(...)):
    """上传人脸图片：校验类型→校验大小→UUID重命名保存→返回URL"""
    # 1. 扩展名校验
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"不支持的图片格式，仅支持 {ALLOWED_EXTENSIONS}")

    # 2. Content-Type校验（防止改扩展名绕过）
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail="文件类型不合法，请上传真实图片")

    # 3. 文件大小校验
    content = await file.read()
    if len(content) > MAX_SIZE:
        raise HTTPException(status_code=400, detail=f"图片大小不能超过{MAX_SIZE // 1024 // 1024}MB")

    # 4. UUID重命名保存
    new_filename = f"{uuid.uuid4().hex}{ext}"
    save_dir = Path(settings.UPLOAD_DIR) / "faces"
    save_path = save_dir / new_filename
    with open(save_path, "wb") as f:
        f.write(content)

    # 5. 返回可访问URL
    file_url = f"/static/faces/{new_filename}"
    return {
        "code": 200,
        "message": "上传成功",
        "data": {
            "filename": new_filename,
            "original_name": file.filename,
            "url": file_url,
            "file_path": f"faces/{new_filename}",  # 返回相对路径的file_path
            "size": len(content),
        },
    }


# ============= 请求模型（face_library 没有 FaceUpdate，在此补充）=============
class FaceUpdate(SQLModel):
    """更新人脸记录（全部可选）"""
    name: str | None = None
    employee_id: str | None = None
    image_url: str | None = None
    file_path: str | None = None
    is_active: bool | None = None


@router.get("/", response_model=dict)
def list_faces(
    db: SessionDep,
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(10, ge=1, le=100, description="每页条数"),
):
    """分页查询人脸列表"""
    total = len(db.exec(select(Face)).all())

    statement = select(Face).offset((page - 1) * size).limit(size).order_by(Face.created_at.desc())
    faces = db.exec(statement).all()

    data = [FaceResp.model_validate(f) for f in faces]

    return {
        "code": 200,
        "message": "查询成功",
        "data": data,
        "total": total,
        "page": page,
        "size": size,
    }


@router.get("/{face_id}", response_model=dict)
def get_face(face_id: int, db: SessionDep):
    """根据ID查单条人脸记录"""
    face = db.get(Face, face_id)
    if not face:
        return {"code": 404, "message": f"人脸记录{face_id}不存在", "data": None}
    return {
        "code": 200,
        "message": "success",
        "data": FaceResp.model_validate(face),
    }


@router.post("/", response_model=dict, status_code=201)
def create_face(req: FaceCreate, db: SessionDep):
    """新建人脸记录"""
    face = Face.model_validate(req)
    db.add(face)
    db.commit()
    db.refresh(face)

    return {
        "code": 200,
        "message": "创建成功",
        "data": FaceResp.model_validate(face),
    }


@router.put("/{face_id}", response_model=dict)
def update_face(face_id: int, req: FaceUpdate, db: SessionDep):
    """更新人脸记录"""
    face = db.get(Face, face_id)
    if not face:
        return {"code": 404, "message": f"人脸记录{face_id}不存在", "data": None}

    update_data = req.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(face, field, value)
    face.updated_at = datetime.now()

    db.add(face)
    db.commit()
    db.refresh(face)

    return {
        "code": 200,
        "message": "更新成功",
        "data": FaceResp.model_validate(face),
    }


@router.delete("/{face_id}", response_model=dict)
def delete_face(face_id: int, db: SessionDep):
    """删除人脸记录（同步删除物理文件）"""
    face = db.get(Face, face_id)
    if not face:
        return {"code": 404, "message": f"人脸记录{face_id}不存在", "data": None}

    # ★ 先删物理文件
    if face.file_path and os.path.exists(face.file_path):
        os.remove(face.file_path)

    # 再删数据库记录
    db.delete(face)
    db.commit()

    return {"code": 200, "message": "删除成功", "data": None}
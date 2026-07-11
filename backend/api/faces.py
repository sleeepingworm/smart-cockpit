from fastapi import APIRouter, File, UploadFile, Depends, HTTPException
from sqlmodel import Session
import uuid
import os
from pathlib import Path

from db.database import SessionDep
from config.settings import settings
from core.security import get_current_user

router = APIRouter(
    prefix="/faces",
    tags=["人脸库"],
    dependencies=[Depends(get_current_user)],
)

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/bmp", "image/webp"}
MAX_SIZE = 5 * 1024 * 1024   # 5MB


@router.post("/upload", summary="上传人脸图片")
async def upload_face(file: UploadFile = File(...)):
    """
    上传人脸图片：
    1. 校验文件类型（扩展名+Content-Type双重校验）
    2. 校验文件大小
    3. UUID重命名保存到 uploads/faces/
    4. 返回可访问URL
    """
    # 1. 扩展名校验
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"不支持的图片格式，仅支持 {ALLOWED_EXTENSIONS}")

    # 2. Content-Type校验（防止改扩展名绕过）
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail="文件类型不合法，请上传真实图片")

    # 3. 文件大小校验（读取前判断）
    # UploadFile.file 是类文件对象，但长度要读一次才知道
    content = await file.read()
    if len(content) > MAX_SIZE:
        raise HTTPException(status_code=400, detail=f"图片大小不能超过{MAX_SIZE//1024//1024}MB")

    # 4. 生成UUID文件名，保存
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
            "size": len(content),
        }
    }
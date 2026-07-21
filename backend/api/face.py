from fastapi import APIRouter, Depends, File, UploadFile, HTTPException
from sqlmodel import Session, select
from pathlib import Path
import tempfile
import os
import cv2
import numpy as np

from db.database import SessionDep
from config.settings import settings
from models.face_library import Face
from core.security import get_current_user
from ai.face_recognition import (
    detect_faces,
    verify_pair,
    verify_face,
    get_face_attributes,
    liveness_detection,
    extract_embedding
)

router = APIRouter(
    prefix="/face",
    tags=["人脸识别功能"],
)

# ============= 工具函数 =============
async def _save_temp_file(file: UploadFile) -> str:
    """保存上传的文件到临时目录，返回文件路径"""
    ext = Path(file.filename or "").suffix.lower()
    if ext not in {".jpg", ".jpeg", ".png", ".bmp", ".webp"}:
        raise HTTPException(status_code=400, detail=f"不支持的图片格式")

    content = await file.read()
    if len(content) > 5 * 1024 * 1024:  # 5MB限制
        raise HTTPException(status_code=400, detail="图片大小不能超过5MB")

    # 保存到临时文件
    temp_file = tempfile.NamedTemporaryFile(suffix=ext, delete=False)
    temp_file.write(content)
    temp_file.close()
    return temp_file.name


def _get_full_path(file_path: str) -> str:
    """将相对路径转换为绝对路径"""
    if os.path.isabs(file_path):
        return file_path
    # 处理upload目录下的相对路径
    if file_path.startswith("faces/"):
        return str(Path(settings.UPLOAD_DIR) / file_path)
    return file_path


# ============= API接口 =============
@router.post("/detect", summary="人脸检测")
async def detect_face_api(file: UploadFile = File(...)):
    """检测图片中的人脸，返回人脸框、关键点、年龄、性别等信息"""
    try:
        temp_path = await _save_temp_file(file)
        faces = detect_faces(temp_path)
        os.unlink(temp_path)

        if not faces:
            return {
                "code": 200,
                "message": "未检测到人脸",
                "data": []
            }

        # 格式化返回结果
        result = []
        for face in faces:
            keypoints = face["keypoints"] if face["keypoints"] is not None else []
            result.append({
                "bbox": [round(float(x), 2) for x in face["bbox"]],
                "age": int(face["age"]),
                "gender": "女" if int(face["gender"]) == 0 else "男",
                "det_score": round(float(face["det_score"]), 4),
                "keypoints": [[round(float(x), 2) for x in kp] for kp in keypoints]
            })

        return {
            "code": 200,
            "message": f"检测到{len(result)}张人脸",
            "data": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"检测失败：{str(e)}")


@router.post("/attributes", summary="人脸属性分析")
async def face_attributes_api(file: UploadFile = File(...)):
    """获取人脸详细属性：年龄、性别、位置等"""
    try:
        temp_path = await _save_temp_file(file)
        attrs = get_face_attributes(temp_path)
        os.unlink(temp_path)

        if not attrs:
            return {
                "code": 200,
                "message": "未检测到人脸",
                "data": None
            }

        return {
            "code": 200,
            "message": "获取属性成功",
            "data": attrs
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"属性分析失败：{str(e)}")


@router.post("/verify/pair", summary="1:1人脸比对")
async def verify_pair_api(
    image1: UploadFile = File(..., description="第一张人脸图片"),
    image2: UploadFile = File(..., description="第二张人脸图片")
):
    """比对两张人脸图片是否为同一个人"""
    try:
        path1 = await _save_temp_file(image1)
        path2 = await _save_temp_file(image2)

        result = verify_pair(path1, path2)

        os.unlink(path1)
        os.unlink(path2)

        return {
            "code": 200,
            "message": "比对完成",
            "data": {
                "is_same_person": result["verified"],
                "similarity": round(float(result["similarity"]), 4),
                "distance": round(float(result["distance"]), 4),
                "threshold": round(float(result["threshold"]), 4)
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"比对失败：{str(e)}")


@router.post("/verify/search", summary="1:N人脸搜索")
async def verify_search_api(
    db: SessionDep,  # SessionDep已经包含Depends，不需要重复写
    file: UploadFile = File(..., description="待搜索的人脸图片"),
):
    """在人脸库中搜索最匹配的人脸"""
    try:
        temp_path = await _save_temp_file(file)

        # 获取所有人脸库记录
        faces = db.exec(select(Face).where(Face.is_active == True)).all()
        face_db_items = []
        for face in faces:
            full_path = _get_full_path(face.file_path)
            if os.path.exists(full_path):
                face_db_items.append({
                    "user_id": face.id,
                    "name": face.name,
                    "file_path": full_path,
                    "employee_id": face.employee_id
                })

        if not face_db_items:
            os.unlink(temp_path)
            return {
                "code": 200,
                "message": "人脸库为空",
                "data": None
            }

        # 进行1:N比对
        result = verify_face(temp_path, face_db_items)
        os.unlink(temp_path)

        if result:
            return {
                "code": 200,
                "message": "匹配成功",
                "data": {
                    "user_id": result["user_id"],
                    "name": result["name"],
                    "similarity": round(1 - float(result["distance"]), 4),
                    "distance": round(float(result["distance"]), 4),
                    "threshold": round(float(result["threshold"]), 4)
                }
            }
        else:
            return {
                "code": 200,
                "message": "未找到匹配的人脸",
                "data": None
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜索失败：{str(e)}")


@router.post("/liveness", summary="活体检测")
async def liveness_detection_api(file: UploadFile = File(...)):
    """检测是否为活体人脸，防止照片欺骗"""
    try:
        temp_path = await _save_temp_file(file)
        result = liveness_detection(temp_path)
        os.unlink(temp_path)

        return {
            "code": 200,
            "message": "检测完成",
            "data": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"活体检测失败：{str(e)}")


@router.post("/extract-embedding", summary="提取人脸特征向量")
async def extract_embedding_api(file: UploadFile = File(...)):
    """提取人脸的512维特征向量，用于人脸库构建或批量比对"""
    try:
        temp_path = await _save_temp_file(file)
        embedding = extract_embedding(temp_path)
        os.unlink(temp_path)

        if embedding is None:
            return {
                "code": 200,
                "message": "未检测到人脸",
                "data": None
            }

        return {
            "code": 200,
            "message": "特征提取成功",
            "data": {
                "embedding": [round(float(x), 6) for x in embedding.tolist()],
                "dimension": len(embedding)
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"特征提取失败：{str(e)}")


@router.post("/batch-verify", summary="批量人脸比对")
async def batch_verify_api(
    target_file: UploadFile = File(..., description="目标人脸图片"),
    file_list: list[UploadFile] = File(..., description="待比对的人脸图片列表")
):
    """批量比对多张图片与目标图片是否为同一个人"""
    try:
        target_path = await _save_temp_file(target_file)
        results = []

        for idx, file in enumerate(file_list):
            try:
                temp_path = await _save_temp_file(file)
                verify_result = verify_pair(target_path, temp_path)
                os.unlink(temp_path)

                results.append({
                    "index": idx,
                    "filename": file.filename,
                    "is_same_person": verify_result["verified"],
                    "similarity": round(float(verify_result["similarity"]), 4)
                })
            except Exception as e:
                results.append({
                    "index": idx,
                    "filename": file.filename,
                    "error": str(e)
                })

        os.unlink(target_path)

        return {
            "code": 200,
            "message": f"批量比对完成，共{len(results)}张图片",
            "data": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批量比对失败：{str(e)}")

import os
import logging
from typing import Optional
from pathlib import Path

logger = logging.getLogger(__name__)

# ============= 全局配置 =============
MODEL_NAME = "Facenet512"        # 512 维 embedding，DeepFace 内建
DISTANCE_METRIC = "cosine"       # 余弦距离
# detector_backend 依次尝试，失败自动降级到下一个
DETECTOR_BACKENDS = ["opencv", "retinaface"]

_warmed_up = False   # 预热标志


def warm_up(sample_image: Optional[str] = None) -> None:
    """
    服务启动时预热：跑一次假推理，把模型权重加载进内存。
    - 有样本图：用样本图 verify 自己（distance≈0）
    - 无样本图：跳过（首次 face-login 请求会自动加载）
    """
    global _warmed_up
    if _warmed_up:
        return
    try:
        from deepface import DeepFace
        if sample_image and os.path.exists(sample_image):
            logger.info(f"[face] 预热开始，样本图：{sample_image}")
            DeepFace.verify(
                img1_path=sample_image,
                img2_path=sample_image,
                model_name=MODEL_NAME,
                distance_metric=DISTANCE_METRIC,
                detector_backend=DETECTOR_BACKENDS[0],
                enforce_detection=False,
            )
            logger.info("[face] 预热完成")
        _warmed_up = True
    except Exception as e:
        logger.warning(f"[face] 预热失败（不影响正常使用）：{e}")


def verify_pair(img1: str, img2: str) -> dict:
    """
    比对两张图片，返回 DeepFace 原始 dict。
    detector_backend 依次尝试，全都失败则抛异常。
    """
    from deepface import DeepFace

    last_error: Optional[Exception] = None
    for backend in DETECTOR_BACKENDS:
        try:
            return DeepFace.verify(
                img1_path=img1,
                img2_path=img2,
                model_name=MODEL_NAME,
                distance_metric=DISTANCE_METRIC,
                detector_backend=backend,
                enforce_detection=True,  # 找不到人脸就报错，避免误判
            )
        except Exception as e:
            last_error = e
            logger.debug(f"[face] {backend} 检测失败：{e}，尝试下一个")
            continue
    # 所有 backend 都失败
    raise RuntimeError(f"人脸检测失败：{last_error}")


def verify_face(query_image_path: str, face_db_items: list) -> Optional[dict]:
    """
    1:N 比对：query 图 vs 人脸库所有 is_active 的记录

    face_db_items: [{"user_id": int, "name": str, "file_path": str}, ...]
    返回命中的 dict 或 None：
        {"user_id": 1, "name": "张三", "distance": 0.32, "threshold": 0.40}
    """
    best_match: Optional[dict] = None
    best_distance = float("inf")

    for item in face_db_items:
        file_path = item.get("file_path")
        if not file_path or not os.path.exists(file_path):
            logger.warning(f"[face] 跳过：文件不存在 {file_path}")
            continue

        try:
            result = verify_pair(query_image_path, file_path)
        except Exception as e:
            logger.warning(f"[face] verify 失败 {file_path}：{e}")
            continue

        distance = result.get("distance", 1.0)
        threshold = result.get("threshold", 0.4)

        # 命中：距离小于阈值 且 是当前最小距离
        if result.get("verified") and distance < best_distance:
            best_distance = distance
            best_match = {
                "user_id": item["user_id"],
                "name": item["name"],
                "distance": round(distance, 4),
                "threshold": round(threshold, 4),
            }

    return best_match
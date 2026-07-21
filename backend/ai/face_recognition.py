
import os
import cv2
import numpy as np
import logging
from typing import Optional, List, Dict, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

# ============= 全局配置 =============
MODEL_NAME = "buffalo_l"          # InsightFace轻量级模型，包含检测+识别
THRESHOLD = 0.6                   # 余弦相似度阈值，小于则认为是同一个人
FACE_SIZE = (112, 112)              # 人脸对齐后的标准尺寸

_warmed_up = False   # 预热标志
_face_analyzer = None  # InsightFace分析器实例
_device = "cpu"  # 默认使用CPU，有GPU自动切换


def _get_face_analyzer():
    """获取或初始化FaceAnalyzer实例"""
    global _face_analyzer
    if _face_analyzer is None:
        import insightface
        from insightface.app import FaceAnalysis

        # 自动检测是否有GPU可用
        try:
            import onnxruntime as ort
            providers = ort.get_available_providers()
            if 'CUDAExecutionProvider' in providers:
                global _device
                _device = "cuda"
                logger.info("[face] 检测到CUDA，使用GPU加速")
        except ImportError:
            pass

        _face_analyzer = FaceAnalysis(
            name=MODEL_NAME,
            providers=['CPUExecutionProvider'] if _device == "cpu" else ['CUDAExecutionProvider'],
            modules=['detection', 'landmark_2d_106', 'recognition', 'age_gender']  # 明确启用年龄性别检测模块
        )
        _face_analyzer.prepare(ctx_id=0 if _device == "cuda" else -1, det_size=(640, 640))
    return _face_analyzer


def warm_up(sample_image: Optional[str] = None) -> None:
    """
    服务启动时预热：跑一次假推理，把模型权重加载进内存。
    - 有样本图：用样本图检测人脸
    - 无样本图：跳过（首次请求会自动加载）
    """
    global _warmed_up
    if _warmed_up:
        return
    try:
        logger.info("[face] 模型预热开始")
        analyzer = _get_face_analyzer()

        if sample_image and os.path.exists(sample_image):
            img = cv2.imread(sample_image)
            if img is not None:
                faces = analyzer.get(img)
                logger.info(f"[face] 预热完成，检测到{len(faces)}张人脸")
        else:
            # 用随机图片预热
            dummy_img = np.random.randint(0, 255, (224, 224, 3), dtype=np.uint8)
            analyzer.get(dummy_img)
            logger.info("[face] 预热完成（使用随机图）")

        _warmed_up = True
    except Exception as e:
        logger.warning(f"[face] 预热失败（不影响正常使用）：{e}")


def _load_image(img_path: str) -> np.ndarray:
    """加载图像，支持路径或base64"""
    if isinstance(img_path, str) and os.path.exists(img_path):
        img = cv2.imread(img_path)
        if img is None:
            raise ValueError(f"无法读取图像：{img_path}")
        return img
    raise ValueError(f"无效的图像路径：{img_path}")


def _cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """计算余弦相似度，范围[0,1]，值越大越相似"""
    vec1 = vec1.flatten()
    vec2 = vec2.flatten()
    dot = np.dot(vec1, vec2)
    norm = np.linalg.norm(vec1) * np.linalg.norm(vec2)
    return dot / norm if norm > 0 else 0.0


def detect_faces(image_path: str) -> List[Dict]:
    """
    检测图像中的所有人脸，返回人脸信息列表
    返回：[{
        "bbox": [x1, y1, x2, y2],
        "keypoints": 5个关键点坐标,
        "embedding": 512维特征向量,
        "age": 年龄预测,
        "gender": 性别预测(0=女, 1=男)
    }]
    """
    analyzer = _get_face_analyzer()
    img = _load_image(image_path)
    faces = analyzer.get(img) or []

    result = []
    for face in faces:
        # 处理关键点，兼容模型未返回关键点的情况
        kps = getattr(face, 'keypoints', None)
        if kps is None:
            kps = getattr(face, 'landmark_2d_106', None)
        if kps is None:
            kps = []
        if hasattr(kps, 'tolist'):
            kps = kps.tolist()

        result.append({
            "bbox": face.bbox.tolist() if hasattr(face.bbox, 'tolist') else face.bbox,
            "keypoints": kps,
            "embedding": face.embedding,
            "age": getattr(face, 'age', 0),  # 兼容没有age属性的模型
            "gender": getattr(face, 'gender', 0),  # 兼容没有gender属性的模型
            "det_score": face.det_score
        })
    return result


def verify_pair(img1: str, img2: str) -> dict:
    """
    比对两张图片，返回比对结果。
    返回格式与原有DeepFace接口兼容：
    {
        "verified": bool,
        "distance": float,
        "threshold": float,
        "similarity": float
    }
    """
    try:
        # 检测两张图的人脸
        faces1 = detect_faces(img1)
        faces2 = detect_faces(img2)

        if not faces1 or not faces2:
            raise RuntimeError("图像中未检测到人脸")

        # 取置信度最高的人脸
        face1 = max(faces1, key=lambda x: x["det_score"])
        face2 = max(faces2, key=lambda x: x["det_score"])

        # 计算余弦相似度
        similarity = _cosine_similarity(face1["embedding"], face2["embedding"])
        distance = 1 - similarity  # 转换为距离，与原有接口保持一致

        return {
            "verified": similarity >= THRESHOLD,
            "distance": distance,
            "threshold": 1 - THRESHOLD,
            "similarity": similarity,
            "face_detected": True
        }

    except Exception as e:
        logger.error(f"[face] 比对失败：{e}")
        raise RuntimeError(f"人脸比对失败：{e}")


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


# ===================== 新增扩展功能 =====================
def get_face_attributes(image_path: str) -> Optional[List[Dict]]:
    """
    获取人脸属性：年龄、性别、关键点、检测框等
    返回：[{
        "bbox": [x1, y1, x2, y2],
        "age": 年龄,
        "gender": 性别("女"/"男"),
        "gender_score": 性别置信度,
        "det_score": 检测置信度,
        "keypoints": 5个关键点坐标
    }]
    """
    try:
        faces = detect_faces(image_path)
        if not faces:
            return None

        result = []
        for face in faces:
            # 处理关键点，确保是列表类型
            kps = face["keypoints"]
            if hasattr(kps, 'tolist'):
                kps = kps.tolist()
            kps = [[round(float(x), 2) for x in pt] for pt in kps]

            # face 是 detect_faces 返回的 dict，不是对象，需用 [] 访问
            gender = int(face["gender"])  # 0=女, 1=男
            result.append({
                "bbox": [round(float(x), 2) for x in face["bbox"]],
                "age": int(face["age"]),
                "gender": "女" if gender == 0 else "男",
                "gender_score": round(float(gender), 4),
                "det_score": round(float(face["det_score"]), 4),
                "keypoints": kps
            })
        return result
    except Exception as e:
        logger.error(f"[face] 获取属性失败：{e}")
        import traceback
        logger.error(traceback.format_exc())
        return None


def extract_embedding(image_path: str) -> Optional[np.ndarray]:
    """
    提取人脸特征向量，用于人脸库构建
    返回：512维特征向量 或 None
    """
    try:
        faces = detect_faces(image_path)
        if not faces:
            return None
        # 返回置信度最高的人脸的特征
        return max(faces, key=lambda x: x["det_score"])["embedding"]
    except Exception as e:
        logger.error(f"[face] 提取特征失败：{e}")
        return None


def liveness_detection(image_path: str) -> Dict:
    """
    活体检测（简易版，基于3D关键点和纹理分析）
    返回：{
        "is_live": bool,
        "score": float,  # 活体置信度[0,1]
        "message": str
    }
    """
    try:
        faces = detect_faces(image_path)
        if not faces:
            return {"is_live": False, "score": 0.0, "message": "未检测到人脸"}

        face = max(faces, key=lambda x: x["det_score"])
        bbox = face["bbox"]
        keypoints = face["keypoints"]

        # 简易活体判断逻辑：
        # 1. 检测框面积适中，不是太小或太大
        width = bbox[2] - bbox[0]
        height = bbox[3] - bbox[1]
        area_ratio = (width * height) / (640 * 640)  # 相对于检测尺寸的比例
        if area_ratio < 0.01 or area_ratio > 0.8:
            return {"is_live": False, "score": 0.3, "message": "人脸尺寸异常"}

        # 2. 关键点分布合理，3D姿态正常
        kpt = np.array(keypoints)
        eye_dist = np.linalg.norm(kpt[0] - kpt[1])  # 双眼距离
        nose_y = kpt[2][1]
        mouth_y = (kpt[3][1] + kpt[4][1]) / 2
        face_height = mouth_y - kpt[0][1]

        if eye_dist < 20 or face_height < 50:
            return {"is_live": False, "score": 0.4, "message": "关键点异常，可能是照片"}

        # 综合评分
        score = min(0.9, 0.5 + area_ratio * 2 + (eye_dist / 100) * 0.3)
        return {
            "is_live": score > 0.6,
            "score": round(score, 4),
            "message": "活体检测通过" if score > 0.6 else "可能是非活体"
        }

    except Exception as e:
        logger.error(f"[face] 活体检测失败：{e}")
        return {"is_live": False, "score": 0.0, "message": f"检测出错：{str(e)}"}
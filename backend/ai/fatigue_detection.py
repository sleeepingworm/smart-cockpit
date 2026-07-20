# backend/ai/fatigue_detection.py
"""
疲劳驾驶检测 · dlib HOG+SVM + 68 点关键点 + EAR/MAR 几何特征

单例懒加载：整个进程一份模型
返回结构兼容 Haar 版：boxes: [{type, x1,y1,x2,y2, confidence}, ...]
时序状态（PERCLOS/哈欠计数/告警冷却）不在这里，放到 api/fatigue.py 的 WS 端点里
"""
from __future__ import annotations
import os
import logging
import threading
from pathlib import Path
from typing import Optional
import numpy as np

logger = logging.getLogger(__name__)

# 68 点关键点索引（Kazemi 2014 标准）
LEFT_EYE_IDX  = [36, 37, 38, 39, 40, 41]
RIGHT_EYE_IDX = [42, 43, 44, 45, 46, 47]
INNER_MOUTH_IDX = [60, 61, 62, 63, 64, 65, 66, 67]

# 模型文件路径（相对 backend 根目录）
MODEL_PATH = Path(__file__).parent / "dlib_models" / "shape_predictor_68_face_landmarks.dat"


def _euclidean(p, q):
    """两个 (x, y) 点的欧氏距离"""
    return float(np.linalg.norm(np.array(p) - np.array(q)))


def eye_aspect_ratio(landmarks, eye_idx):
    """
    EAR = (|p1-p5| + |p2-p4|) / (2 * |p0-p3|)
    landmarks: List[(x, y)] 长度 68
    eye_idx:   六个关键点索引
    """
    p = [landmarks[i] for i in eye_idx]
    vertical = _euclidean(p[1], p[5]) + _euclidean(p[2], p[4])
    horizontal = _euclidean(p[0], p[3])
    if horizontal < 1e-6:
        return 0.0
    return vertical / (2.0 * horizontal)


def mouth_aspect_ratio(landmarks):
    """
    MAR 用嘴内轮廓 60-67 计算（更能反映真实张嘴，不受说话影响）
    MAR = (|61-67| + |62-66| + |63-65|) / (3 * |60-64|)
    """
    p = [landmarks[i] for i in INNER_MOUTH_IDX]
    vertical = (
        _euclidean(p[1], p[7])
        + _euclidean(p[2], p[6])
        + _euclidean(p[3], p[5])
    )
    horizontal = _euclidean(p[0], p[4])
    if horizontal < 1e-6:
        return 0.0
    return vertical / (3.0 * horizontal)


class FatigueDetector:
    """
    单例懒加载。第一次 detect() 时才加载 dlib 模型（避免服务启动阻塞）。
    warm_up() 用零数组跑一次推理，触发内部缓存分配。
    """
    _instance: Optional["FatigueDetector"] = None
    _lock = threading.Lock()

    def __init__(self):
        self._detector = None
        self._predictor = None
        self._loaded = False

    @classmethod
    def instance(cls) -> "FatigueDetector":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _lazy_load(self):
        # 双重检查 + 加锁，防止多个 WS 帧并发触发重复加载
        if self._loaded:
            return
        with self._lock:
            if self._loaded:
                return
            logger.info("[fatigue] 开始加载 dlib 模型...")
            try:
                import dlib   # type: ignore
            except ImportError as e:
                raise RuntimeError("dlib 未安装，请 uv add dlib-bin") from e

            if not MODEL_PATH.exists():
                raise RuntimeError(
                    f"dlib 68 点模型不存在: {MODEL_PATH}\n"
                    "请从 http://dlib.net/files/shape_predictor_68_face_landmarks.dat.bz2 下载并解压。"
                )

            self._detector = dlib.get_frontal_face_detector()
            self._predictor = dlib.shape_predictor(str(MODEL_PATH))
            self._loaded = True
            logger.info("[fatigue] dlib 模型加载完成")

    def warm_up(self):
        """启动预热：用 320x240 零数组跑一次，激活内部内存分配"""
        try:
            self._lazy_load()
            dummy = np.zeros((240, 320, 3), dtype=np.uint8)
            self.detect(dummy, ear_threshold=0.22, mar_threshold=0.6)
            logger.info("[fatigue] 预热完成")
        except Exception as e:
            logger.warning(f"[fatigue] 预热失败（不阻塞启动）: {e}")

    def detect(
        self,
        frame_bgr: np.ndarray,
        ear_threshold: float = 0.22,
        mar_threshold: float = 0.60,
    ) -> dict:
        """
        对一帧 BGR 图像做检测。
        返回：
        {
            "boxes": [ { "type": "face"|"open_eye"|"closed_eye"|"open_mouth"|"closed_mouth",
                         "x1","y1","x2","y2", "confidence": 0-1 }, ...],
            "eye_state": "open" | "closed" | "unknown",
            "mouth_state": "open" | "closed" | "unknown",
            "ear": float,
            "mar": float,
        }
        画面多张脸时取面积最大的一张（司机单人场景）。
        """
        import cv2   # type: ignore

        self._lazy_load()

        h, w = frame_bgr.shape[:2]
        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)

        # HOG+SVM 检脸；upsample=1 检得出小脸
        faces = self._detector(gray, 1)

        if len(faces) == 0:
            return {
                "boxes": [],
                "eye_state": "unknown",
                "mouth_state": "unknown",
                "ear": 0.0, "mar": 0.0,
            }

        # 取面积最大的脸（司机脸最大，后排乘客小）
        face = max(faces, key=lambda r: r.width() * r.height())
        fx1, fy1, fx2, fy2 = face.left(), face.top(), face.right(), face.bottom()

        # 68 点关键点
        shape = self._predictor(gray, face)
        landmarks = [(shape.part(i).x, shape.part(i).y) for i in range(68)]

        # EAR / MAR
        ear_left  = eye_aspect_ratio(landmarks, LEFT_EYE_IDX)
        ear_right = eye_aspect_ratio(landmarks, RIGHT_EYE_IDX)
        ear = (ear_left + ear_right) / 2.0
        mar = mouth_aspect_ratio(landmarks)

        # 状态判定
        eye_state = "closed" if ear < ear_threshold else "open"
        mouth_state = "open" if mar > mar_threshold else "closed"

        # 置信度：EAR/MAR 距离阈值越远越自信，映射到 [0.6, 0.95]
        eye_conf = _confidence(ear, ear_threshold)
        mouth_conf = _confidence(mar, mar_threshold, inverse=False)

        # 眼睛 / 嘴巴的包围框（从关键点算 bounding rect）
        left_eye_box  = _bbox_from_points([landmarks[i] for i in LEFT_EYE_IDX], w, h)
        right_eye_box = _bbox_from_points([landmarks[i] for i in RIGHT_EYE_IDX], w, h)
        mouth_box     = _bbox_from_points([landmarks[i] for i in INNER_MOUTH_IDX], w, h)

        eye_type   = "closed_eye" if eye_state == "closed" else "open_eye"
        mouth_type = "open_mouth" if mouth_state == "open" else "closed_mouth"

        boxes = [
            {"type": "face", "x1": fx1, "y1": fy1, "x2": fx2, "y2": fy2, "confidence": 0.95},
            {"type": eye_type,   **left_eye_box,  "confidence": round(eye_conf, 3)},
            {"type": eye_type,   **right_eye_box, "confidence": round(eye_conf, 3)},
            {"type": mouth_type, **mouth_box,     "confidence": round(mouth_conf, 3)},
        ]

        return {
            "boxes": boxes,
            "eye_state": eye_state,
            "mouth_state": mouth_state,
            "ear": round(ear, 4),
            "mar": round(mar, 4),
        }


def _bbox_from_points(pts: list, img_w: int, img_h: int, pad: int = 4) -> dict:
    """从若干关键点得到包围 rect，向外扩 pad 像素让框更好看"""
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    x1 = max(0, min(xs) - pad)
    y1 = max(0, min(ys) - pad)
    x2 = min(img_w, max(xs) + pad)
    y2 = min(img_h, max(ys) + pad)
    return {"x1": int(x1), "y1": int(y1), "x2": int(x2), "y2": int(y2)}


def _confidence(value: float, threshold: float, inverse: bool = True) -> float:
    """
    根据 value 与 threshold 的差距映射到 [0.6, 0.95]。
    inverse=True 时（EAR），value 越小于 threshold（闭眼）越自信；越大于 threshold（睁大）越自信。
    """
    diff = abs(value - threshold)
    return min(0.95, 0.6 + diff * 2.0)


# ============ 对外便捷函数 ============
def warm_up():
    """供 main.py lifespan 调用"""
    FatigueDetector.instance().warm_up()


def detect(frame_bgr: np.ndarray, ear_threshold: float, mar_threshold: float) -> dict:
    """供 api/fatigue.py WS 端点调用"""
    return FatigueDetector.instance().detect(frame_bgr, ear_threshold, mar_threshold)
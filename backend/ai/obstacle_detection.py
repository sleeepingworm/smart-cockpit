# backend/ai/obstacle_detection.py
"""
障碍物多目标检测 · Ultralytics YOLO

设计要点：
- 单例懒加载：整个进程一份模型，首次 detect() 才加载
- 双重类别过滤：模型侧（predict(classes=...)) + Python 后处理
- 返回 boxes 包含 cls_name 供前端做不同颜色渲染
- get_class_names() 暴露完整 80 类映射，供前端 GET /obstacle/info 使用
"""
from __future__ import annotations

import logging
import time
import threading
from pathlib import Path
from typing import List, Optional

import numpy as np

from config.settings import settings

logger = logging.getLogger(__name__)

# 驾驶风险默认白名单（学员未配置 OBSTACLE_CLASSES 时使用）
_DEFAULT_DRIVING_CLASSES = {
    "person", "bicycle", "car", "motorcycle",
    "bus", "truck", "traffic light", "stop sign",
}


def _parse_classes(csv: str) -> Optional[List[str]]:
    """
    解析 .env 中的类别配置：
      空字符串 -> 返回默认驾驶集
      '*'      -> 返回 None（表示不过滤，全 80 类）
      'a,b,c'  -> 返回 ['a', 'b', 'c']（小写去空格）
    """
    csv = (csv or "").strip()
    if not csv:
        return sorted(_DEFAULT_DRIVING_CLASSES)
    if csv == "*":
        return None
    return sorted({c.strip().lower() for c in csv.split(",") if c.strip()})


class ObstacleDetector:
    """
    Ultralytics YOLO 单例。第一次 detect() 时才加载模型（~500MB torch 依赖）。
    """
    _instance: Optional["ObstacleDetector"] = None
    _lock = threading.Lock()

    def __init__(self):
        self._model = None
        self._class_names: dict[int, str] = {}
        # 反向映射：class_name (lower) -> class_id
        self._name_to_id: dict[str, int] = {}
        # 白名单 class_id 列表（None 表示不过滤）
        self._active_ids: Optional[List[int]] = None

    @classmethod
    def instance(cls) -> "ObstacleDetector":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _lazy_load(self):
        # 双重检查 + 加锁，防止多个 WS 帧并发触发重复加载
        if self._model is not None:
            return
        with self._lock:
            if self._model is not None:
                return
            logger.info("[obstacle] 开始加载 YOLO 模型...")
            try:
                from ultralytics import YOLO  # type: ignore
            except ImportError as e:
                raise RuntimeError("ultralytics 未安装，请 uv add ultralytics") from e

            model_path = Path(settings.OBSTACLE_MODEL_PATH)
            if not model_path.is_absolute():
                # 相对路径基于 backend/ 目录
                model_path = Path(__file__).parent.parent / settings.OBSTACLE_MODEL_PATH
            if not model_path.exists():
                raise RuntimeError(
                    f"YOLO 模型不存在: {model_path}\n"
                    "请下载 yolo26n.pt 到 ai/ai_models/，或修改 OBSTACLE_MODEL_PATH"
                )

            logger.info(f"[obstacle] 加载 YOLO 模型 {model_path.name} ...")
            self._model = YOLO(str(model_path))

            # 从模型里取 class_id -> class_name 映射
            # Ultralytics 里 model.names 是 dict[int,str]
            self._class_names = dict(self._model.names)  # type: ignore
            self._name_to_id = {v.lower(): k for k, v in self._class_names.items()}

            # 解析白名单
            active_names = _parse_classes(settings.OBSTACLE_CLASSES)
            if active_names is None:
                self._active_ids = None
            else:
                self._active_ids = sorted({
                    self._name_to_id[n] for n in active_names if n in self._name_to_id
                })
            logger.info(
                f"[obstacle] 模型加载完成，共 {len(self._class_names)} 类；"
                f"启用 {len(self._active_ids) if self._active_ids else '全部'} 类白名单"
            )

    def warm_up(self):
        """启动预热：320x320 零数组预测一次，触发权重加载 + 内核编译"""
        try:
            self._lazy_load()
            dummy = np.zeros((320, 320, 3), dtype=np.uint8)
            self._model.predict(  # type: ignore
                dummy,
                imgsz=settings.OBSTACLE_IMGSZ,
                conf=settings.OBSTACLE_CONF,
                iou=settings.OBSTACLE_IOU,
                device=settings.OBSTACLE_DEVICE,
                half=settings.OBSTACLE_HALF,
                verbose=False,
            )
            logger.info("[obstacle] 预热完成")
        except Exception as e:
            logger.warning(f"[obstacle] 预热失败（不阻塞启动）: {e}")

    def get_class_names(self) -> dict[int, str]:
        """全 80 类映射，供 /obstacle/info 用"""
        self._lazy_load()
        return self._class_names

    def get_info(self) -> dict:
        """完整模型信息，供 /obstacle/info 用"""
        self._lazy_load()
        return {
            "model_path": settings.OBSTACLE_MODEL_PATH,
            "imgsz": settings.OBSTACLE_IMGSZ,
            "conf": settings.OBSTACLE_CONF,
            "iou": settings.OBSTACLE_IOU,
            "device": settings.OBSTACLE_DEVICE,
            "half": settings.OBSTACLE_HALF,
            "class_names": self._class_names,
            "active_classes": (
                [self._class_names[i] for i in self._active_ids]
                if self._active_ids is not None
                else list(self._class_names.values())
            ),
            "alert_classes": [
                c.strip().lower()
                for c in settings.OBSTACLE_ALERT_CLASSES.split(",")
                if c.strip()
            ],
        }

    def detect(self, frame_bgr: np.ndarray) -> dict:
        """
        对一帧做检测。返回：
        {
            "boxes": [{x1,y1,x2,y2, confidence, cls, cls_name}, ...],
            "count": int,
            "class_counts": {cls_name: count, ...},
            "avg_confidence": float,
            "latency_ms": int,
        }
        """
        self._lazy_load()

        t0 = time.time()
        results = self._model.predict(  # type: ignore
            frame_bgr,
            imgsz=settings.OBSTACLE_IMGSZ,
            conf=settings.OBSTACLE_CONF,
            iou=settings.OBSTACLE_IOU,
            device=settings.OBSTACLE_DEVICE,
            half=settings.OBSTACLE_HALF,
            classes=self._active_ids,   # 模型侧过滤
            verbose=False,
        )
        latency_ms = int((time.time() - t0) * 1000)

        boxes: list[dict] = []
        class_counts: dict[str, int] = {}
        conf_sum = 0.0

        if results and len(results) > 0:
            r0 = results[0]
            if r0.boxes is not None and len(r0.boxes) > 0:
                # xyxy: (N, 4) tensor
                xyxy = r0.boxes.xyxy.cpu().numpy()
                confs = r0.boxes.conf.cpu().numpy()
                clss = r0.boxes.cls.cpu().numpy().astype(int)

                for (x1, y1, x2, y2), c, cid in zip(xyxy, confs, clss):
                    cls_name = self._class_names.get(int(cid), str(cid))
                    # 二次防御：即使模型侧漏过，Python 侧再筛一次
                    if self._active_ids is not None and int(cid) not in self._active_ids:
                        continue
                    boxes.append({
                        "x1": int(x1), "y1": int(y1),
                        "x2": int(x2), "y2": int(y2),
                        "confidence": round(float(c), 3),
                        "cls": int(cid),
                        "cls_name": cls_name,
                    })
                    class_counts[cls_name] = class_counts.get(cls_name, 0) + 1
                    conf_sum += float(c)

        count = len(boxes)
        avg_conf = round(conf_sum / count, 3) if count else 0.0

        return {
            "boxes": boxes,
            "count": count,
            "class_counts": class_counts,
            "avg_confidence": avg_conf,
            "latency_ms": latency_ms,
        }


# ============ 对外便捷函数 ============
def warm_up():
    ObstacleDetector.instance().warm_up()


def detect(frame_bgr: np.ndarray) -> dict:
    return ObstacleDetector.instance().detect(frame_bgr)


def get_info() -> dict:
    return ObstacleDetector.instance().get_info()
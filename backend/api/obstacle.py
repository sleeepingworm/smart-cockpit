# backend/api/obstacle.py
"""
障碍物多目标检测 · WebSocket 端点

架构与 Day9 疲劳检测对称：
- Client → Server: bytes(JPEG)
- Server → Client: JSON {frame_index, boxes[cls_name], count, class_counts,
                          avg_confidence, latency_ms, alert_created, alert?}

差异点（相比 fatigue）：
- 时序状态是"每类计数器 dict"而不是单个 deque
- 分级：detected person → danger；否则 warning
- 告警描述自动汇总多个类别
"""
from __future__ import annotations

import io
import time
import asyncio
import logging
from typing import Optional

import numpy as np
from PIL import Image
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlmodel import Session

from config.settings import settings
from db.database import engine
from models.alert import Alert
from ai import obstacle_detection as obstacle

logger = logging.getLogger(__name__)

router = APIRouter(tags=["障碍物检测"])

# 中文类别别名（告警描述里用）
_CN_ALIAS = {
    "person": "行人",
    "bicycle": "自行车",
    "motorcycle": "摩托车",
    "car": "汽车",
    "bus": "公交车",
    "truck": "卡车",
    "traffic light": "交通灯",
    "stop sign": "停止标志",
}


# ============ 工具函数 ============
def _decode_jpeg_to_bgr(data: bytes) -> np.ndarray:
    import cv2  # type: ignore
    img = Image.open(io.BytesIO(data)).convert("RGB")
    return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)


def _parse_alert_classes() -> list[str]:
    return [
        c.strip().lower()
        for c in settings.OBSTACLE_ALERT_CLASSES.split(",")
        if c.strip()
    ]


def _build_alert_description(class_counts: dict, avg_conf: float) -> str:
    """告警描述自动汇总：'检测到 2 个行人、1 辆自行车，平均置信度 0.85'"""
    parts = []
    for cls_name, cnt in class_counts.items():
        alias = _CN_ALIAS.get(cls_name, cls_name)
        parts.append(f"{cnt} 个{alias}")
    desc = "检测到 " + "、".join(parts) if parts else "检测到障碍物"
    return f"{desc}，平均置信度 {avg_conf:.2f}"


def _write_obstacle_alert(
    level: str, class_counts: dict, avg_conf: float
) -> Optional[int]:
    """写告警。用独立 Session，避免 WS 长事务锁表。"""
    try:
        with Session(engine) as db:
            alert = Alert(
                alert_type="obstacle",
                level=level,
                title="障碍物检测预警",
                description=_build_alert_description(class_counts, avg_conf),
                status="pending",
            )
            db.add(alert)
            db.commit()
            db.refresh(alert)
            logger.info(
                f"[obstacle] 已写入 {level} 级告警 id={alert.id} "
                f"class_counts={class_counts}"
            )
            return alert.id
    except Exception as e:
        logger.warning(f"[obstacle] 告警入库失败: {e}")
        return None


# ============ HTTP: 模型信息 ============
@router.get("/obstacle/info", summary="获取 YOLO 模型信息（类别映射、运行参数）")
def obstacle_info():
    """
    前端启动时调用，动态构建 cls_name → 颜色调色板与告警分级信息。
    """
    return {"code": 200, "message": "success", "data": obstacle.get_info()}


# ============ WebSocket ============
@router.websocket("/ws/obstacle")
async def ws_obstacle(ws: WebSocket):
    await ws.accept()
    logger.info("[obstacle] WS 连接建立")

    alert_classes = _parse_alert_classes()
    # 每一类维护"连续命中帧数"
    persistence: dict[str, int] = {c: 0 for c in alert_classes}
    last_alert_ts = 0.0
    frame_index = 0

    try:
        while True:
            data = await ws.receive_bytes()
            frame_index += 1

            try:
                # 1. 解码 + 推理（都丢线程池）
                frame_bgr = await asyncio.to_thread(_decode_jpeg_to_bgr, data)
                result = await asyncio.to_thread(obstacle.detect, frame_bgr)
            except Exception as e:
                logger.debug(f"[obstacle] 单帧异常 #{frame_index}: {e}")
                continue

            class_counts: dict[str, int] = result["class_counts"]

            # 2. 更新每类持续计数（按告警类别）
            triggered: list[str] = []
            for cls_name in alert_classes:
                if class_counts.get(cls_name, 0) > 0:
                    persistence[cls_name] += 1
                else:
                    persistence[cls_name] = 0
                if persistence[cls_name] >= settings.OBSTACLE_ALERT_FRAMES:
                    triggered.append(cls_name)

            # 3. 告警冷却 + 分级 + 入库
            alert_created = False
            alert_payload: Optional[dict] = None
            now = time.time()
            if triggered and (now - last_alert_ts) > settings.OBSTACLE_ALERT_COOLDOWN:
                level = "danger" if "person" in triggered else "warning"
                # 只把触发类的计数带到描述里，其他类（比如汽车）不算告警对象
                trigger_counts = {c: class_counts[c] for c in triggered}
                alert_id = await asyncio.to_thread(
                    _write_obstacle_alert,
                    level,
                    trigger_counts,
                    result["avg_confidence"],
                )
                if alert_id is not None:
                    last_alert_ts = now
                    alert_created = True
                    alert_payload = {
                        "id": alert_id,
                        "level": level,
                        "class_counts": trigger_counts,
                        "description": _build_alert_description(
                            trigger_counts, result["avg_confidence"]
                        ),
                    }
                    # 触发过一次后，重置持续计数（避免连续 5+5+5 快速刷）
                    for c in triggered:
                        persistence[c] = 0

            # 4. 送回结果
            resp = {
                "frame_index":    frame_index,
                "boxes":          result["boxes"],
                "count":          result["count"],
                "class_counts":   class_counts,
                "avg_confidence": result["avg_confidence"],
                "latency_ms":     result["latency_ms"],
                "alert_created":  alert_created,
            }
            if alert_payload is not None:
                resp["alert"] = alert_payload
            await ws.send_json(resp)

    except WebSocketDisconnect:
        logger.info(f"[obstacle] WS 断开（本次处理 {frame_index} 帧）")
    except Exception as e:
        logger.warning(f"[obstacle] WS 异常: {e}")
# backend/api/fatigue.py
"""
疲劳驾驶检测 WebSocket 端点
- 客户端持续 send JPEG 二进制帧（约 200ms 一帧，5fps）
- 服务端 async 收帧，asyncio.to_thread 里跑同步 dlib 推理
- 时序状态（PERCLOS/哈欠/告警冷却）在 WS 连接生命周期内维护
- 疲劳达阈值时写 Alert 表（60s 冷却去重）
"""
import io
import time
import asyncio
import logging
from collections import deque
from datetime import datetime

import numpy as np
from PIL import Image
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlmodel import Session

from config.settings import settings
from db.database import engine
from models.alert import Alert
from ai import fatigue_detection as fatigue

logger = logging.getLogger(__name__)

router = APIRouter(tags=["疲劳检测"])


def _decode_jpeg_to_bgr(data: bytes) -> np.ndarray:
    """
    JPEG bytes → numpy BGR（dlib/OpenCV 需要 BGR）
    - PIL 解码更宽容（不完整帧不炸）；再转 BGR 通道顺序
    """
    import cv2  # type: ignore
    img = Image.open(io.BytesIO(data)).convert("RGB")
    arr = np.array(img)              # RGB
    return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)


def _write_alert(perclos: float, yawn_count: int, driver_name: str = None):
    """
    疲劳达阈值时写告警。用独立 Session（WS 生命周期内保持事务干净）。
    """
    try:
        with Session(engine) as db:
            alert = Alert(
                alert_type="fatigue",
                level="danger",
                title="疲劳驾驶预警",
                description=(
                    f"检测到驾驶员疲劳：PERCLOS={perclos:.1%}，"
                    f"累计哈欠 {yawn_count} 次"
                ),
                driver_name=driver_name,
                status="pending",
            )
            # 若你的 Alert 模型没有直接 driver_name 字段，可以先注释
            db.add(alert)
            db.commit()
            logger.info(f"[fatigue] 已写入疲劳告警 id={alert.id}")
    except Exception as e:
        logger.warning(f"[fatigue] 告警入库失败: {e}")


@router.websocket("/ws/fatigue")
async def ws_fatigue(ws: WebSocket):
    """
    协议：
        Client → Server: bytes (JPEG 帧)
        Server → Client: JSON {
            frame_index, boxes, eye_state, mouth_state,
            ear, mar, perclos, yawn_count,
            is_fatigued, has_yawn_alert,
            alert_created, latency_ms
        }
    """
    await ws.accept()
    logger.info("[fatigue] WS 连接建立")

    # 本次连接的时序状态
    window: deque = deque(maxlen=settings.FATIGUE_WINDOW_FRAMES)
    yawn_frames = 0     # 连续张嘴帧数
    yawn_count = 0
    last_alert_ts = 0.0
    frame_index = 0

    try:
        while True:
            data = await ws.receive_bytes()
            frame_index += 1

            t0 = time.time()
            try:
                # 1. 解码（线程池，避免阻塞事件循环）
                frame_bgr = await asyncio.to_thread(_decode_jpeg_to_bgr, data)

                # 2. 推理（线程池，dlib 是同步的）
                result = await asyncio.to_thread(
                    fatigue.detect,
                    frame_bgr,
                    settings.FATIGUE_EAR_THRESHOLD,
                    settings.FATIGUE_MAR_THRESHOLD,
                )
            except Exception as e:
                # 单帧解码/推理失败不断开连接，跳过即可
                logger.debug(f"[fatigue] 单帧异常: {e}")
                continue

            # 3. 时序状态更新
            is_closed = result["eye_state"] == "closed"
            window.append(is_closed)
            perclos = sum(window) / len(window) if window else 0.0

            has_yawn_alert = False
            if result["mouth_state"] == "open":
                yawn_frames += 1
            else:
                # 边沿：从"连续张嘴 N 帧"跳到闭嘴的瞬间 → 计 1 次哈欠
                if yawn_frames >= settings.FATIGUE_YAWN_MIN_FRAMES:
                    yawn_count += 1
                    has_yawn_alert = True
                yawn_frames = 0

            # 4. 疲劳判定：滑窗至少半满，且 PERCLOS ≥ 阈值
            is_fatigued = (
                len(window) >= settings.FATIGUE_WINDOW_FRAMES // 2
                and perclos >= settings.FATIGUE_PERCLOS_THRESHOLD
            )

            # 5. 告警冷却 + 入库
            alert_created = False
            now = time.time()
            if is_fatigued and (now - last_alert_ts) > settings.FATIGUE_ALERT_COOLDOWN:
                await asyncio.to_thread(_write_alert, perclos, yawn_count)
                last_alert_ts = now
                alert_created = True

            # 6. 返回结果
            latency_ms = int((time.time() - t0) * 1000)
            await ws.send_json({
                "frame_index":   frame_index,
                "boxes":         result["boxes"],
                "eye_state":     result["eye_state"],
                "mouth_state":   result["mouth_state"],
                "ear":           result["ear"],
                "mar":           result["mar"],
                "perclos":       round(perclos, 4),
                "yawn_count":    yawn_count,
                "is_fatigued":   is_fatigued,
                "has_yawn_alert": has_yawn_alert,
                "alert_created": alert_created,
                "latency_ms":    latency_ms,
            })

    except WebSocketDisconnect:
        logger.info(f"[fatigue] WS 断开 (总处理 {frame_index} 帧)")
    except Exception as e:
        logger.warning(f"[fatigue] WS 异常: {e}")
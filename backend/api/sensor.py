"""
STM32 串口传感器代理（HTTP + WebSocket，支持 mock 降级）
"""
import json
import time
import random
import asyncio
import logging
import threading
from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from config.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["传感器"])

try:
    import serial
    _HAS_SERIAL = True
except ImportError:
    _HAS_SERIAL = False


# ============= 传感器管理器（进程单例） =============
class SensorManager:
    def __init__(self):
        self._ser: Optional["serial.Serial"] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._lock = threading.Lock()
        self._cache: dict = {}          # 最新一帧数据
        self._last_update: float = 0    # 上次数据到达时间

    def start(self):
        """FastAPI lifespan 里调用：尝试打开串口 + 起后台读线程"""
        if not settings.SENSOR_ENABLED:
            logger.info("[sensor] SENSOR_ENABLED=false，跳过串口，走 mock")
            return
        if not _HAS_SERIAL:
            logger.warning("[sensor] pyserial 未安装，走 mock")
            return
        try:
            self._ser = serial.Serial(
                port=settings.SENSOR_PORT,
                baudrate=settings.SENSOR_BAUDRATE,
                timeout=1,
            )
            logger.info(f"[sensor] 串口已打开: {settings.SENSOR_PORT} @ {settings.SENSOR_BAUDRATE}")
            self._running = True
            self._thread = threading.Thread(target=self._read_loop, daemon=True)
            self._thread.start()
        except Exception as e:
            logger.warning(f"[sensor] 串口打开失败: {e}，降级 mock")
            self._ser = None

    def stop(self):
        """lifespan 关闭时调用"""
        self._running = False
        if self._ser:
            try:
                self._ser.close()
            except Exception:
                pass

    def _read_loop(self):
        """后台线程：不断 readline，解析 JSON 行"""
        while self._running and self._ser:
            try:
                line = self._ser.readline().decode("utf-8", errors="ignore").strip()
                if not line:
                    time.sleep(settings.SENSOR_READ_INTERVAL)
                    continue
                # STM32 通常输出 JSON 行：{"Temperature": 24.5, "Humidity": 45}
                data = json.loads(line)
                # 字段名归一化（驼峰 → 小写下划线）
                normalized = {
                    "temperature": data.get("Temperature"),
                    "humidity": data.get("Humidity"),
                    "light": data.get("Light"),
                    "smoke": data.get("Smoke"),
                    "potentiometer": data.get("Potentiometer"),
                    "card_id": data.get("Card_Id"),
                }
                with self._lock:
                    self._cache.update({k: v for k, v in normalized.items() if v is not None})
                    self._last_update = time.time()
            except json.JSONDecodeError:
                continue  # 不完整行/杂讯直接跳过
            except Exception as e:
                logger.warning(f"[sensor] 读取异常: {e}")
                time.sleep(0.5)

    def get_latest(self) -> dict:
        """
        返回最新一帧快照。
        - 数据在 TTL 内：返回真实数据
        - 数据过期 / 无硬件：返回 mock 抖动数据
        """
        now = time.time()
        fresh = self._cache and (now - self._last_update) < settings.SENSOR_DATA_TTL
        if fresh:
            snap = dict(self._cache)
            snap["connected"] = True
            snap["source"] = "serial"
            snap["timestamp"] = now
            return snap
        # mock
        if settings.SENSOR_MOCK_ENABLED_FALLBACK:
            return _mock_reading()
        return {"connected": False, "source": "none", "timestamp": now}


_MGR = SensorManager()


# ============= mock 数据生成器 =============
def _mock_reading() -> dict:
    """在合理区间内随机抖动，模拟车内传感器"""
    return {
        "temperature": round(22 + random.uniform(-1.5, 1.5), 1),
        "humidity": round(45 + random.uniform(-5, 5), 1),
        "light": round(500 + random.uniform(-100, 100)),
        "smoke": round(random.uniform(0, 30)),   # 0-1000, 30 以下正常
        "potentiometer": round(random.uniform(0, 4095)),
        "card_id": None,
        "connected": False,
        "source": "mock",
        "timestamp": time.time(),
    }


# ============= HTTP 接口 =============
@router.get("/sensor/latest", summary="获取最新传感器快照")
def sensor_latest():
    return {"code": 200, "message": "success", "data": _MGR.get_latest()}


@router.get("/sensor/status", summary="传感器连接状态")
def sensor_status():
    return {
        "code": 200,
        "message": "success",
        "data": {
            "enabled": settings.SENSOR_ENABLED,
            "connected": _MGR._ser is not None,
            "port": settings.SENSOR_PORT,
            "baudrate": settings.SENSOR_BAUDRATE,
            "serial_available": _HAS_SERIAL,
            "source": "serial" if (_MGR._ser and _MGR._cache) else "mock",
        },
    }


# ============= WebSocket 接口 =============
@router.websocket("/ws/sensor")
async def ws_sensor(ws: WebSocket):
    """约每秒推送一次最新快照"""
    await ws.accept()
    try:
        while True:
            snapshot = _MGR.get_latest()
            await ws.send_json(snapshot)
            await asyncio.sleep(1.0)
    except WebSocketDisconnect:
        logger.info("[sensor] 客户端断开 WS")


# ============= 提供 start/stop 给 main.py lifespan 用 =============
def start_sensor_manager():
    _MGR.start()


def stop_sensor_manager():
    _MGR.stop()
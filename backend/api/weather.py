"""
天气 API 代理（高德天气）
文档: https://lbs.amap.com/api/webservice/guide/api/weatherinfo
"""
import time
import asyncio
import logging
from typing import Optional
import httpx
from fastapi import APIRouter, Query

from config.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/weather", tags=["天气"])

# 缓存：{city_code: {"data": {...}, "ts": timestamp}}
_WEATHER_CACHE: dict = {}
_WEATHER_TTL = 600   # 10 分钟

# 降级 mock（用于无 Key 或调用失败）
_MOCK_WEATHER = {
    "city": "北京市",
    "adcode": "110000",
    "province": "北京市",
    "weather": "晴",
    "temperature": "22",
    "winddirection": "东北",
    "windpower": "3",
    "humidity": "45",
    "reporttime": "2026-07-13 09:00:00",
    "forecast": [
        {"date": "2026-07-13", "week": "1", "dayweather": "晴", "nightweather": "多云", "daytemp": "26", "nighttemp": "18"},
        {"date": "2026-07-14", "week": "2", "dayweather": "多云", "nightweather": "阴", "daytemp": "24", "nighttemp": "17"},
    ],
    "source": "mock",
}


@router.get("/current", summary="查询当前天气")
async def current_weather(
    city: str = Query("110000", description="城市 adcode，默认北京"),
):
    """
    合并返回：实况（base） + 未来预报（all）
    - 命中缓存直接返回
    - 未配 Key / 上游失败 → mock
    """
    now = time.time()
    if city in _WEATHER_CACHE and now - _WEATHER_CACHE[city]["ts"] < _WEATHER_TTL:
        return {"code": 200, "message": "success", "data": _WEATHER_CACHE[city]["data"]}

    if not settings.AMAP_KEY:
        logger.info("[weather] AMAP_KEY 未配置，返回 mock 天气")
        return {"code": 200, "message": "success (mock)", "data": _MOCK_WEATHER}

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # 并发请求：实况 + 预报
            base_task = client.get(
                "https://restapi.amap.com/v3/weather/weatherInfo",
                params={"key": settings.AMAP_KEY, "city": city, "extensions": "base"},
            )
            all_task = client.get(
                "https://restapi.amap.com/v3/weather/weatherInfo",
                params={"key": settings.AMAP_KEY, "city": city, "extensions": "all"},
            )
            base_resp, all_resp = await asyncio.gather(base_task, all_task)

        base = base_resp.json()
        all_ = all_resp.json()

        if base.get("status") != "1":
            raise RuntimeError(f"高德实况返回失败: {base.get('info')}")

        live = (base.get("lives") or [{}])[0]
        forecast_pack = (all_.get("forecasts") or [{}])[0]

        data = {
            "city": live.get("city", ""),
            "adcode": live.get("adcode", city),
            "province": live.get("province", ""),
            "weather": live.get("weather", ""),
            "temperature": live.get("temperature", ""),
            "winddirection": live.get("winddirection", ""),
            "windpower": live.get("windpower", ""),
            "humidity": live.get("humidity", ""),
            "reporttime": live.get("reporttime", ""),
            "forecast": forecast_pack.get("casts", []),
            "source": "amap",
        }

        _WEATHER_CACHE[city] = {"data": data, "ts": now}
        return {"code": 200, "message": "success", "data": data}

    except Exception as e:
        logger.warning(f"[weather] 天气获取失败，降级 mock：{e}")
        return {"code": 200, "message": "success (fallback mock)", "data": _MOCK_WEATHER}
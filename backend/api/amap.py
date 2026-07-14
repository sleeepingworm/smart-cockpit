"""
高德地图 API 代理（IP 定位）
文档: https://lbs.amap.com/api/webservice/guide/api/ipconfig
"""
import time
import logging
from typing import Optional
import httpx
from fastapi import APIRouter, HTTPException

from config.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/amap", tags=["高德地图"])

# ============= 简易内存缓存 =============
# key: "latest"（IP 定位不区分 IP，只缓存最近一次）
# value: {"data": {...}, "ts": time.time()}
_LOCATE_CACHE: dict = {}
_LOCATE_TTL = 600   # 10 分钟


# ============= 默认降级值（北京天安门）=============
_MOCK_LOCATE = {
    "province": "北京市",
    "city": "北京市",
    "adcode": "110000",
    "rectangle": "116.0119343,39.66127144;116.7829835,40.2164962",
    "center": [116.404, 39.915],
    "source": "mock",
}


@router.get("/locate", summary="IP 定位（代理高德）")
async def amap_locate():
    """
    调高德 IP 定位 API，返回省市 + 中心点经纬度。
    - 未配置 AMAP_KEY / 上游失败：降级返回北京天安门
    - 10 分钟内返回缓存
    """
    # 1. 命中缓存直接返回
    now = time.time()
    if (
        "latest" in _LOCATE_CACHE
        and now - _LOCATE_CACHE["latest"]["ts"] < _LOCATE_TTL
    ):
        return {
            "code": 200,
            "message": "success",
            "data": _LOCATE_CACHE["latest"]["data"],
        }

    # 2. 未配置 Key 直接 mock
    if not settings.AMAP_KEY:
        logger.info("[amap] AMAP_KEY 未配置，返回 mock 定位")
        return {"code": 200, "message": "success (mock)", "data": _MOCK_LOCATE}

    # 3. 真调高德
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                "https://restapi.amap.com/v3/ip",
                params={"key": settings.AMAP_KEY, "output": "json"},
            )
        raw = resp.json()

        # 高德的 status=1 表示成功
        if raw.get("status") != "1":
            raise RuntimeError(f"高德返回失败: {raw.get('info')}")

        # 解析 rectangle 字符串为中心点
        rect = raw.get("rectangle", "")
        center = _MOCK_LOCATE["center"]
        if rect and ";" in rect:
            (x1, y1), (x2, y2) = [
                [float(x) for x in p.split(",")] for p in rect.split(";")
            ]
            center = [round((x1 + x2) / 2, 6), round((y1 + y2) / 2, 6)]

        data = {
            "province": raw.get("province", ""),
            "city": raw.get("city", ""),
            "adcode": raw.get("adcode", ""),
            "rectangle": rect,
            "center": center,
            "source": "amap",
        }

        # 更新缓存
        _LOCATE_CACHE["latest"] = {"data": data, "ts": now}
        return {"code": 200, "message": "success", "data": data}

    except Exception as e:
        logger.warning(f"[amap] 定位失败，降级 mock：{e}")
        return {"code": 200, "message": "success (fallback mock)", "data": _MOCK_LOCATE}
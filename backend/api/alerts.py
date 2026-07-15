from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select, func
from typing import Optional
from datetime import datetime

from db.database import SessionDep
from models.alert import Alert, AlertCreate, AlertHandle, AlertResp
from core.security import get_current_user

router = APIRouter(
    prefix="/alerts",
    tags=["告警管理"],
    dependencies=[Depends(get_current_user)],
)


@router.get("/alerts", summary="分页查询告警列表（多条件筛选）")
def list_alerts(
    db: SessionDep,
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(10, ge=1, le=100, description="每页条数"),
    alert_type: Optional[str] = Query(None, description="告警类型筛选"),
    level: Optional[str] = Query(None, description="级别筛选：info/warning/danger"),
    status: Optional[str] = Query(None, description="状态筛选：pending/handled/ignored"),
    vehicle_id: Optional[str] = Query(None, description="车牌号筛选"),
):
    """多条件组合筛选告警列表，支持分页"""
    # 基础查询
    stmt = select(Alert)
    count_stmt = select(func.count()).select_from(Alert)

    # 动态拼装 WHERE 条件
    if alert_type is not None:
        stmt = stmt.where(Alert.alert_type == alert_type)
        count_stmt = count_stmt.where(Alert.alert_type == alert_type)
    if level is not None:
        stmt = stmt.where(Alert.level == level)
        count_stmt = count_stmt.where(Alert.level == level)
    if status is not None:
        stmt = stmt.where(Alert.status == status)
        count_stmt = count_stmt.where(Alert.status == status)
    if vehicle_id is not None:
        stmt = stmt.where(Alert.vehicle_id == vehicle_id)
        count_stmt = count_stmt.where(Alert.vehicle_id == vehicle_id)

    # 总数（用 func.count 让数据库返回一个数字，比 len(all()) 高效）
    total = db.exec(count_stmt).one()

    # 分页查询
    stmt = stmt.offset((page - 1) * size).limit(size).order_by(Alert.created_at.desc())
    alerts = db.exec(stmt).all()

    data = [AlertResp.model_validate(a) for a in alerts]

    return {
        "code": 200,
        "message": "查询成功",
        "data": data,
        "total": total,
        "page": page,
        "size": size,
    }


@router.get("/alerts/{alert_id}", summary="获取告警详情")
def get_alert(alert_id: int, db: SessionDep):
    """根据ID查单条告警"""
    alert = db.get(Alert, alert_id)
    if not alert:
        return {"code": 404, "message": f"告警{alert_id}不存在", "data": None}
    return {
        "code": 200,
        "message": "success",
        "data": AlertResp.model_validate(alert),
    }


@router.post("/alerts", summary="创建告警（AI检测自动调用）", status_code=201)
def create_alert(req: AlertCreate, db: SessionDep):
    """创建告警（AI检测模块/手动测试用）"""
    alert = Alert.model_validate(req)
    db.add(alert)
    db.commit()
    db.refresh(alert)

    return {
        "code": 200,
        "message": "创建成功",
        "data": AlertResp.model_validate(alert),
    }


@router.patch("/alerts/{alert_id}/handle", summary="处理告警（仅 pending 状态可处理）")
def handle_alert(alert_id: int, payload: AlertHandle, db: SessionDep):
    """
    处理告警：将 pending 状态的告警标记为 handled(已处理) 或 ignored(已忽略)。
    已处理/已忽略是终态，不能重复处理。
    """
    alert = db.get(Alert, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="告警记录不存在")

    if alert.status != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"该告警状态为 {alert.status}，无法重复处理",
        )

    # 执行业务动作
    alert.status = payload.status
    alert.handled_at = datetime.now()
    alert.updated_at = datetime.now()

    db.add(alert)
    db.commit()
    db.refresh(alert)

    return {
        "code": 200,
        "message": "处理成功",
        "data": AlertResp.model_validate(alert),
    }


@router.delete("/alerts/{alert_id}", summary="删除告警")
def delete_alert(alert_id: int, db: SessionDep):
    """删除告警记录"""
    alert = db.get(Alert, alert_id)
    if not alert:
        return {"code": 404, "message": f"告警{alert_id}不存在", "data": None}

    db.delete(alert)
    db.commit()

    return {"code": 200, "message": "删除成功", "data": None}